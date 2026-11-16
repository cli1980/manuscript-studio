"""Common operation contract and the Codex App Server protocol adapter."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .stdio import StdioTransport
from .usage import CodexUsage


@dataclass(frozen=True)
class Request:
    cwd: Path
    prompt: str
    model: str | None
    thread_id: str | None
    output_schema: dict


class Runtime(Protocol):
    def run(self, request: Request, on_event: Callable, on_thread: Callable) -> dict: ...


class CodexRuntime:
    def __init__(self, command=None, timeout=900):
        self.command = command or ["codex", "app-server"]
        self.timeout = timeout

    def run(self, request, on_event, on_thread):
        with StdioTransport(self.command, cwd=request.cwd, timeout=self.timeout, name="Codex") as transport:
            next_id = 0
            pending = deque()

            def receive():
                while True:
                    message = transport.receive()
                    if "method" not in message or "id" not in message:
                        return message
                    method = message["method"]
                    on_event("runtime.request", {"method": method, "declined": True})
                    if method in ("item/commandExecution/requestApproval", "item/fileChange/requestApproval"):
                        transport.send({"id": message["id"], "result": {"decision": "decline"}})
                    else:
                        transport.send({"id": message["id"], "error": {
                            "code": -32601, "message": "Unsupported interactive request; use saved domain gates."}})

            def rpc(method, params):
                nonlocal next_id
                next_id += 1
                call_id = next_id
                transport.send({"id": call_id, "method": method, "params": params})
                while True:
                    message = receive()
                    if message.get("id") == call_id and "method" not in message:
                        if "error" in message:
                            raise RuntimeError(f"{method}: {message['error']}")
                        return message["result"]
                    pending.append(message)

            rpc("initialize", {"clientInfo": {"name": "manuscript_workflow", "version": "0.1.0"},
                               "capabilities": {"experimentalApi": False}})
            transport.send({"method": "initialized", "params": {}})
            params = {"cwd": str(request.cwd), "approvalPolicy": "never",
                      "sandbox": "workspace-write"}
            if request.model:
                params["model"] = request.model
            if request.thread_id:
                params["threadId"] = request.thread_id
            result = rpc("thread/resume" if request.thread_id else "thread/start", params)
            thread_id = result["thread"]["id"]
            on_thread(thread_id)  # Durable before submitting work.
            turn = rpc("turn/start", {
                "threadId": thread_id,
                "input": [{"type": "text", "text": request.prompt, "text_elements": []}],
                "outputSchema": request.output_schema,
                "sandboxPolicy": {"type": "workspaceWrite", "writableRoots": [str(request.cwd)],
                                  "networkAccess": False},
            })
            turn_id = turn["turn"]["id"]
            on_event("runtime.turn_started", {"id": turn_id})
            final, usage = None, CodexUsage()
            try:
                while True:
                    message = pending.popleft() if pending else receive()
                    params = message.get("params", {})
                    if params.get("threadId") != thread_id:
                        continue
                    method = message.get("method")
                    if method == "turn/completed" and params["turn"]["id"] == turn_id:
                        failed = params["turn"]["status"] != "completed"
                        on_event("runtime.turn_completed", {"id": turn_id, "failed": failed})
                        if failed:
                            raise RuntimeError(f"Codex turn did not complete: {params['turn']}")
                        if final is None:
                            raise ValueError("Completed turn had no final structured message.")
                        return json.loads(final)
                    if params.get("turnId") != turn_id:
                        continue
                    if method in ("item/started", "item/completed"):
                        item = params["item"]
                        if item.get("type") in ("commandExecution", "fileChange", "mcpToolCall",
                                                "dynamicToolCall", "webSearch"):
                            kind = "runtime.tool_started" if method == "item/started" else "runtime.tool_completed"
                            on_event(kind, {"id": item.get("id"), "tool": item["type"],
                                            "failed": item.get("exitCode") not in (None, 0)})
                        if method == "item/completed" and item.get("type") == "agentMessage":
                            final = item["text"]
                    elif method == "thread/tokenUsage/updated":
                        delta = usage.update(params.get("tokenUsage", {}))
                        if delta is not None:
                            on_event("runtime.usage", {"id": turn_id, "accounting": "delta-v1",
                                                      "partial": usage.partial, **delta})
            except (TimeoutError, KeyboardInterrupt):
                try:
                    transport.send({"id": "interrupt", "method": "turn/interrupt",
                                    "params": {"threadId": thread_id, "turnId": turn_id}})
                except RuntimeError:
                    pass
                raise
