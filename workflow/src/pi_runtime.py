"""Pinned Pi JSONL adapter. Fresh sessions recover from the engine's durable context."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from jsonschema import Draft202012Validator

from .stdio import StdioTransport

VERSION = "0.73.1"
EXTENSION = Path(__file__).resolve().parents[1] / "adapters/pi/workflow-result.mjs"


class PiRuntime:
    def __init__(self, command, timeout=900, *, endpoint, model, api_key):
        self.command = list(command)
        self.timeout = timeout
        self.endpoint, self.model, self.api_key = endpoint, model, api_key

    def run(self, request, on_event, on_thread):
        # Pi tools run with the host user's permissions. This is not a sandbox.
        version = subprocess.run([*self.command, "--version"], capture_output=True, text=True,
                                 encoding="utf-8", timeout=min(self.timeout, 20))
        if version.returncode or VERSION not in (version.stdout.strip(), version.stderr.strip()):
            raise RuntimeError(f"Pi evaluation requires @mariozechner/pi-coding-agent {VERSION}.")
        with tempfile.TemporaryDirectory(prefix="manuscript-pi-") as temp:
            root = Path(temp)
            schema_path = root / "result-schema.json"
            schema_path.write_text(json.dumps(request.output_schema), encoding="utf-8", newline="\n")
            provider = {
                "baseUrl": self.endpoint["base_url"], "api": self.endpoint["api"],
                "apiKey": "MANUSCRIPT_PI_API_KEY", "authHeader": True,
                "models": [{"id": self.model, "name": self.model, "reasoning": False,
                            "input": ["text"]}],
            }
            (root / "models.json").write_text(json.dumps({"providers": {"manuscript": provider}}),
                                             encoding="utf-8", newline="\n")
            (root / "settings.json").write_text(
                json.dumps({"retry": {"enabled": False}, "compaction": {"enabled": False}}),
                encoding="utf-8", newline="\n")
            env = {**os.environ, "PI_CODING_AGENT_DIR": str(root),
                   "MANUSCRIPT_PI_SCHEMA": str(schema_path), "MANUSCRIPT_PI_API_KEY": self.api_key}
            command = [*self.command, "--mode", "rpc", "--no-session", "--no-extensions",
                       "--no-skills", "--no-prompt-templates", "--no-context-files", "--no-themes",
                       "--extension", str(EXTENSION), "--provider", "manuscript", "--model", self.model]
            with StdioTransport(command, cwd=request.cwd, timeout=self.timeout, name="Pi", env=env) as transport:
                return self._operation(request, transport, on_event, on_thread)

    def _operation(self, request, transport, on_event, on_thread):
        identity = "pi-" + uuid.uuid4().hex
        result, error = None, None
        try:
            on_thread(identity)
            prompt = (request.prompt + "\n\nReturn the operation result by calling workflow_result alone as "
                      "your final tool call. Plain assistant text is not a workflow result. Human questions "
                      "must use saved domain gates, not interactive Pi UI. The host validates all results.")
            transport.send({"id": "operation", "type": "prompt", "message": prompt})
            while True:
                event = transport.receive()
                kind = event.get("type")
                if kind == "response" and not event.get("success"):
                    raise RuntimeError("Pi rejected a protocol command.")
                if kind == "extension_error":
                    raise RuntimeError("Pi could not load or execute the workflow result extension.")
                if kind == "extension_ui_request":
                    transport.send({"type": "extension_ui_response", "id": event["id"], "cancelled": True})
                    raise RuntimeError("Interactive Pi requests are unsupported; use saved domain gates.")
                if kind == "agent_start":
                    on_event("runtime.turn_started", {"id": identity})
                elif kind == "tool_execution_start":
                    on_event("runtime.tool_started", {"id": event.get("toolCallId"), "tool": event.get("toolName")})
                elif kind == "tool_execution_end":
                    on_event("runtime.tool_completed", {"id": event.get("toolCallId"),
                                                      "tool": event.get("toolName"),
                                                      "failed": bool(event.get("isError"))})
                    if event.get("toolName") == "workflow_result":
                        if result is not None or event.get("isError"):
                            raise ValueError("Pi returned a duplicate or invalid workflow result.")
                        result = (event.get("result") or {}).get("details", {}).get("workflow_result")
                        if result is None:
                            raise ValueError("Pi result tool returned no structured workflow result.")
                        if next(Draft202012Validator(request.output_schema).iter_errors(result), None):
                            raise ValueError("Pi returned a result that does not match the stage schema.")
                elif kind == "message_end":
                    message = event.get("message") or {}
                    if message.get("role") == "assistant":
                        if message.get("stopReason") in ("error", "aborted", "length"):
                            error = "Pi inference failed, was interrupted, or exhausted its output limit."
                        usage = message.get("usage")
                        if usage:
                            on_event("runtime.usage", {"id": identity, "accounting": "delta-v1",
                                                      "input": sum(usage.get(k, 0) or 0 for k in
                                                                   ("input", "cacheRead", "cacheWrite")),
                                                      **{key: usage.get(key) for key in
                                                         ("output", "cacheRead", "cacheWrite")}})
                elif kind == "agent_end":
                    on_event("runtime.turn_completed", {"id": identity, "failed": bool(error)})
                    if error:
                        raise RuntimeError(error)
                    if result is None:
                        raise ValueError("Pi finished without calling the workflow_result tool.")
                    return result
        except (TimeoutError, KeyboardInterrupt):
            try:
                transport.send({"id": "abort", "type": "abort"})
            except RuntimeError:
                pass
            raise
