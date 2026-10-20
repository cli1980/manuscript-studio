"""Small synchronous Codex App Server stdio adapter; no model SDK dependency."""

from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol


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
        process = subprocess.Popen(
            self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1, cwd=request.cwd,
        )
        messages = queue.Queue()
        stderr = []

        def read_stdout():
            try:
                for line in process.stdout:
                    try:
                        messages.put(json.loads(line))
                    except json.JSONDecodeError:
                        messages.put(RuntimeError("App Server emitted invalid JSON."))
            finally:
                messages.put(EOFError("App Server closed its output."))

        def read_stderr():
            for line in process.stderr:
                stderr.append(line.rstrip())
                del stderr[:-20]

        readers = [threading.Thread(target=read_stdout, daemon=True),
                   threading.Thread(target=read_stderr, daemon=True)]
        for reader in readers:
            reader.start()
        deadline = time.monotonic() + self.timeout
        next_id = 0
        pending = []

        def send(message):
            process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            process.stdin.flush()

        def receive():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Codex turn exceeded the configured execution timeout.")
            try:
                message = messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise TimeoutError("Codex turn exceeded the configured execution timeout.") from exc
            if isinstance(message, Exception):
                raise RuntimeError(f"{message} {' '.join(stderr)}")
            # No permission escalation is supported in this first CLI iteration.
            if "method" in message and "id" in message:
                on_event("runtime.request", message)
                if message["method"] in (
                    "item/commandExecution/requestApproval", "item/fileChange/requestApproval"
                ):
                    send({"id": message["id"], "result": {"decision": "decline"}})
                else:
                    send({"id": message["id"], "error": {
                        "code": -32601, "message": "Unsupported interactive runtime request; use saved domain gates."
                    }})
                return receive()
            if "method" in message:
                on_event(message["method"], message.get("params", {}))
            return message

        def rpc(method, params):
            nonlocal next_id
            next_id += 1
            call_id = next_id
            send({"id": call_id, "method": method, "params": params})
            while True:
                message = receive()
                if message.get("id") == call_id and "method" not in message:
                    if "error" in message:
                        raise RuntimeError(f"{method}: {message['error']}")
                    return message["result"]
                # Notifications can arrive before the response, including turn/completed.
                pending.append(message)

        try:
            rpc("initialize", {"clientInfo": {"name": "manuscript_workflow", "version": "0.1.0"},
                               "capabilities": {"experimentalApi": False}})
            send({"method": "initialized", "params": {}})
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
            final = None
            while True:
                message = pending.pop(0) if pending else receive()
                params = message.get("params", {})
                if params.get("threadId") != thread_id:
                    continue
                method = message.get("method")
                if method == "item/completed" and params.get("turnId") == turn_id:
                    item = params["item"]
                    if item.get("type") == "agentMessage":
                        final = item["text"]
                if method == "turn/completed" and params["turn"]["id"] == turn_id:
                    if params["turn"]["status"] != "completed":
                        raise RuntimeError(f"Codex turn did not complete: {params['turn']}")
                    if final is None:
                        raise ValueError("Completed turn had no final structured message.")
                    return json.loads(final)
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            for reader in readers:
                reader.join(timeout=2)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
