"""Run: python -m unittest workflow.tests.test_workflow -v."""

import json
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

from ..src.engine import DEFAULT_DEFINITION, Engine, RESULT_SCHEMA, definition_at
from ..src.runtime import CodexRuntime, Request
from ..src.storage import digest, now
from . import run_e2e


def result(outcome="completed", **fields):
    return dict(outcome=outcome, message="Saved operation result.", state_path=None,
                work_record=None, output_path=None, gate=None, review_path=None,
                binding_path=None) | fields


class ScriptedRuntime:
    """A deterministic test double, never presented as a model translation."""

    def __init__(self, action):
        self.action = action

    def run(self, request, on_event, on_thread):
        on_thread("test-thread")
        on_event("test.turn", {"model": request.model})
        return self.action(request)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / "original.md"
        self.source.write_bytes("# 故事\n\n他回来了。\n".encode())
        self.engine = Engine.create(self.base / "run with spaces", self.source, "zh")
        self.addCleanup(lambda: self.engine.close())
        self.workspace = self.engine.workspace

    def write(self, relative, content):
        path = self.workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, indent=2) + "\n"
        path.write_bytes(content.encode())
        return relative

    def preparation(self, request):
        source = self.engine.root / "input" / self.source.name
        content = source.read_bytes()
        parts = getattr(self, "parts", [content.decode()])
        chapters = [{
            "chapter_id": "story" if len(parts) == 1 else f"chapter-{index}", "order": index, "source_number": None,
            "title": "故事", "role": "standalone", "file": "chapters/0001.md",
            "sha256": digest(part.encode()), "source_spans": [{"source_id": "original", "locator": f"Source unit {index}"}],
            "status": "verified",
        } for index, part in enumerate(parts, 1)]
        for index, chapter in enumerate(chapters, 1):
            chapter["file"] = f"chapters/{index:04d}.md"
        manifest = {
            "schema_version": 1, "work_id": "story", "revision": "r0001", "status": "verified",
            "created_at": now(), "sources": [{
                "source_id": "original", "locator": str(source), "format": "markdown",
                "identity": {"kind": "sha256", "value": digest(content)},
            }],
            "scope": {"kind": "whole_work", "chapter_ids": [c["chapter_id"] for c in chapters]},
            "chapters": chapters, "assets": [],
            "extraction": {"tool": "test", "method": "Exact fixture copy", "normalization_notes": []},
            "verification": {"performed_by": "test", "verified_at": now(),
                             "coverage_complete": True, "issues": []},
        }
        work = {
            "schema_version": 1, "work_id": "story", "record_revision": 1, "updated_at": now(),
            "metadata": {"title": "Story", "authors": [], "source_language": "zh",
                         "work_type": "fiction", "genre": None, "edition": None},
            "discovery": {"location_kind": "file", "location": str(source), "recursive": False,
                          "selection_status": "confirmed", "notes": []},
            "preparation": {"status": "ready", "current_revision": "r0001", "blockers": []},
            "workflows": {name: {"status": "not_started", "basis_revision": None, "scope": None,
                                 "operation": None, "state_locator": None, "updated_at": None}
                          for name in ("literary-editing", "literary-translation",
                                       "literary-agent-querying", "format-manuscript")},
        }
        for chapter, part in zip(chapters, parts):
            self.write("prepared/story/revisions/r0001/" + chapter["file"], part)
        self.write("prepared/story/revisions/r0001/manifest.json", manifest)
        return result(work_record=self.write("prepared/story/work.json", work))

    def prepare(self):
        self.engine.advance(ScriptedRuntime(self.preparation))

    def sheet(self, revision="1", resolved=False):
        return {
            "schema_version": "1.0", "sheet_id": "map-story", "revision": revision,
            "title": "Passage map", "bindings": [{"label": "Chapter", "value": "story"}],
            "decisions": [
                {"id": "approve", "command": "approve", "label": "Approve", "requires_note": False, "effect": "resolve"},
                {"id": "revise", "command": "revise", "label": "Revise", "requires_note": True, "effect": "reopen"},
            ],
            "items": [{
                "id": "PM001", "summary": "One passage: complete story",
                "details": [{"label": "Original", "value": "他回来了。"}],
                "status": "resolved" if resolved else "pending", "status_label": "Reviewed" if resolved else "Pending",
                "allowed_decisions": ["approve", "revise"], "dependencies": [],
                "response": {"decision": "approve", "note": "", "date": now()} if resolved else None,
            }],
            "gate": {"status": "awaiting-approval", "closure_required": True,
                     "final_closure": "pending", "ready_state": "not-ready"},
            "presentation": {"mode": "all", "note_label": "Feedback", "note_placeholder": "Required for revision",
                             "submit_label": "Submit"},
            "submission": {"instruction": "Review this map.", "rules": ["Do not translate before closure."],
                           "closure_command": "confirm final closure", "closure_label": "Confirm"},
        }

    def map_gate(self, revision="1", resolved=False):
        return result(
            "needs_human_input", message="Review the complete story passage boundary.",
            gate="passage_map", state_path=self.write("translation/state.md", "Passage map pending.\n"),
            binding_path=self.write("translation/map-proposal.md", "PM001: entire source story.\n"),
            review_path=self.write("translation/map-review.json", self.sheet(revision, resolved)),
        )

    def approve_map(self):
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        gate = self.engine.state()["gate"]["id"]
        self.engine.reply(gate, "PM001 approve")
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate("2", True)))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm final closure")

    def sanity_gate(self, request):
        return result(
            "needs_human_input", gate="chapter_sanity", message="He came back.\nNo textual changes proposed.",
            state_path=self.write("translation/sanity.md", "No textual changes proposed\n"),
            binding_path=self.write("translation/assembled.md", "He came back.\n"),
        )

    def translation(self, request):
        self.write("translation/glossary.md", "# Glossary\n")
        self.write("translation/voice.md", "# Voice\n")
        return result(state_path=self.write("translation/state.md", "Chapter finalized.\n"),
                      output_path=self.write("translation/translated_english/story.md", "He came back.\n"))

    def complete_translation(self):
        self.prepare()
        self.approve_map()
        self.engine.advance(ScriptedRuntime(self.sanity_gate))
        self.engine.reply(self.engine.state()["gate"]["id"], "approve chapter")
        self.engine.advance(ScriptedRuntime(self.translation))

    def test_restart_gates_acceptance_and_export_preserve_original(self):
        original = self.source.read_bytes()
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        gate_id = self.engine.state()["gate"]["id"]
        self.engine.close()
        self.engine = Engine(self.base / "run with spaces")
        self.assertEqual(self.engine.state()["gate"]["id"], gate_id)
        with self.assertRaisesRegex(ValueError, "WAITING_FOR_HUMAN"):
            self.engine.advance(ScriptedRuntime(lambda r: result()))
        with self.assertRaisesRegex(ValueError, "unresolved"):
            self.engine.reply(gate_id, "confirm final closure")
        self.engine.reply(gate_id, "PM001 approve")
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.reply(gate_id, "PM001 approve")
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate("2", True)))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm final closure")
        self.engine.advance(ScriptedRuntime(self.sanity_gate))
        self.engine.reply(self.engine.state()["gate"]["id"], "approve chapter")
        self.engine.advance(ScriptedRuntime(self.translation))
        self.assertEqual(self.engine.state()["status"], "WAITING_FOR_ACCEPTANCE")
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.accept("incorrect-acceptance")
        self.engine.accept(self.engine.state()["acceptance_id"])
        state = self.engine.advance(None)
        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual((Path(state["export_path"]) / "0001.md").read_text(), "He came back.\n")
        self.assertEqual(self.source.read_bytes(), original)
        self.assertTrue(any(event["kind"] == "review.received" for event in self.engine.store.events()))

    def test_cannot_complete_translation_without_domain_gates(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "map closure"):
            self.engine.advance(ScriptedRuntime(self.translation))
        self.assertEqual(self.engine.state()["status"], "FAILED")
        self.assertEqual(self.engine.state()["outputs"], [])
        self.engine.recover()
        self.assertEqual(self.engine.state()["stage"], "translate")
        self.assertIsNone(self.engine.state()["thread_id"])

    def test_second_chapter_has_new_context_and_cannot_inherit_first_chapter_gates(self):
        self.engine.close()
        self.parts = ["# 第一章\n\n他回来了。\n", "# 第二章\n\n她走了。\n"]
        self.source.write_bytes("".join(self.parts).encode())
        self.engine = Engine.create(self.base / "two-chapters", self.source, "zh")
        self.workspace = self.engine.workspace
        self.complete_translation()
        state = self.engine.state()
        self.assertEqual(state["status"], "READY")
        self.assertEqual(state["chapter_index"], 1)
        self.assertIsNone(state["thread_id"])
        self.assertIsNone(state["map_approval"])
        self.assertIsNone(state["sanity_approval"])
        self.assertEqual(len(state["outputs"]), 1)
        self.assertEqual(set(state["continuity"]), {"glossary", "voice"})
        with self.assertRaisesRegex(ValueError, "map closure"):
            self.engine.advance(ScriptedRuntime(self.translation))

    def test_malformed_result_is_persisted_as_failure(self):
        with self.assertRaisesRegex(ValueError, "Invalid runtime result"):
            self.engine.advance(ScriptedRuntime(lambda request: {"outcome": "completed"}))
        self.assertEqual(self.engine.state()["status"], "FAILED")
        self.assertEqual(self.engine.state()["stage"], "prepare")

    def test_empty_sanity_diff_still_requires_explicit_approval(self):
        self.prepare()
        self.approve_map()
        self.engine.advance(ScriptedRuntime(self.sanity_gate))
        self.engine.reply(self.engine.state()["gate"]["id"], "continue")
        self.assertIsNone(self.engine.state()["sanity_approval"])
        with self.assertRaisesRegex(ValueError, "chapter approval"):
            self.engine.advance(ScriptedRuntime(self.translation))

    def test_agent_cannot_claim_resolved_items_without_human_receipts(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "no matching human"):
            self.engine.advance(ScriptedRuntime(lambda request: self.map_gate("1", True)))
        self.assertIsNone(self.engine.state()["map_approval"])

    def test_changed_review_and_changed_source_block_responses(self):
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        gate_id = self.engine.state()["gate"]["id"]
        self.write("translation/map-proposal.md", "Changed boundary\n")
        with self.assertRaisesRegex(ValueError, "Review changed"):
            self.engine.reply(gate_id, "PM001 approve")
        self.write("prepared/story/revisions/r0001/chapters/0001.md", "Tampered original\n")
        with self.assertRaisesRegex(ValueError, "Prepared source changed"):
            self.engine.recover(refresh_gate=True)

    def test_wrong_revision_envelope_is_rejected(self):
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        sheet = self.sheet()
        payload = "\n".join([sheet["submission"]["instruction"], "Approval sheet: map-story",
                             "Revision: old", *sheet["submission"]["rules"], "", "PM001 approve"])
        with self.assertRaises(ValueError):
            self.engine.reply(self.engine.state()["gate"]["id"], payload)
        self.assertEqual(self.engine.state()["receipts"], [])

    def test_changed_proposal_cannot_reuse_old_disposition(self):
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        self.engine.reply(self.engine.state()["gate"]["id"], "PM001 approve")

        def changed(request):
            output = self.map_gate("2", True)
            sheet = self.sheet("2", True)
            sheet["items"][0]["details"][0]["value"] = "A different boundary"
            self.write(output["review_path"], sheet)
            return output

        with self.assertRaisesRegex(ValueError, "no matching human"):
            self.engine.advance(ScriptedRuntime(changed))

    def test_source_failure_and_path_escape_do_not_promote(self):
        def invalid(request):
            output = self.preparation(request)
            path = self.workspace / output["work_record"]
            work = json.loads(path.read_text())
            work["preparation"]["blockers"] = ["Missing page"]
            path.write_text(json.dumps(work), encoding="utf-8")
            return output

        with self.assertRaisesRegex(ValueError, "blockers"):
            self.engine.advance(ScriptedRuntime(invalid))
        self.assertEqual(self.engine.state()["stage"], "prepare")
        self.engine.recover()
        with self.assertRaisesRegex(ValueError, "escapes"):
            self.engine.advance(ScriptedRuntime(lambda r: result(work_record="../outside.json")))

    def test_failure_keeps_receipt_and_restart_requires_explicit_recovery(self):
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        self.engine.reply(self.engine.state()["gate"]["id"], "PM001 approve")
        receipt = self.engine.state()["next_input"]["id"]

        def fail(request):
            raise RuntimeError("Interrupted provider")

        with self.assertRaisesRegex(RuntimeError, "Interrupted"):
            self.engine.advance(ScriptedRuntime(fail))
        self.engine.recover()
        self.assertEqual(self.engine.state()["next_input"]["id"], receipt)
        self.assertEqual(len(self.engine.state()["receipts"]), 1)

    def test_export_conflict_is_not_overwritten(self):
        self.complete_translation()
        self.engine.accept(self.engine.state()["acceptance_id"])
        export = self.engine.root / "export"
        export.mkdir()
        (export / "0001.md").write_bytes(b"User file")
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            self.engine.advance(None)
        self.assertEqual((export / "0001.md").read_bytes(), b"User file")

    def test_run_lock_excludes_another_process_handle(self):
        second = Engine(self.engine.root)
        try:
            with self.engine.store.locked():
                with self.assertRaisesRegex(ValueError, "Another process"):
                    with second.store.locked():
                        self.fail("Acquired an already-held lock")
        finally:
            second.close()

    def test_reject_unsupported_language_or_incomplete_skill_bundle(self):
        config = json.loads(DEFAULT_DEFINITION.read_text())
        path = self.base / "definition.json"
        config["target_language"] = "fr-FR"
        path.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, "US English"):
            definition_at(path)
        config["target_language"] = "en-US"
        config["agents"]["translate"]["skills"].remove("review-approval-sheet")
        path.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, "bundle"):
            definition_at(path)

    def e2e_case(self):
        spec = json.loads(run_e2e.DEFAULT_CASE.read_text(encoding="utf-8"))
        spec["case_id"] = "fixture-e2e"
        spec["input"]["manuscript"] = {
            "file": str(self.source), "format": "markdown", "sha256": digest(self.source.read_bytes()),
        }
        spec["input"]["workflow_definition"] = str(DEFAULT_DEFINITION)
        spec["input"]["task_specification"] = "task.md"
        spec["source_inventory"] = {"title": "Synthetic fixture"}
        (self.base / "task.md").write_text("Translate the complete synthetic fixture.", encoding="utf-8")
        path = self.base / "case.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        case = run_e2e.load_case(path)
        run_e2e.bind_case(self.engine, case, {"executable": "test-only", "version": "scripted fixture"})
        return case

    def test_e2e_launcher_interactive_loop_and_honest_report(self):
        case = self.e2e_case()
        actions = iter([
            self.preparation, lambda r: self.map_gate(),
            lambda r: self.map_gate("2", True), self.sanity_gate, self.translation,
        ])
        prompts = []

        def action(request):
            prompts.append(request.prompt)
            return next(actions)(request)

        replies = iter(["PM001 approve", ".", "confirm final closure", ".", "approve chapter", ".",
                        "accept", "skip", "skip", "skip", "skip"])
        runtime = run_e2e.CaseRuntime(ScriptedRuntime(action), case["task"])
        with contextlib.redirect_stdout(io.StringIO()):
            code = run_e2e.drive(self.engine, case, runtime, input_fn=lambda _: next(replies))
        self.assertEqual(code, 2)  # Execution completed, manual checks not claimed as passed.
        self.assertTrue(all("Translate the complete synthetic fixture." in prompt for prompt in prompts))
        report = json.loads((self.engine.root / "e2e-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["workflow_status"], "COMPLETED")
        self.assertEqual(report["e2e_status"], "needs-review")
        checks = {c["id"]: c for c in report["checks"]}
        for name in ("recovery", "stale-response", "source-integrity", "export-provenance"):
            self.assertEqual(checks[name]["status"], "passed")
        self.assertEqual(checks["domain-gates"]["status"], "not-checked")
        self.assertEqual(report["literary_quality"]["status"], "not-checked")
        self.assertEqual((self.engine.root / "candidate.en.txt").read_text(), "He came back.\n")
        self.assertEqual(len(self.engine.state()["receipts"]), 3)
        # A completed run can finish its human evidence review without another model call.
        evidence = iter(["pass", "Synthetic test evidence"] * 4)
        with contextlib.redirect_stdout(io.StringIO()):
            code = run_e2e.drive(self.engine, case, None, input_fn=lambda _: next(evidence))
        self.assertEqual(code, 0)
        report = json.loads((self.engine.root / "e2e-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["e2e_status"], "passed")
        self.assertEqual(report["literary_quality"]["status"], "not-checked")

    def test_e2e_launcher_eof_preserves_gate_and_can_bind_resume(self):
        case = self.e2e_case()
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda r: self.map_gate()))
        gate_id = self.engine.state()["gate"]["id"]

        def eof(_):
            raise EOFError

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_e2e.drive(self.engine, case, None, input_fn=eof), 2)
        self.assertEqual(self.engine.state()["gate"]["id"], gate_id)
        self.assertEqual(self.engine.state()["receipts"], [])
        run_e2e.bind_case(self.engine, case, {"version": "test"}, resume=True)
        changed = dict(case, task_sha256="changed")
        with self.assertRaisesRegex(ValueError, "Changed task_sha256"):
            run_e2e.bind_case(self.engine, changed, {}, resume=True)

    def test_e2e_report_detects_corrupt_export_and_does_not_write_candidate(self):
        case = self.e2e_case()
        self.complete_translation()
        self.engine.accept(self.engine.state()["acceptance_id"])
        self.engine.advance(None)
        (self.engine.root / "export/0001.md").write_bytes(b"Unaccepted replacement")
        report = run_e2e.write_report(self.engine, case)
        self.assertEqual(report["e2e_status"], "failed")
        self.assertEqual(report["automated_checks"]["export-provenance"]["status"], "failed")
        run_e2e.collect_candidate(self.engine, report)
        self.assertFalse((self.engine.root / "candidate.en.txt").exists())

    def test_e2e_case_check_has_no_run_or_runtime_side_effects(self):
        case = self.e2e_case()
        unused = self.base / "unused-run"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run_e2e.main(["--case", case["case_path"], "--check-case", "--run-dir", str(unused)])
        self.assertEqual(code, 0)
        self.assertFalse(unused.exists())
        self.source.write_bytes(b"Changed source")
        with self.assertRaisesRegex(ValueError, "manuscript hash"):
            run_e2e.load_case(Path(case["case_path"]))


class CodexTransportTests(unittest.TestCase):
    SERVER = r'''
import json, sys
def send(value):
    print(json.dumps(value), flush=True)
for line in sys.stdin:
    m = json.loads(line)
    method = m.get("method")
    if method == "initialize":
        send({"id": m["id"], "result": {"userAgent": "fixture"}})
    elif method in ("thread/start", "thread/resume"):
        assert m["params"]["sandbox"] == "workspace-write"
        assert m["params"]["approvalPolicy"] == "never"
        send({"id": m["id"], "result": {"thread": {"id": "thread-1"}}})
    elif method == "turn/start":
        assert m["params"]["outputSchema"]["type"] == "object"
        assert not m["params"]["sandboxPolicy"]["networkAccess"]
        send({"id": 88, "method": "item/commandExecution/requestApproval",
              "params": {"command": "fixture denied command"}})
        answer = json.loads(sys.stdin.readline())
        assert answer["result"]["decision"] == "decline"
        # Notifications intentionally precede the RPC response.
        send({"method": "item/completed", "params": {"threadId": "thread-1", "turnId": "turn-1",
              "item": {"type": "agentMessage", "text": json.dumps({"outcome": "blocked"})}}})
        send({"method": "turn/completed", "params": {"threadId": "thread-1",
              "turn": {"id": "turn-1", "status": "completed"}}})
        send({"id": m["id"], "result": {"turn": {"id": "turn-1"}}})
'''

    def test_stdio_protocol_start_resume_interleaving_and_denial(self):
        with tempfile.TemporaryDirectory() as temp:
            for thread_id in (None, "thread-1"):
                with self.subTest(thread_id=thread_id):
                    events, threads = [], []
                    runtime = CodexRuntime([sys.executable, "-u", "-c", self.SERVER], timeout=10)
                    response = runtime.run(Request(Path(temp), "Fixture", None, thread_id, RESULT_SCHEMA),
                                           lambda *event: events.append(event), threads.append)
                    self.assertEqual(response, {"outcome": "blocked"})
                    self.assertEqual(threads, ["thread-1"])
                    self.assertTrue(any(event[0] == "runtime.request" for event in events))

    def test_timeout_terminates_process(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = CodexRuntime([sys.executable, "-u", "-c", "import time; time.sleep(30)"], timeout=0.1)
            with self.assertRaises(TimeoutError):
                runtime.run(Request(Path(temp), "", None, None, RESULT_SCHEMA), lambda *args: None, lambda t: None)


if __name__ == "__main__":
    unittest.main()
