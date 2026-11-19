"""Execution-profile and Pi transport checks; no external inference requests."""

import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from ..src.engine import result_schema
from ..src import cli
from ..src.execution import ExecutionProfile
from ..src.harnesses import HARNESSES, Harness
from ..src.pi_runtime import PiRuntime
from ..src.runtime import Request
from ..src.service import WorkflowService
from ..src.stdio import StdioTransport

PI_CLI = Path(__file__).resolve().parents[2] / (
    ".workflow-runs/pi-evaluation/node_modules/@mariozechner/pi-coding-agent/dist/cli.js")


def profile_data():
    return {
        "name": "evaluation", "harness": "pi", "trusted_local_execution": True,
        "default_model": "choice",
        "endpoints": {"fixture": {"base_url": "https://inference.example.test/v1",
                                 "api": "openai-completions", "api_key_env": "TEST_INFERENCE_KEY"}},
        "models": [{"key": "choice", "model": "vendor/family/test-model", "endpoint": "fixture",
                    "workflows": ["literary-translation"]}],
    }


class ProfileTests(unittest.TestCase):
    def setUp(self):
        from .inline_intake_fixture import inline_intake_templates
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.enterContext(inline_intake_templates(Path(folder.name)))

    def test_restart_rejects_changed_models_without_cancelling_original(self):
        for change in ("removed-key", "restricted-workflow", "incompatible-default"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                source = root / "source.md"
                source.write_bytes(b"# Story\n\nSynthetic manuscript.\n")
                original = profile_data()
                service = WorkflowService(root / "server", execution_profile=ExecutionProfile(original))
                try:
                    run_id = service.create_run("literary-translation-v1", upload=source,
                                                manuscript_language="en", model="choice")
                    path = Path(service._run_row(run_id)["path"])
                    before = service._load_state(path)
                finally:
                    service.close()
                updated = copy.deepcopy(original)
                if change == "removed-key":
                    updated["default_model"] = updated["models"][0]["key"] = "replacement"
                elif change == "restricted-workflow":
                    updated["models"][0]["workflows"] = ["literary-editing"]
                else:
                    updated["models"].append({**updated["models"][0], "key": "editing-only",
                                              "workflows": ["literary-editing"]})
                    updated["default_model"] = "editing-only"
                service = WorkflowService(root / "server", execution_profile=ExecutionProfile(updated))
                try:
                    with self.assertRaises(ValueError):
                        service.restart_workflow(run_id, reason="Profile changed")
                    self.assertEqual(service._load_state(path), before)
                    self.assertEqual(service._run_row(run_id)["status"], before["status"])
                    self.assertEqual([r["id"] for r in service.list_runs()], [run_id])
                finally:
                    service.close()
                service = WorkflowService(root / "server", execution_profile=ExecutionProfile(original))
                try:
                    replacement = service.restart_workflow(run_id, reason="Compatible profile restored")
                    self.assertEqual(service._load_state(path)["superseded_by"], replacement)
                    self.assertEqual(service.get_run(replacement)["execution"]["model_key"], "choice")
                finally:
                    service.close()

    def test_file_and_credentials_are_snapshotted_and_secrets_are_not_public(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            data = profile_data()
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch.dict(os.environ, {"TEST_INFERENCE_KEY": "original-secret"}):
                profile = ExecutionProfile.load(path)
            data["models"][0]["model"] = "another-model"
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch.dict(os.environ, {"TEST_INFERENCE_KEY": "changed-secret"}):
                self.assertEqual(profile.select(None).model, "vendor/family/test-model")
                self.assertEqual(profile.redact({"message": "original-secret"}), {"message": "[REDACTED]"})
                reloaded = ExecutionProfile.load(path)
            self.assertNotEqual(profile.revision, reloaded.revision)
            self.assertNotIn("original-secret", json.dumps(profile.public()))
            self.assertNotIn("api_key_env", json.dumps(profile.public()))
            self.assertEqual(reloaded.select(None).model, "another-model")

    def test_model_selection_is_endpoint_qualified_and_workflow_checked(self):
        data = profile_data()
        data["endpoints"]["other"] = {**data["endpoints"]["fixture"], "base_url": "https://other.example/v1"}
        data["models"].append({**data["models"][0], "key": "other-choice", "endpoint": "other"})
        profile = ExecutionProfile(data)
        self.assertEqual(profile.describe("other-choice")["endpoint"], "other")
        with self.assertRaisesRegex(ValueError, "not enabled"):
            profile.select("choice", "literary-editing")
        with self.assertRaisesRegex(ValueError, "no fallback"):
            profile.select("unknown")

    def test_reject_untrusted_execution_invalid_config_and_credential_urls(self):
        for change in (
            {"trusted_local_execution": False},
            {"default_model": "unknown"},
            {"api_key": "never-print-this-secret"},
            {"endpoints": {"fixture": {"base_url": "https://user:never-print-this-secret@example.com/v1",
                                      "api": "openai-completions", "api_key_env": "TEST_INFERENCE_KEY"}}},
        ):
            with self.subTest(change=list(change)):
                with self.assertRaises(ValueError) as error:
                    ExecutionProfile({**profile_data(), **change})
                self.assertNotIn("never-print-this-secret", str(error.exception))

    def test_missing_credentials_fail_without_launching_pi(self):
        with patch.dict(os.environ, {"TEST_INFERENCE_KEY": ""}):
            runtime = ExecutionProfile(profile_data()).runtime()
        with patch("workflow.src.harnesses.PiRuntime") as adapter:
            with self.assertRaisesRegex(RuntimeError, "Missing credential environment variable"):
                runtime.run(Request(Path.cwd(), "", "choice", None, result_schema([])),
                            lambda *args: None, lambda *args: None)
            adapter.assert_not_called()

    def test_provider_error_is_redacted(self):
        with patch.dict(os.environ, {"TEST_INFERENCE_KEY": "test-secret-value"}):
            runtime = ExecutionProfile(profile_data()).runtime()
        with patch("workflow.src.harnesses.PiRuntime") as adapter:
            adapter.return_value.run.side_effect = RuntimeError("Authorization failed: test-secret-value")
            with self.assertRaisesRegex(RuntimeError, r"Authorization failed: \[REDACTED\]"):
                runtime.run(Request(Path.cwd(), "", None, None, result_schema([])),
                            lambda *args: None, lambda *args: None)

    def test_cli_creation_keeps_the_profile_and_model_key(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.md"
            source.write_bytes(b"# A short manuscript\n\nOne paragraph.\n")
            path = root / "profile.json"
            path.write_text(json.dumps(profile_data()), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = cli.main(["--server-root", str(root / "server"), "--execution-profile", str(path),
                                 "create", "--template", "literary-translation-v1", "--source", str(source),
                                 "--manuscript-language", "en", "--model", "choice"])
            self.assertEqual(code, 0, output.getvalue())
            self.assertIn('"model_key": "choice"', output.getvalue())
            self.assertIn('"model": "vendor/family/test-model"', output.getvalue())
            self.assertIn(f'--execution-profile "{path}" step ', output.getvalue())

    def test_profile_forwards_adapter_events_without_changing_its_model_choice(self):
        profile = ExecutionProfile({
            "name": "codex", "harness": "codex", "default_model": "choice",
            "models": [{"key": "choice", "model": "configured-model"}],
        })
        events = []

        def operation(request, emit, on_thread):
            self.assertEqual(request.model, "configured-model")
            self.assertEqual(request.thread_id, "same-profile-thread")
            on_thread(request.thread_id)
            emit("runtime.turn_started", {"id": "one"})
            emit("runtime.usage", {"input": 100, "output": 10, "cacheRead": 50})
            emit("runtime.turn_completed", {"id": "one", "failed": False})
            return {"outcome": "blocked"}

        with patch("workflow.src.harnesses.CodexRuntime") as adapter:
            adapter.return_value.run.side_effect = operation
            result = profile.runtime().run(
                Request(Path.cwd(), "", "choice", "same-profile-thread", result_schema([])),
                lambda *event: events.append(event), lambda *args: None)
        self.assertEqual(result["outcome"], "blocked")
        self.assertEqual(events[0][0], "runtime.turn_started")
        self.assertEqual(events[-1][0], "runtime.turn_completed")
        self.assertEqual(sum(p["input"] for k, p in events if k == "runtime.usage"), 100)

    def test_registered_harness_is_bound_at_startup_without_profile_dispatch_changes(self):
        calls = []
        factory = lambda profile, model: calls.append(model.model) or object()
        entry = Harness(factory, ("test-harness",), "test-only")
        with patch.dict(HARNESSES, {"test-harness": entry}):
            profile = ExecutionProfile({
                "name": "registered", "harness": "test-harness", "default_model": "choice",
                "models": [{"key": "choice", "model": "test-model"}],
            })
        self.assertEqual(calls, [])  # Profile loading and wrapper creation must not launch anything.
        profile.runtime()
        profile.create_adapter(profile.select(None))
        self.assertEqual(calls, ["test-model"])
        self.assertEqual(profile.command, ("test-harness",))
        self.assertEqual(profile.describe()["sandbox"], "test-only")
        with self.assertRaisesRegex(ValueError, "Unknown execution harness"):
            ExecutionProfile({**profile_data(), "harness": "unregistered"})

    def test_constructors_have_no_subprocess_side_effects(self):
        with patch("workflow.src.stdio.subprocess.Popen") as spawn:
            profile = ExecutionProfile({"name": "codex", "harness": "codex", "default_model": "one",
                                        "models": [{"key": "one", "model": "test-model"}]})
            profile.runtime()
            profile.create_adapter(profile.select(None))
            StdioTransport(["test"], cwd=Path.cwd(), timeout=1, name="test")
            spawn.assert_not_called()


class UserProfileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project, self.user = self.root / "project.json", self.root / "user.json"
        self.write(self.project, profile_data())

    @staticmethod
    def write(path, data):
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_bundled_pi_profile_is_policy_only_and_requires_user_choices(self):
        folder = Path(__file__).resolve().parents[1] / "profiles"
        project = folder / "pi-evaluation.json"
        data = json.loads(project.read_text(encoding="utf-8"))
        self.assertTrue({"endpoints", "models", "default_model"}.isdisjoint(data))
        with self.assertRaisesRegex(ValueError, "execution profile"):
            ExecutionProfile.load(project)
        profile = ExecutionProfile.load(project, folder / "user.example.json")
        self.assertEqual(profile.harness, "pi")
        self.assertEqual(profile.select(None).key, "personal-model")
        self.assertEqual(profile.describe()["base_url"], "https://api.example.com/v1")

    def test_user_entries_extend_and_replace_complete_objects_without_mutating_files(self):
        data = profile_data()
        data["models"].append({**data["models"][0], "key": "keep"})
        self.write(self.project, data)
        self.write(self.user, {
            "default_model": "personal",
            "endpoints": {"fixture": {"base_url": "https://personal.example/v1", "api": "openai-responses",
                                      "api_key_env": "USER_INFERENCE_KEY"}},
            "models": [{"key": "choice", "model": "replacement", "endpoint": "fixture"},
                       {"key": "personal", "model": "personal-model", "endpoint": "fixture",
                        "workflows": ["literary-translation"]}],
        })
        before = (self.project.read_bytes(), self.user.read_bytes())
        with patch.dict(os.environ, {"TEST_INFERENCE_KEY": "project-secret", "USER_INFERENCE_KEY": "user-secret"}):
            merged = ExecutionProfile.load(self.project, self.user)
        self.assertEqual([m.key for m in merged.models], ["choice", "keep", "personal"])
        self.assertEqual(merged.select(None).key, "personal")
        self.assertEqual(merged.select("choice").model, "replacement")
        self.assertEqual(merged.select("choice").workflows, ())  # Replacement, not field-by-field inheritance.
        self.assertEqual(merged.select("keep").model, "vendor/family/test-model")
        self.assertEqual(merged.describe()["base_url"], "https://personal.example/v1")
        self.assertEqual(merged._secrets, {"fixture": "user-secret"})
        self.assertNotIn("user-secret", json.dumps(merged.public()))
        self.assertEqual(before, (self.project.read_bytes(), self.user.read_bytes()))

    def test_thin_project_policy_can_take_all_endpoint_and_model_choices_from_user(self):
        project_folder = self.root / "project"
        project_folder.mkdir()
        self.project = project_folder / "policy.json"
        self.write(self.project, {"name": "policy", "harness": "pi", "trusted_local_execution": True,
                                 "command": ["node", "./adapter.js"], "timeout": 42})
        data = profile_data()
        self.write(self.user, {k: data[k] for k in ("models", "endpoints", "default_model")})
        profile = ExecutionProfile.load(self.project, self.user)
        self.assertEqual(profile.name, "policy")
        self.assertEqual(profile.timeout, 42)
        self.assertEqual(profile.command, ("node", str((project_folder / "adapter.js").resolve())))
        self.assertEqual(profile.select(None).model, "vendor/family/test-model")

    def test_new_user_endpoint_is_added_without_changing_project_endpoint_or_default(self):
        self.write(self.user, {
            "endpoints": {"personal": {"base_url": "https://personal.example/v1",
                                       "api": "openai-completions", "api_key_env": "USER_KEY"}},
            "models": [{"key": "personal", "model": "personal-model", "endpoint": "personal",
                        "workflows": ["literary-translation"]}],
        })
        with patch.dict(os.environ, {"TEST_INFERENCE_KEY": "project-secret", "USER_KEY": "user-secret"}):
            profile = ExecutionProfile.load(self.project, self.user)
        self.assertEqual(profile.default_model, "choice")
        self.assertEqual(profile.describe("choice")["base_url"], "https://inference.example.test/v1")
        self.assertEqual(profile.describe("personal")["base_url"], "https://personal.example/v1")
        self.assertEqual(profile._secrets, {"fixture": "project-secret", "personal": "user-secret"})

    def test_user_changes_are_snapshotted_and_merged_revision_tracks_effective_configuration(self):
        self.write(self.user, {"models": [{"key": "choice", "model": "first", "endpoint": "fixture"}]})
        with patch.dict(os.environ, {"TEST_INFERENCE_KEY": "first-secret"}):
            first = ExecutionProfile.load(self.project, self.user)
        self.write(self.user, {"models": [{"key": "choice", "model": "second", "endpoint": "fixture"}]})
        with patch.dict(os.environ, {"TEST_INFERENCE_KEY": "second-secret"}):
            second = ExecutionProfile.load(self.project, self.user)
        self.assertEqual(first.select(None).model, "first")
        self.assertEqual(first.redact("first-secret"), "[REDACTED]")
        self.assertNotEqual(first.revision, second.revision)
        self.write(self.user, {})
        self.assertEqual(ExecutionProfile.load(self.project).revision,
                         ExecutionProfile.load(self.project, self.user).revision)

    def test_empty_overlay_does_not_change_codex_configuration_or_revision(self):
        self.write(self.project, {"name": "codex", "harness": "codex", "default_model": "sol",
                                 "models": [{"key": "sol", "model": "gpt-6-sol"}]})
        self.write(self.user, {"endpoints": {}})
        self.assertEqual(ExecutionProfile.load(self.project).revision,
                         ExecutionProfile.load(self.project, self.user).revision)

    def test_user_cannot_override_execution_policy_or_embed_credentials(self):
        for key, value in (("harness", "codex"), ("command", ["untrusted"]), ("timeout", 999),
                           ("trusted_local_execution", False), ("name", "replacement"),
                           ("api_key", "do-not-print-this")):
            with self.subTest(key=key):
                self.write(self.user, {key: value})
                with self.assertRaisesRegex(ValueError, "user execution profile") as caught:
                    ExecutionProfile.load(self.project, self.user)
                self.assertNotIn("do-not-print-this", str(caught.exception))

    def test_partial_replacements_duplicate_models_and_invalid_references_fail(self):
        for data in (
            {"endpoints": {"fixture": {"base_url": "https://replacement.example/v1"}}},
            {"models": [{"key": "choice", "model": "missing-endpoint"}]},
            {"models": [profile_data()["models"][0]] * 2},
            {"models": [{"key": "choice", "model": "new", "endpoint": "unknown"}]},
            {"default_model": "unavailable"},
            {"endpoints": {"fixture": {"base_url": "https://user:do-not-print-this@example.com/v1",
                                      "api": "openai-completions", "api_key_env": "USER_KEY"}}},
        ):
            with self.subTest(data=list(data)):
                self.write(self.user, data)
                with self.assertRaises(ValueError) as caught:
                    ExecutionProfile.load(self.project, self.user)
                self.assertNotIn("do-not-print-this", str(caught.exception))
        data = profile_data()
        data["models"] *= 2
        self.write(self.project, data)
        self.write(self.user, {})
        with self.assertRaisesRegex(ValueError, "unique"):
            ExecutionProfile.load(self.project, self.user)

    def test_explicit_missing_files_malformed_json_and_duplicate_json_keys_fail_closed(self):
        with self.assertRaises(FileNotFoundError):
            ExecutionProfile.load(self.project, self.user)
        for text in ('{"default_model": "one", "default_model": "two"}',
                     '{"endpoints":{"same":{},"same":{}}}', '{"default_model":"do-not-print-this",'):
            self.user.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                ExecutionProfile.load(self.project, self.user)
            self.assertNotIn("do-not-print-this", str(caught.exception))
        with self.assertRaisesRegex(ValueError, "requires --execution-profile"):
            ExecutionProfile.load(None, self.user)
        self.assertIsNone(ExecutionProfile.load(None))

    def test_cli_creation_selects_user_model_and_preserves_both_paths_in_next_command(self):
        self.write(self.user, {"default_model": "personal",
                               "models": [{"key": "personal", "model": "personal-model", "endpoint": "fixture",
                                           "workflows": ["literary-translation"]}]})
        source = self.root / "source.md"
        source.write_bytes(b"# Manuscript\n\nA short story.\n")
        with WorkflowService(self.root / "server") as service:
            work_id = service.create_work(source, "en")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = cli.main(["--server-root", str(self.root / "server"),
                             "--execution-profile", str(self.project),
                             "--user-execution-profile", str(self.user),
                             "works", "prepare", work_id])
        self.assertEqual(code, 0, output.getvalue())
        self.assertIn('"model": "personal-model"', output.getvalue())
        self.assertIn(f'--execution-profile "{self.project}"', output.getvalue())
        self.assertIn(f'--user-execution-profile "{self.user}" step ', output.getvalue())
        with contextlib.redirect_stderr(io.StringIO()) as error:
            code = cli.main(["--user-execution-profile", str(self.user), "models"])
        self.assertEqual(code, 1)
        self.assertIn("requires --execution-profile", error.getvalue())


class StdioTransportTests(unittest.TestCase):
    def test_eof_and_bad_json_fail_without_leaking_stdout_or_stderr(self):
        for source, error in (
            ("import sys; print('private credential', file=sys.stderr)", "closed its protocol output"),
            ("print('private credential')", "malformed JSONL"),
            ("print('[]')", "malformed JSONL"),
        ):
            with self.subTest(error=error):
                transport = StdioTransport([sys.executable, "-u", "-c", source],
                                           cwd=Path.cwd(), timeout=5, name="fixture")
                with self.assertRaisesRegex(RuntimeError, error) as caught:
                    with transport:
                        process = transport.process
                        transport.receive()
                self.assertNotIn("private credential", str(caught.exception))
                self.assertIsNotNone(process.poll())
                self.assertTrue(process.stdout.closed)

    def test_callback_failure_and_deadline_reap_the_child(self):
        for fail in (True, False):
            transport = StdioTransport([sys.executable, "-u", "-c", "import time; time.sleep(30)"],
                                       cwd=Path.cwd(), timeout=0.2, name="fixture")
            with self.subTest(callback_failure=fail):
                with self.assertRaises((RuntimeError, TimeoutError)):
                    with transport:
                        process = transport.process
                        if fail:
                            raise RuntimeError("callback failed")
                        transport.receive()
                self.assertIsNotNone(process.poll())
                self.assertTrue(process.stdin.closed)


class PiTransportTests(unittest.TestCase):
    SERVER = r'''
import json, os, sys, time
if "--version" in sys.argv:
    print("0.73.1", file=sys.stderr)
    sys.exit()
def send(message):
    print(json.dumps(message), flush=True)
assert os.environ["MANUSCRIPT_PI_API_KEY"] == "fixture-secret"
schema = json.load(open(os.environ["MANUSCRIPT_PI_SCHEMA"]))
assert schema["properties"]["outcome"]["enum"] == ["needs_human_input", "completed", "blocked"]
for line in sys.stdin:
    request = json.loads(line)
    mode = request.get("message", "").split("\n")[0]
    send({"type": "agent_start"})
    if mode == "timeout":
        time.sleep(30)
    if mode == "invalid-json":
        print("not JSON", flush=True)
        continue
    if mode == "rejected":
        send({"type": "response", "id": request["id"], "success": False})
        continue
    if mode == "provider-error":
        send({"type": "message_end", "message": {"role": "assistant", "stopReason": "error",
                                                "errorMessage": "fixture-secret"}})
    if mode not in ("no-result", "provider-error"):
        value = dict(outcome="blocked", message="Fixture result", state_path=None, work_record=None,
                     output_path=None, gate=None, review_path=None, binding_path=None)
        if mode == "invalid-result":
            value["gate"] = "unauthorized-gate"
        for i in range(2 if mode == "duplicate-result" else 1):
            send({"type": "tool_execution_start", "toolName": "workflow_result", "toolCallId": str(i)})
            send({"type": "tool_execution_end", "toolName": "workflow_result", "toolCallId": str(i),
                  "isError": False, "result": {"details": {"workflow_result": value}}})
    # Notifications deliberately precede the prompt response.
    send({"type": "response", "id": request["id"], "command": "prompt", "success": True})
    send({"type": "agent_end"})
'''

    def call(self, mode, timeout=10):
        with tempfile.TemporaryDirectory() as folder:
            runtime = PiRuntime([sys.executable, "-u", "-c", self.SERVER], timeout,
                                endpoint={"base_url": "https://example.test/v1", "api": "openai-completions"},
                                model="vendor/family/test-model", api_key="fixture-secret")
            events, sessions = [], []
            result = runtime.run(Request(Path(folder), mode, None, "incompatible-old-thread", result_schema([])),
                                 lambda *event: events.append(event), sessions.append)
            return result, events, sessions

    def test_structured_tool_result_and_interleaved_events(self):
        result, events, sessions = self.call("success")
        self.assertEqual(result["outcome"], "blocked")
        self.assertEqual(len(sessions), 1)
        self.assertTrue(sessions[0].startswith("pi-"))
        self.assertNotEqual(sessions[0], "incompatible-old-thread")
        self.assertEqual(events[0][0], "runtime.turn_started")
        self.assertEqual(events[-1][0], "runtime.turn_completed")
        self.assertNotIn("fixture-secret", json.dumps(events))

    def test_malformed_missing_duplicate_and_failed_results_are_not_success(self):
        for mode, error in (("invalid-json", "malformed JSONL"), ("no-result", "without calling"),
                            ("invalid-result", "stage schema"), ("duplicate-result", "duplicate"),
                            ("rejected", "rejected"), ("provider-error", "inference failed")):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex((ValueError, RuntimeError), error) as caught:
                    self.call(mode)
                self.assertNotIn("fixture-secret", str(caught.exception))

    def test_active_turn_deadline_terminates_the_process(self):
        with self.assertRaisesRegex(TimeoutError, "execution timeout"):
            self.call("timeout", timeout=1)

    @unittest.skipUnless(PI_CLI.is_file(), "Install the pinned Pi evaluation package for the local RPC check.")
    def test_real_pinned_pi_with_local_inference_fixture(self):
        """Exercise the installed Pi, extension schema, and model ID without external inference."""
        requests = []
        value = dict(outcome="blocked", message="Local inference fixture", state_path=None, work_record=None,
                     output_path=None, gate=None, review_path=None, binding_path=None)

        class Provider(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(body)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                chunks = [
                    {"choices": [{"index": 0, "delta": {"role": "assistant", "tool_calls": [
                        {"index": 0, "id": "call_fixture", "type": "function",
                         "function": {"name": "workflow_result", "arguments": json.dumps(value)}}]},
                                  "finish_reason": None}]},
                    {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
                     "usage": {"prompt_tokens": 100, "completion_tokens": 25, "total_tokens": 125}},
                ]
                for chunk in chunks:
                    data = {"id": "fixture", "object": "chat.completion.chunk", "created": 1,
                            "model": body["model"], **chunk}
                    self.wfile.write(("data: " + json.dumps(data) + "\n\n").encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()

        server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                runtime = PiRuntime(["node", str(PI_CLI)], 30,
                                    endpoint={"base_url": f"http://127.0.0.1:{server.server_port}/v1",
                                              "api": "openai-completions"},
                                    model="vendor/family/test-model", api_key="local-fixture")
                response = runtime.run(Request(Path(folder), "Return a blocked workflow result.", None, None,
                                               result_schema([])), lambda *args: None, lambda *args: None)
            self.assertEqual(response, value)
            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0]["model"], "vendor/family/test-model")
            tool = next(t["function"] for t in requests[0]["tools"] if t["function"]["name"] == "workflow_result")
            self.assertEqual(tool["parameters"]["properties"]["outcome"]["enum"],
                             ["needs_human_input", "completed", "blocked"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
