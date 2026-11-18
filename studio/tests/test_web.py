"""Run: python -m unittest studio.tests.test_web -v (requires studio/requirements.txt)."""

import base64
import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote

from workflow.src.execution import ExecutionProfile
from workflow.src.service import WorkflowService
from workflow.src.storage import Store, digest, now
from workflow.tests.test_execution import profile_data
from workflow.tests.interior_fixture import apply_target, proposal_for
from workflow.tests.analysis_fixture import analyze

HAS_WEB = importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx")
ORIGIN = "http://127.0.0.1:8765"


@unittest.skipUnless(HAS_WEB, "Install studio/requirements.txt.")
class StartupProfileTests(unittest.TestCase):
    def test_server_entrypoint_exposes_merged_startup_snapshot_and_user_model_selection(self):
        from fastapi.testclient import TestClient
        from studio.server.__main__ import main

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            project, user = root / "project.json", root / "user.json"
            project.write_text(json.dumps(profile_data()), encoding="utf-8")
            overlay = {"default_model": "personal",
                       "models": [{"key": "personal", "model": "personal-model", "endpoint": "fixture",
                                   "workflows": ["literary-translation"]}]}
            user.write_text(json.dumps(overlay), encoding="utf-8")
            with patch("studio.server.__main__.uvicorn.run") as launch:
                main(["--server-root", str(root / "server"), "--execution-profile", str(project),
                      "--user-execution-profile", str(user)])
            app = launch.call_args.args[0]
            overlay["models"][0]["model"] = "changed-after-startup"
            user.write_text(json.dumps(overlay), encoding="utf-8")
            with TestClient(app, base_url=ORIGIN) as client:
                catalog = client.get("/api/execution").json()
                self.assertEqual(catalog["default_model"], "personal")
                self.assertEqual([m["model_key"] for m in catalog["models"]], ["choice", "personal"])
                self.assertEqual(catalog["models"][1]["model"], "personal-model")
                self.assertNotIn("api_key_env", json.dumps(catalog))
                work = client.post("/api/works", headers={"Origin": ORIGIN}, json={
                    "upload": {"name": "story.md", "data": base64.b64encode(b"# Story\n\nText.\n").decode()},
                    "manuscript_language": "en"}).json()
                created = client.post("/api/runs", headers={"Origin": ORIGIN}, json={
                    "template_id": "literary-translation-v1", "work_id": work["id"], "start": False})
                self.assertEqual(created.status_code, 200, created.text)
                self.assertEqual(created.json()["execution"]["model"], "personal-model")
                self.assertFalse(created.json()["worker"]["active"])

    def test_server_rejects_overlay_without_project_before_starting(self):
        from studio.server.__main__ import main

        with patch("studio.server.__main__.uvicorn.run") as launch:
            with contextlib.redirect_stderr(io.StringIO()) as error:
                with self.assertRaises(SystemExit) as caught:
                    main(["--user-execution-profile", "not-read.json"])
            self.assertEqual(caught.exception.code, 2)
            self.assertIn("requires --execution-profile", error.getvalue())
            launch.assert_not_called()


def context(request):
    return json.loads(request.prompt[request.prompt.index('{\n  "stage"'):])  # The context JSON follows the prompt.


def write(root, relative, content):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)).encode())
    return relative


def result(outcome="completed", **fields):
    return dict(outcome=outcome, message="Saved operation result.", state_path=None, work_record=None,
                output_path=None, gate=None, review_path=None, binding_path=None) | fields


def prepare(request):
    ctx = context(request)
    work_id, source = ctx["required_work_id"], Path(ctx["source"])
    text = source.read_bytes()
    front = "# 故事\n".encode()  # Every prepared revision starts with a front-matter unit.
    chapters = [
        {"chapter_id": "front-matter", "order": 1, "source_number": None, "title": "故事", "role": "front_matter",
         "file": "chapters/0001.md", "sha256": digest(front),
         "source_spans": [{"source_id": "original", "locator": "Title"}], "status": "verified"},
        {"chapter_id": "story", "order": 2, "source_number": None, "title": "故事", "role": "standalone",
         "file": "chapters/0002.md", "sha256": digest(text),
         "source_spans": [{"source_id": "original", "locator": "Whole file"}], "status": "verified"}]
    base = f"prepared/{work_id}/"
    write(request.cwd, base + "revisions/r0001/chapters/0001.md", front.decode())
    write(request.cwd, base + "revisions/r0001/chapters/0002.md", text.decode())
    write(request.cwd, base + "revisions/r0001/manifest.json", {
        "schema_version": 1, "work_id": work_id, "revision": "r0001", "status": "verified", "created_at": now(),
        "sources": [{"source_id": "original", "locator": str(source), "format": "markdown",
                     "identity": {"kind": "sha256", "value": digest(text)}}],
        "scope": {"kind": "whole_work", "chapter_ids": ["front-matter", "story"]}, "chapters": chapters, "assets": [],
        "extraction": {"tool": "test", "method": "Exact fixture copy", "normalization_notes": []},
        "verification": {"performed_by": "test", "verified_at": now(), "coverage_complete": True, "issues": []}})
    work = {"schema_version": 2, "work_id": work_id, "record_revision": 1, "updated_at": now(),
            "metadata": {"title": "Story", "subtitle": None, "contributors": [], "original_language": None, "manuscript_language": "zh", "work_type": "fiction", "form": None, "genres": [], "audience": None, "keywords": [], "description": None, "edition": {"label": None, "status": None}, "series": {"name": None, "position": None, "relationship": None}, "extent": None}, "metadata_provenance": {},
            "discovery": {"location_kind": "file", "location": str(source), "recursive": False,
                          "selection_status": "confirmed", "notes": []},
            "preparation": {"status": "ready", "current_revision": "r0001", "blockers": []},
            "workflows": {name: {"status": "not_started", "basis_revision": None, "scope": None, "operation": None,
                                 "state_locator": None, "updated_at": None}
                          for name in ("literary-editing", "literary-translation", "literary-agent-querying")}}
    return result(work_record=write(request.cwd, base + "work.json", work))


def sheet(revision, resolved):
    return {
        "schema_version": "1.0", "sheet_id": "map-story", "revision": revision, "title": "Passage map",
        "bindings": [{"label": "Chapter", "value": "story"}],
        "decisions": [{"id": "approve", "command": "approve", "label": "Approve", "requires_note": False,
                       "effect": "resolve"},
                      {"id": "revise", "command": "revise", "label": "Revise", "requires_note": True,
                       "effect": "reopen"}],
        "items": [{"id": "PM001", "summary": "One passage: complete story",
                   "details": [{"label": "Original", "value": "他回来了。"}],
                   "status": "resolved" if resolved else "pending",
                   "status_label": "Reviewed" if resolved else "Pending",
                   "allowed_decisions": ["approve", "revise"], "dependencies": [],
                   "response": {"decision": "approve", "note": "", "date": now()} if resolved else None},
                  {"id": "PM002", "summary": "Second passage", "details": [{"label": "Original", "value": "门开了。"}],
                   "status": "resolved" if resolved else "pending",
                   "status_label": "Reviewed" if resolved else "Pending",
                   "allowed_decisions": ["approve", "revise"], "dependencies": [],
                   "response": {"decision": "approve", "note": "", "date": now()} if resolved else None}],
        "gate": {"status": "awaiting-approval", "closure_required": True, "final_closure": "pending",
                 "ready_state": "not-ready"},
        "presentation": {"mode": "all", "note_label": "Feedback", "note_placeholder": "Required for revision",
                         "submit_label": "Submit"},
        "submission": {"instruction": "Review this map.", "rules": ["Do not translate before closure."],
                       "closure_command": "confirm final closure", "closure_label": "Confirm"},
    }


def samples_sheet():
    return {
        "schema_version": "1.0", "sheet_id": "brief-samples", "revision": "1", "title": "Translation samples",
        "bindings": [{"label": "Samples", "value": "translation/brief-samples.md"}],
        "decisions": [{"id": "choose-a", "command": "choose A", "label": "A", "requires_note": False, "effect": "resolve"},
                      {"id": "choose-b", "command": "choose B", "label": "B", "requires_note": False, "effect": "resolve"},
                      {"id": "none", "command": "none of these", "label": "None of these", "requires_note": True,
                       "effect": "reopen"}],
        "items": [{"id": "S1", "summary": "story, paragraph 1",
                   "details": [{"label": "Original", "value": "他回来了。"}, {"label": "A", "value": "He came back."},
                               {"label": "About A", "value": "Close."}, {"label": "B", "value": "He was back."},
                               {"label": "About B", "value": "Freer."}],
                   "status": "pending", "status_label": "Pending", "allowed_decisions": ["choose-a", "choose-b", "none"],
                   "dependencies": [], "response": None}],
        "gate": {"status": "awaiting-choices", "closure_required": False, "final_closure": "not-required",
                 "ready_state": "not-ready"},
        "presentation": {"mode": "all", "note_label": "Reasons", "note_placeholder": "Optional", "submit_label": "Submit"},
        "submission": {"instruction": "Choose one variant per sample.", "rules": ["Decide every sample."],
                       "closure_command": "confirm final closure", "closure_label": "Confirm"},
    }


def translate(request):
    """A scripted translation agent driven only by the saved receipts it is given."""
    ctx, cwd = context(request), request.cwd
    if ctx["stage"] == "prepare":
        return prepare(request)
    receipt = ctx["user_receipt"] or {}
    command = receipt.get("parsed", {}).get("command") or ""
    if ctx["stage"] == "brief":
        # The translation brief: tryout samples polled first, then glossary, voice, and samples approved together.
        if not ctx["brief_samples_approval"]:
            write(cwd, "translation/glossary.md", "| 故事 | Story | title | provisional |\n")
            write(cwd, "translation/voice.md", "## Narrator · story · home\nPlain. Status: provisional\n")
            return result("needs_human_input", gate="brief_samples", message="Choose the sample variants.",
                          binding_path=write(cwd, "translation/brief-samples.md", "S1: A / B\n"),
                          review_path=write(cwd, "translation/brief-samples.json", samples_sheet()))
        if receipt.get("parsed", {}).get("type") == "dispositions":
            note = receipt["parsed"]["dispositions"][0]["note"]
            write(cwd, "translation/brief-samples.md", f"S1: A accepted ({note}); B rejected\n")
        if receipt.get("parsed", {}).get("type") == "feedback":
            write(cwd, "translation/glossary.md", "| 故事 | Tale | title | provisional |\n")
        return result("needs_human_input", gate="translation_brief", message="Proposed glossary, voice, and samples.")
    if ctx["whole_book"]:
        consistency = ctx["consistency"]
        folder = consistency["plan_path"].rsplit("/", 1)[0]
        change = {"id": "C001", "chapter_id": "story", "source_quote": "他回来了。",
                  "before": "He came back.", "after": "He returned.", "reason": "Synthetic consistency correction."}
        if not consistency["review"]:
            plan = {"chapters": {
                chapter["chapter_id"]: {"source_sha256": chapter["source_sha256"],
                                         "translation_sha256": chapter["translation"]["sha256"],
                                         "evidence": "Synthetic full-book comparison."}
                for chapter in consistency["chapters"]}, "changes": [change]}
            resolved = receipt.get("parsed", {}).get("type") == "dispositions"
            review = sheet("2" if resolved else "1", resolved)
            review.update(sheet_id="whole-book", title="Whole-book consistency")
            review["decisions"].append({"id": "reject", "command": "reject", "label": "Reject",
                                        "requires_note": False, "effect": "resolve"})
            review["items"] = [{
                "id": "C001", "summary": change["reason"], "status": "resolved" if resolved else "pending",
                "status_label": "Reviewed" if resolved else "Pending",
                "details": [{"label": label, "value": change[key]} for label, key in (
                    ("Chapter", "chapter_id"), ("Original", "source_quote"), ("Before", "before"),
                    ("After", "after"), ("Reason", "reason"))],
                "allowed_decisions": ["approve", "reject", "revise"], "dependencies": [],
                "response": {"decision": "approve", "note": "", "date": now()} if resolved else None}]
            return result("needs_human_input", gate="translation_consistency", message="Review whole-book consistency.",
                          state_path=write(cwd, folder + "/review.md", "Synthetic coverage."),
                          binding_path=write(cwd, consistency["plan_path"], plan),
                          review_path=write(cwd, folder + "/sheet.json", review))
        chapter = next(c for c in consistency["chapters"] if c["chapter_id"] == "story")
        write(cwd, chapter["candidate_path"], "He returned.\n")
        write(cwd, consistency["report_path"], {"chapters": {"story": {
            "source_sha256": chapter["source_sha256"], "output_sha256": digest(b"He returned.\n"),
            "evidence": "Synthetic source comparison confirms the approved fix."}}})
        return result(state_path=write(cwd, folder + "/review.md", "Applied and verified."))
    if ctx["chapter"]["chapter_id"] == "front-matter":
        # The front matter: an internal map without exceptions, then chapter approval.
        if receipt.get("parsed", {}).get("type") == "feedback":
            write(cwd, "translation/glossary.md", "| 故事 | Fable | title | user correction |\n")
            write(cwd, "translation/voice.md", "Warmer narration, per the user's correction.\n")
        write(cwd, "translation/maps/front-matter.json", {
            "chapter_id": "front-matter", "passages": [{"id": "P1", "first_paragraph": 1, "last_paragraph": 1}],
            "exceptions": []})
        if command != "approve chapter":
            return result("needs_human_input", gate="chapter_sanity", message="Story\nNo textual changes proposed.",
                          state_path=write(cwd, "translation/sanity.md", "No textual changes proposed\n"),
                          binding_path=write(cwd, "translation/assembled.md", "Story\n"))
        write(cwd, "translation/glossary.md", "# Glossary\n")
        write(cwd, "translation/voice.md", "# Voice\n")
        return result(state_path=write(cwd, "translation/state.md", "Front matter finalized.\n"),
                      output_path=write(cwd, "translation/translated_english/front-matter.md", "Story\n"))
    if not ctx["map_exceptions_approval"]:
        if receipt.get("parsed", {}).get("type") == "dispositions":
            revision, resolved = "2", True
        else:
            revision, resolved = "1", False
        return result("needs_human_input", gate="map_exceptions", message="Review the passage map.",
                      state_path=write(cwd, "translation/state.md", "Map pending.\n"),
                      binding_path=write(cwd, "translation/maps/story.json", {
                          "chapter_id": "story", "passages": [{"id": "P1", "first_paragraph": 1, "last_paragraph": 2}],
                          "exceptions": [{"id": "PM001", "kind": "special", "first_paragraph": 1, "last_paragraph": 1,
                                          "reason": "Keep the heading in its original form."}]}),
                      review_path=write(cwd, "translation/map-review.json", sheet(revision, resolved)))
    if not ctx["sanity_approval"] and command != "approve chapter":
        return result("needs_human_input", gate="chapter_sanity", message="He came back.\nNo textual changes proposed.",
                      state_path=write(cwd, "translation/sanity.md", "No textual changes proposed\n"),
                      binding_path=write(cwd, "translation/assembled.md", "He came back.\n"))
    write(cwd, "translation/glossary.md", "# Glossary\n")
    write(cwd, "translation/voice.md", "# Voice\n")
    return result(state_path=write(cwd, "translation/state.md", "Chapter finalized.\n"),
                  output_path=write(cwd, "translation/translated_english/story.md", "He came back.\n"))


def interior_design(request, *, include_openings=False):
    ctx = context(request)
    if ctx["stage"] == "prepare":
        return prepare(request)
    if ctx["stage"] != "interior-design":
        raise AssertionError("The zero-pass design route must not call an editorial agent.")
    proposal = ctx["previous_proposal"] or proposal_for(Path(request.cwd) / ctx["work_record"], include_openings=include_openings)
    if ctx["previous_proposal"]:
        proposal["revision"] += 1
    apply_target(proposal, ctx["vendor_profile"], ctx["format_target"])
    return result(state_path=write(request.cwd, ctx["proposal_path"], proposal), work_record=ctx["work_record"])


class Scripted:
    def __init__(self, action):
        self.action = action

    def run(self, request, on_event, on_thread):
        on_thread("scripted-thread")
        on_event("test.turn", {})
        return analyze(request) if context(request)["stage"] == "analysis" else self.action(request)


@unittest.skipUnless(HAS_WEB, "Install studio/requirements.txt for web API tests.")
class WebApiTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from studio.server.app import create_app
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.source = base / "original.md"
        self.source.write_bytes("# 故事\n\n他回来了。\n".encode())
        self.app = create_app(base / "server", runtime_factory=lambda: Scripted(translate), owner="tester")
        self.client = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def post(self, path, payload=None, **kwargs):
        response = self.client.post(path, json=payload or {}, headers={"Origin": ORIGIN}, **kwargs)
        return response

    def settle(self, run_id):
        self.app.state.workers.wait(run_id, 30)
        for _ in range(100):
            if not self.app.state.workers.status(run_id)["active"]:
                break
            time.sleep(0.05)
        return self.client.get(f"/api/runs/{run_id}").json()

    def test_run_detail_usage_is_aggregated_read_only_and_not_added_to_the_run_list(self):
        work = self.post("/api/works", {
            "upload": {"name": "original.md", "data": base64.b64encode(self.source.read_bytes()).decode()},
            "manuscript_language": "zh"}).json()
        created = self.post("/api/runs", {"template_id": "literary-translation-v1",
                                         "work_id": work["id"], "start": False}).json()
        self.assertIsNone(created["usage"]["total_tokens"])
        with WorkflowService(Path(self.temp.name) / "server") as svc, svc.open_run(created["id"]) as engine:
            engine.store.event("execution.started", {"execution": {"harness": "pi"}})
            engine.store.event("runtime.usage", {"input": 100, "output": 20, "cacheRead": 70})
            before = len(list(engine.store.events()))
            for _ in range(2):
                usage = self.client.get(f"/api/runs/{created['id']}").json()["usage"]
                self.assertEqual(usage["total_tokens"], 120)
                self.assertEqual(usage["cached_input_tokens"], 70)
                self.assertFalse(usage["partial"])
            self.assertEqual(len(list(engine.store.events())), before)
        self.assertNotIn("usage", self.client.get("/api/runs").json()[0])

    def test_approved_sheets_use_only_closed_immutable_snapshots_and_preserve_scope(self):
        work = self.post("/api/works", {"upload": {
            "name": "original.md", "data": base64.b64encode(self.source.read_bytes()).decode()},
            "manuscript_language": "zh"}).json()
        run = self.post("/api/runs", {"template_id": "literary-editing-v1", "work_id": work["id"], "start": False}).json()
        run_id = run["id"]
        path = f"/api/runs/{run_id}/approved-sheets"
        self.assertEqual(self.client.get(path).json(), [])
        with WorkflowService(Path(self.temp.name) / "server") as svc, svc.open_run(run_id) as engine:
            engine.advance(Scripted(prepare))
            revision, state = engine.store.load()
            pending = sheet("1", False)
            approved = sheet("2", True)
            pending_snapshot = engine.checkpoint(write(engine.workspace, "history/pending.json", pending), "review_sheet")
            approved_snapshot = engine.checkpoint(write(engine.workspace, "history/approved.json", approved), "review_sheet")
            context_snapshot = engine.checkpoint(write(engine.workspace, "history/context.md", "Saved context.\n"), "document")

            def receipt(identity, snapshot, parsed, *, epoch=1, chapter="story", source="human"):
                gate = {**copy.deepcopy(state["gate"]), "id": identity + "-gate", "kind": "editorial_review",
                        "stage": "line", "chapter_id": chapter, "instance": f"line/{epoch}/{chapter}/1",
                        "attempt": 1, "sheet": snapshot, "documents": [context_snapshot]}
                return {"id": identity, "created_at": now(), "gate": gate, "text": "Recorded author response",
                        "parsed": parsed, "decision_source": source}

            first = receipt("start-first", None, {"type": "final-closure"})
            second = receipt("start-second", None, {"type": "final-closure"})
            feedback = receipt("feedback", pending_snapshot, {"type": "feedback"})
            dispositions = receipt("items-only", pending_snapshot, {"type": "dispositions", "dispositions": []})
            closed = receipt("closed", approved_snapshot, {"type": "final-closure"})
            closed["gate"]["binding"] = context_snapshot
            implied = receipt("implied", pending_snapshot, {
                "type": "dispositions", "implied_closure": True,
                "dispositions": [{"item_id": item["id"], "decision": "approve", "note": "Keep this wording.", "effect": "resolve"}
                                 for item in pending["items"]],
            }, epoch=2, chapter="_whole", source="delegated-automation")
            state["receipts"].extend([first, feedback, dispositions, closed, second, implied])
            state["passes"] = [
                {"number": number, "stage": "line", "epoch": number, "receipt_id": start["id"],
                 "started_at": start["created_at"], "completed_at": now(), "accepted": None, "result": None, "restarts": 0}
                for number, start in enumerate((first, second), 1)]
            state["restarts"].append({"kind": "stage", "superseded_receipt_ids": ["closed"]})
            engine.store.save(revision, state, "fixture.history")
            before = engine.store.load()
            events = len(engine.store.events())
            write(engine.workspace, "history/approved.json", {**approved, "title": "Overwritten workspace draft"})
            write(engine.workspace, "history/context.md", "Changed working context.\n")

        history = self.client.get(path)
        self.assertEqual(history.status_code, 200, history.text)
        entries = history.json()
        self.assertEqual([r["receipt_id"] for r in entries], ["implied", "closed"])
        self.assertEqual([(r["pass_number"], r["scope"]) for r in entries], [(2, "Whole book"), (1, "故事")])
        self.assertTrue(entries[1]["superseded"])
        self.assertEqual(entries[0]["decision_source"], "delegated-automation")
        saved = self.client.get(path + "/closed.md")
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.content, b"Saved context.\n")
        self.assertEqual(saved.headers["x-content-sha256"], context_snapshot["sha256"])
        self.assertIn("attachment;", saved.headers["content-disposition"])
        self.assertIn('.md"', saved.headers["content-disposition"])
        self.assertIn("text/markdown", saved.headers["content-type"])
        implied_view = self.client.get(path + "/implied.md")
        self.assertEqual(implied_view.status_code, 200)
        self.assertIn("# Passage map", implied_view.text)
        self.assertIn("## PM001:", implied_view.text)
        self.assertIn("Recorded decision: Approve", implied_view.text)
        self.assertIn("Keep this wording.", implied_view.text)
        self.assertIn("Whole book", implied_view.text)
        self.assertEqual(implied_view.headers["x-content-sha256"], digest(implied_view.content))
        self.assertEqual(self.client.get(path + "/closed").status_code, 404)  # No historical viewer API.
        for identity in ("feedback", "items-only", "start-first", "missing", approved_snapshot["sha256"]):
            self.assertEqual(self.client.get(path + "/" + identity + ".md").status_code, 404)
        with WorkflowService(Path(self.temp.name) / "server") as svc, svc.open_run(run_id) as engine:
            self.assertEqual(engine.store.load(), before)
            self.assertEqual(len(engine.store.events()), events)
            engine.store.root.joinpath("objects", approved_snapshot["sha256"]).write_bytes(b"corrupt snapshot")
        corrupted = self.client.get(path + "/closed.md")
        self.assertEqual(corrupted.status_code, 400)
        self.assertIn("checksum", corrupted.json()["detail"])

    def test_metadata_has_one_post_preparation_location_and_preserves_approved_snapshots(self):
        work = self.post("/api/works", {
            "upload": {"name": "original.md", "data": base64.b64encode(self.source.read_bytes()).decode()},
        }).json()
        self.assertIsNone(work["metadata_editor_run"])
        early = self.post(f"/api/works/{work['id']}/metadata", {"field": "/title", "value": "Too early"})
        self.assertEqual(early.status_code, 400, early.text)
        self.assertIn("Prepare the manuscript first", early.text)
        self.assertEqual({f["group"] for f in work["metadata_fields"]}, {"suggested", "computed"})
        run = self.post("/api/runs", {"template_id": "literary-translation-v1",
                                      "work_id": work["id"], "start": False}).json()
        path = f"/api/runs/{run['id']}"
        with WorkflowService(Path(self.temp.name) / "server") as svc, svc.open_run(run["id"]) as engine:
            engine.advance(Scripted(prepare))
            engine.edit_metadata("/contributors", [{"id": "chosen", "name": "Chosen Pen Name", "roles": ["author"]}],
                                 gate_id=engine.state()["gate"]["id"])
            view = self.client.get(path + "/overview").json()
            self.assertEqual(view["metadata_edit"], {"target": "run", "run_id": run["id"]})
            self.assertEqual(view["metadata"]["metadata"]["contributors"][0]["name"], "Chosen Pen Name")
            engine.reply(engine.state()["gate"]["id"], "confirm metadata")
        with WorkflowService(Path(self.temp.name) / "server") as svc:
            svc.stop(run["id"])
        before = self.client.get(path + "/overview").json()
        self.assertEqual(before["metadata_edit"], {"target": "work", "run_id": run["id"]})
        approved = before["source"]["reviews"]
        edited = self.post(f"/api/works/{work['id']}/metadata", {
            "field": "/title", "value": "Later correction", "rationale": "Corrected in Overview"})
        self.assertEqual(edited.status_code, 200, edited.text)
        after = self.client.get(path + "/overview").json()
        self.assertEqual(after["metadata"]["metadata"]["title"], "Later correction")
        self.assertEqual(self.client.get(path + "/chapters").json()["overview"]["title"], "Later correction")
        self.assertEqual(after["source"]["reviews"], approved)
        self.assertEqual(after["source"]["prepared_text"], before["source"]["prepared_text"])
        # Typed optional values still validate, but only after preparation.
        endpoint = f"/api/works/{work['id']}/metadata"
        for field, value in (("/genres", ["Literary fiction", "Science fiction"]),
                             ("/series/position", 2), ("/audience", "adult"),
                             ("/contributors", [{"id": "writer", "name": "A Writer", "roles": ["author", "editor"]}])):
            response = self.post(endpoint, {"field": field, "value": value})
            self.assertEqual(response.status_code, 200, response.text)
        current_revision = self.client.get(path + "/overview").json()["metadata"]["record_revision"]
        for field, value in (("/series/position", -1), ("/original_language", "Chinese"),
                             ("/contributors", [{"id": "x", "name": "X", "roles": []}])):
            response = self.post(endpoint, {"field": field, "value": value})
            self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self.client.get(path + "/overview").json()["metadata"]["record_revision"], current_revision)

    def test_overview_is_a_read_only_projection_with_stable_source_identity(self):
        front_text = "# 故事\n\n献给读者。\n"
        body_text = "他回来了。\n"
        self.source.write_bytes((front_text + "\n" + body_text).encode())

        def prepare_with_opening(request):
            prepared = prepare(request)
            work_id = context(request)["required_work_id"]
            root = Path(request.cwd) / "prepared" / work_id / "revisions/r0001"
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            manifest["chapters"][0].update(chapter_id="book-opening", sha256=digest(front_text.encode()))
            manifest["chapters"][0]["source_spans"][0]["locator"] = "Title and dedication"
            manifest["chapters"][1]["sha256"] = digest(body_text.encode())
            manifest["chapters"][1]["source_spans"][0]["locator"] = "Body"
            manifest["scope"]["chapter_ids"][0] = "book-opening"
            write(request.cwd, str((root / "chapters/0001.md").relative_to(request.cwd)), front_text)
            write(request.cwd, str((root / "chapters/0002.md").relative_to(request.cwd)), body_text)
            write(request.cwd, str((root / "manifest.json").relative_to(request.cwd)), manifest)
            return prepared

        for template in ("literary-editing-v1", "literary-translation-v1"):
            with self.subTest(template=template):
                work = self.post("/api/works", {
                    "upload": {"name": "original.md", "data": base64.b64encode(self.source.read_bytes()).decode()},
                    "manuscript_language": "zh"}).json()
                created = self.post("/api/runs", {"template_id": template, "work_id": work["id"], "start": False}).json()
                run_id = created["id"]
                path = f"/api/runs/{run_id}"
                initial = self.client.get(path + "/overview").json()
                self.assertEqual((initial["prepared"], initial["source_unit_id"], initial["source"]), (False, None, None))
                with WorkflowService(Path(self.temp.name) / "server") as svc, svc.open_run(run_id) as engine:
                    before = engine.advance(Scripted(prepare_with_opening))
                    source_hashes = copy.deepcopy(before["prepared"]["files"])
                self.assertEqual(before["gate"]["chapter_id"], "book-opening")
                overview = self.client.get(path + "/overview").json()
                index = self.client.get(path + "/chapters").json()
                self.assertEqual(overview["source_unit_id"], "book-opening")
                self.assertEqual(overview["title"], "Story")
                self.assertEqual(overview["source"]["prepared_text"], front_text)
                self.assertEqual(overview["metadata"]["metadata"]["title"], "Story")
                self.assertEqual(index["overview"]["source_unit_id"], "book-opening")
                self.assertEqual([(c["chapter_id"], c["order"], c["display_number"]) for c in index["chapters"]],
                                 [("story", 2, 1)])
                self.assertEqual(self.client.get(path).json()["viewer_target"], {"kind": "overview"})
                listed = next(r for r in self.client.get("/api/runs").json() if r["id"] == run_id)
                self.assertEqual(listed["viewer_target"], {"kind": "overview"})
                with WorkflowService(Path(self.temp.name) / "server") as svc, svc.open_run(run_id) as engine:
                    self.assertEqual(engine.state(), before)
                    self.assertEqual(engine.state()["prepared"]["files"], source_hashes)
                renamed = self.post(path + "/metadata", {"gate_id": before["gate"]["id"], "field": "/title",
                                                         "value": "Renamed work", "rationale": "Author's title"})
                self.assertEqual(renamed.status_code, 200, renamed.text)
                renamed_overview = self.client.get(path + "/overview").json()
                self.assertEqual((renamed_overview["title"], renamed_overview["source_unit_id"]),
                                 ("Renamed work", "book-opening"))
                self.assertEqual(renamed_overview["source"]["prepared_text"], front_text)
                self.assertEqual(renamed.json()["viewer_target"], {"kind": "overview"})

    def test_overview_exposes_frozen_subject_proposals_without_changing_metadata(self):
        for template in ("literary-editing-v1", "literary-translation-v1"):
            with self.subTest(template=template):
                work = self.post("/api/works", {"upload": {"name": "story.md",
                    "data": base64.b64encode(self.source.read_bytes()).decode()}, "manuscript_language": "zh"})
                self.assertEqual(work.status_code, 200, work.text)
                created = self.post("/api/runs", {
                    "template_id": template, "work_id": work.json()["id"], "start": False})
                self.assertEqual(created.status_code, 200, created.text)
                run_id = created.json()["id"]
                with WorkflowService(Path(self.temp.name) / "server") as svc, svc.open_run(run_id) as engine:
                    state = engine.advance(Scripted(prepare))
                    state = engine.edit_metadata("/keywords", ["author keyword"], gate_id=state["gate"]["id"],
                                                 reason="Author's existing keyword")
                    engine.reply(state["gate"]["id"], "confirm metadata")
                    metadata = engine._work_path(engine.state()).read_bytes()
                    before = engine.advance(Scripted(analyze))
                    revision = engine.store.load()[0]
                response = self.client.get(f"/api/runs/{run_id}/overview")
                self.assertEqual(response.status_code, 200, response.text)
                overview = response.json()
                self.assertEqual(overview["analysis"]["subject_proposals"], before["analysis"]["subject_proposals"])
                self.assertEqual(overview["metadata"]["metadata"]["keywords"], ["author keyword"])
                self.assertEqual(overview["analysis"]["subject_proposals"]["place_subjects"]["status"], "undetermined")
                with WorkflowService(Path(self.temp.name) / "server") as svc, svc.open_run(run_id) as engine:
                    self.assertEqual(engine.state(), before)
                    self.assertEqual(engine.store.load()[0], revision)
                    self.assertEqual(engine._work_path(engine.state()).read_bytes(), metadata)

    def test_literary_editing_interior_design_form_save_revision_and_approval(self):
        calls = []

        def runtime(request):
            calls.append(context(request)["stage"])
            return interior_design(request)

        self.app.state.workers.runtime_factory = lambda: Scripted(runtime)
        added = self.post("/api/works", {"upload": {"name": "story.md",
                           "data": base64.b64encode(self.source.read_bytes()).decode()}, "manuscript_language": "zh"})
        run = self.post("/api/runs", {"template_id": "literary-editing-v1", "work_id": added.json()["id"]}).json()
        run_id = run["id"]
        run = self.settle(run_id)
        self.post(f"/api/runs/{run_id}/metadata/confirm", {
            "gate_id": run["gate"]["id"], "record_revision": run["metadata"]["record_revision"]})
        run = self.settle(run_id)
        response = self.post(f"/api/runs/{run_id}/reply", {
            "gate_id": run["gate"]["id"], "text": "proceed to formatting"})
        self.assertEqual(response.status_code, 400, response.text)
        response = self.post(f"/api/runs/{run_id}/reply", {"gate_id": run["gate"]["id"], "text": "finish"})
        self.assertEqual(response.status_code, 200, response.text)
        run = self.settle(run_id)
        self.assertEqual(run["status"], "WAITING_FOR_ACCEPTANCE")
        self.assertFalse(run["acceptance"]["finalizes"])
        self.assertEqual(calls, ["prepare"])
        self.assertEqual(run["acceptance"]["title"], "Approve manuscript for formatting")
        self.assertFalse(self.client.get(f"/api/works/{added.json()['id']}").json()["workflows"])
        response = self.post(f"/api/runs/{run_id}/accept", {
            "acceptance_id": run["acceptance"]["acceptance_id"], "confirm_final": True})
        self.assertEqual(response.status_code, 200, response.text)
        run = self.settle(run_id)
        self.assertEqual((run["status"], run["gate"]["kind"]), ("WAITING_FOR_HUMAN", "interior_design_review"))
        view = run["gate"]["design_review"]
        self.assertEqual(view["schema"]["properties"]["status"], {"const": "proposed"})
        spec = {key: view["proposal"][key] for key in ("edition_brief", "design_system")}
        spec["role_styles"] = {role["id"]: role["style_id"] for role in view["proposal"]["text_roles"]}
        spec["design_system"]["page"]["margins_mm"]["inside"] = 23
        payload = {"gate_id": run["gate"]["id"], "expected_sha256": view["sha256"], "action": "save", "spec": spec}
        saved = self.post(f"/api/runs/{run_id}/interior-design", payload)
        self.assertEqual(saved.status_code, 200, saved.text)
        run = saved.json()
        self.assertEqual(run["gate"]["design_review"]["proposal"]["design_system"]["page"]["margins_mm"]["inside"], 23)
        self.assertEqual(self.post(f"/api/runs/{run_id}/interior-design", payload).status_code, 400)
        current = {"gate_id": run["gate"]["id"], "expected_sha256": run["gate"]["design_review"]["sha256"]}
        revised = self.post(f"/api/runs/{run_id}/interior-design", {
            **current, "action": "request-revision", "feedback": "Keep my inside margin; reconsider the typeface."})
        self.assertEqual(revised.status_code, 200, revised.text)
        run = self.settle(run_id)
        self.assertEqual(run["gate"]["design_review"]["proposal"]["design_system"]["page"]["margins_mm"]["inside"], 23)
        current = {"gate_id": run["gate"]["id"], "expected_sha256": run["gate"]["design_review"]["sha256"]}
        answers = {q["id"]: "Keep the proposed new-page openings." for q in run["gate"]["design_review"]["proposal"]["questions"]
                   if q["blocking"]}
        approved = self.post(f"/api/runs/{run_id}/interior-design", {**current, "action": "generate", "answers": answers})
        self.assertEqual(approved.status_code, 200, approved.text)
        run = self.settle(run_id)
        self.assertEqual(run["status"], "WAITING_FOR_ACCEPTANCE")
        self.assertIsNone(run.get("gate"))
        self.assertEqual(self.post(f"/api/runs/{run_id}/docx/authorize", {
            "gate_id": "removed", "expected_plan_sha256": "0" * 64}).status_code, 405)
        docx_url = f"/api/runs/{run_id}/docx/{run['production']['id']}"
        document = self.client.get(docx_url)
        self.assertEqual(document.status_code, 200, document.text if document.status_code != 200 else "")
        self.assertEqual(digest(document.content), run["production"]["docx"]["sha256"])
        self.assertEqual(document.headers["x-content-sha256"], digest(document.content))
        self.assertIn(f'Story-v001-candidate-{run["production"]["id"][:8]}.docx',
                      document.headers["content-disposition"])
        self.assertEqual(self.client.get(f"/api/runs/{run_id}/docx/wrong-build").status_code, 400)
        accepted = self.post(f"/api/runs/{run_id}/accept", {
            "acceptance_id": run["acceptance"]["acceptance_id"], "confirm_final": True})
        self.assertEqual(accepted.status_code, 200, accepted.text)
        run = self.settle(run_id)
        self.assertEqual((run["status"], run["finalized"]), ("COMPLETED", True))
        work = self.client.get(f"/api/works/{added.json()['id']}").json()
        published = work["heads"]["literary-editing/v001/document.docx"]
        delivery = self.client.get(f"/api/works/{work['id']}/docx/{published['id']}")
        self.assertEqual(delivery.content, document.content)
        self.assertIn('filename="Story-v001.docx"', delivery.headers["content-disposition"])
        accepted_download = self.client.get(docx_url)
        self.assertEqual(accepted_download.content, document.content)
        self.assertEqual(accepted_download.headers["x-content-sha256"], document.headers["x-content-sha256"])
        self.assertEqual(accepted_download.headers["content-disposition"], delivery.headers["content-disposition"])
        renamed = self.post(f"/api/works/{work['id']}/metadata", {
            "field": "/title", "value": "Later title", "rationale": "New edition title"})
        self.assertEqual(renamed.status_code, 200, renamed.text)
        historical = self.client.get(f"/api/works/{work['id']}/docx/{published['id']}")
        self.assertEqual(historical.headers["content-disposition"], delivery.headers["content-disposition"])
        self.assertEqual(self.client.get(docx_url).headers["content-disposition"], delivery.headers["content-disposition"])
        self.assertEqual(calls, ["prepare", "interior-design", "interior-design"])

    def test_docx_download_filename_preserves_unicode_and_sanitizes_unsafe_titles(self):
        from studio.server.app import docx_disposition

        for title, expected in (('洞: A/B "draft"\r\n', "洞_ A_B _draft__"),
                                (" .. ", "Manuscript"), ("", "Manuscript")):
            core = ET.Element("properties")
            ET.SubElement(core, "{http://purl.org/dc/elements/1.1/}title").text = title
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w") as document:
                document.writestr("docProps/core.xml", ET.tostring(core))
            header = docx_disposition(stream.getvalue(), "v002")
            self.assertNotIn("\r", header)
            self.assertNotIn("\n", header)
            self.assertIn("filename*=UTF-8''", header)
            self.assertEqual(unquote(header.split("filename*=UTF-8''")[1]), f"{expected}-v002.docx")

    def test_removed_formatting_route_and_read_only_history(self):
        work_id = self.post("/api/works", {"upload": {"name": "story.md",
                            "data": base64.b64encode(self.source.read_bytes()).decode()}}).json()["id"]
        template = "manuscript-formatting-v1"
        templates = self.client.get("/api/templates").json()
        self.assertNotIn(template, [item["id"] for item in templates])
        for fields in ({}, {"derived": True, "options": {"renderer": "word"}}):
            rejected = self.post("/api/runs", {"template_id": template, "work_id": work_id, **fields})
            self.assertEqual(rejected.status_code, 400 if fields else 404, rejected.text)
        run = self.post("/api/runs", {"template_id": "literary-editing-v1",
                        "work_id": work_id, "start": False}).json()
        store = Store(Path(run["path"]))
        self.addCleanup(store.close)
        revision, state = store.load()
        state.update(template_id=template, workflow="format-manuscript", status="WAITING_FOR_HUMAN")
        state["definition"]["engine"] = "workflow.src.formatting:FormattingEngine"
        state["gate"] = {"id": "archived-format", "kind": "format_spec", "stage": state["stage"],
                         "chapter_id": None, "message": "Historical format review."}
        store.save(revision, state, "fixture.retired")
        recorded = store.load()
        detail = self.client.get(f"/api/runs/{run['id']}").json()
        self.assertEqual(detail["status"], "RETIRED")
        self.assertTrue(detail["retired"])
        self.assertNotIn("gate", detail)
        self.assertEqual(detail["available_actions"], [])
        reply = self.post(f"/api/runs/{run['id']}/reply", {"gate_id": "archived-format", "text": "FM001 approve"})
        self.assertEqual(reply.status_code, 409, reply.text)
        restart = self.post(f"/api/runs/{run['id']}/restart", {"reason": "Try the removed workflow"})
        self.assertEqual(restart.status_code, 409, restart.text)
        self.assertIsNone(self.client.get(f"/api/works/{work_id}").json()["unfinished_run"])
        self.assertEqual(store.load(), recorded)

    def test_upload_without_language_is_prepared_before_downstream_language_is_set(self):
        added = self.post("/api/works", {"upload": {"name": "story.md",
                           "data": base64.b64encode(self.source.read_bytes()).decode()}})
        self.assertEqual(added.status_code, 200, added.text)
        self.assertIsNone(added.json()["manuscript_language"])
        run = self.post("/api/runs", {"template_id": "literary-translation-v1",
                                     "work_id": added.json()["id"]})
        self.assertEqual(run.status_code, 200, run.text)
        prepared = self.settle(run.json()["id"])
        self.assertEqual(prepared["gate"]["kind"], "metadata_review")
        self.assertEqual(prepared["manuscript_language"], "zh")
        self.assertEqual(prepared["settings"]["passage_size"], 1500)
        work = self.client.get("/api/works/" + added.json()["id"]).json()
        self.assertEqual(work["manuscript_language"], "zh")

    def test_outdated_run_can_be_stopped_to_start_another_workflow(self):
        added = self.post("/api/works", {"upload": {"name": "story.md",
                           "data": base64.b64encode(self.source.read_bytes()).decode()}})
        work_id = added.json()["id"]
        run = self.post("/api/runs", {"template_id": "literary-translation-v1", "work_id": work_id})
        self.assertEqual(run.status_code, 200, run.text)
        run_id = run.json()["id"]
        self.settle(run_id)
        path = self.app.state.workers.server_root / "runs" / run_id
        store = Store(path)
        try:
            with store.locked():
                revision, state = store.load()
                state["engine"]["sha256"] = "0" * 64
                store.save(revision, state, "test.engine_changed")
        finally:
            store.close()
        outdated = self.client.get(f"/api/runs/{run_id}").json()
        actions = {a["action"]: a["enabled"] for a in outdated["available_actions"]}
        self.assertFalse(outdated["engine_current"])
        self.assertTrue(actions["stop"])
        self.assertFalse(actions["reply"])
        self.assertEqual(self.client.get(f"/api/works/{work_id}").json()["unfinished_run"], run_id)
        stopped = self.post(f"/api/runs/{run_id}/stop")
        self.assertEqual(stopped.status_code, 200, stopped.text)
        self.assertEqual(stopped.json()["status"], "CANCELLED")
        self.assertIsNone(self.client.get(f"/api/works/{work_id}").json()["unfinished_run"])
        started = self.post("/api/runs", {"template_id": "literary-translation-v1", "work_id": work_id})
        self.assertEqual(started.status_code, 200, started.text)
        self.settle(started.json()["id"])

    def test_run_details_do_not_mix_state_snapshots_when_a_gate_appears(self):
        from workflow.src.engine import Engine
        from workflow.src.service import WorkflowService

        added = self.post("/api/works", {"upload": {"name": "story.md",
                           "data": base64.b64encode(self.source.read_bytes()).decode()}, "manuscript_language": "zh"})
        with WorkflowService(self.app.state.workers.server_root, owner="tester") as service:
            run_id = service.create_run("literary-editing-v1", work_id=added.json()["id"])
            with service.open_run(run_id) as engine:
                waiting = engine.advance(Scripted(prepare))
        running = copy.deepcopy(waiting)
        running.update(status="RUNNING", gate=None)
        # A worker can publish the gate between reads. A response must describe one snapshot.
        with patch.object(Engine, "state", side_effect=[running, waiting]):
            response = self.client.get(f"/api/runs/{run_id}")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "RUNNING")
        self.assertNotIn("gate", response.json())

    def test_translation_runs_through_every_gate_from_the_browser_api(self):
        upload = {"name": "original.md", "data": base64.b64encode(self.source.read_bytes()).decode()}
        refused = self.post("/api/runs", {"template_id": "literary-translation-v1", "upload": upload,
                                          "manuscript_language": "zh"})
        self.assertIn("Works page", refused.json()["detail"])  # Intake belongs to the Works page.
        added = self.post("/api/works", {"upload": upload, "manuscript_language": "zh"})
        self.assertEqual(added.status_code, 200, added.text)
        self.assertEqual((added.json()["runs"], added.json()["unfinished_run"]), ([], None))
        created = self.post("/api/runs", {"template_id": "literary-translation-v1", "work_id": added.json()["id"],
                                          "settings": {"passage_size": 1200}})
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["settings"], {"passage_size": 1200})  # The run's own passage size.
        run_id = created.json()["id"]
        run = self.settle(run_id)
        self.assertEqual((run["stage"], run["status"], run["gate"]["kind"]), ("metadata", "WAITING_FOR_HUMAN",
                                                                             "metadata_review"))
        self.assertEqual(run["metadata"]["record_revision"], 1)
        stale = self.post(f"/api/runs/{run_id}/metadata/confirm", {"gate_id": run["gate"]["id"], "record_revision": 9})
        self.assertEqual(stale.status_code, 400)
        self.assertEqual(run["gate"]["chapter_id"], "front-matter")  # Metadata review is on the front matter.
        self.assertEqual(run["viewer_target"], {"kind": "overview"})
        self.post(f"/api/runs/{run_id}/metadata/confirm", {"gate_id": run["gate"]["id"], "record_revision": 1})
        run = self.settle(run_id)
        # The sample poll: each original beside its variants; one choice per sample, reasons optional.
        self.assertEqual((run["gate"]["kind"], run["gate"]["chapter_id"]), ("brief_samples", "front-matter"))
        self.assertEqual(run["viewer_target"], {"kind": "overview"})
        self.assertEqual([row["label"] for row in run["gate"]["sheet"]["items"][0]["details"][:2]], ["Original", "A"])
        self.post(f"/api/runs/{run_id}/reply", {"gate_id": run["gate"]["id"], "text": "S1 choose A: keeps the restraint"})
        run = self.settle(run_id)
        # The translation brief is the workflow's own front-matter review: read the files, correct, approve.
        self.assertEqual((run["gate"]["kind"], run["gate"]["chapter_id"], run["gate"]["commands"]),
                         ("translation_brief", "front-matter", ["approve brief"]))
        self.assertTrue(run["gate_review"])
        self.assertEqual([d["path"] for d in run["gate"]["documents"]],
                         ["translation/glossary.md", "translation/voice.md", "translation/brief-samples.md"])
        self.assertIn("keeps the restraint", run["gate"]["documents"][2]["text"])
        self.post(f"/api/runs/{run_id}/reply", {"gate_id": run["gate"]["id"], "text": "Render 故事 as Tale."})
        run = self.settle(run_id)
        self.assertIn("Tale", run["gate"]["documents"][0]["text"])
        self.post(f"/api/runs/{run_id}/reply", {"gate_id": run["gate"]["id"], "text": "approve brief"})
        run = self.settle(run_id)
        front = self.client.get(f"/api/runs/{run_id}/chapters/front-matter").json()
        self.assertEqual([r["kind"] for r in front["reviews"]], ["metadata_review", "translation_brief"])
        self.assertIn("Tale", front["reviews"][1]["documents"][0]["text"])
        self.assertEqual((run["gate"]["kind"], run["gate"]["chapter_id"]), ("chapter_sanity", "front-matter"))
        self.assertEqual(run["viewer_target"], {"kind": "overview"})
        # A correction after brief approval updates working documents, while approval history keeps the old version.
        self.post(f"/api/runs/{run_id}/reply", {"gate_id": run["gate"]["id"],
                                              "text": "Use Fable for 故事 and warmer narration."})
        run = self.settle(run_id)
        front = self.client.get(f"/api/runs/{run_id}/chapters/front-matter").json()
        brief = front["reviews"][1]
        self.assertIn("Fable", brief["current_documents"][0]["text"])
        self.assertIn("Warmer narration", brief["current_documents"][1]["text"])
        self.assertIn("Tale", brief["documents"][0]["text"])
        self.assertNotEqual(brief["documents"][0]["sha256"], brief["current_documents"][0]["sha256"])
        self.post(f"/api/runs/{run_id}/reply", {"gate_id": run["gate"]["id"], "text": "approve chapter"})
        run = self.settle(run_id)
        self.assertEqual(run["gate"]["kind"], "map_exceptions")
        self.assertEqual(run["gate"]["sheet"]["items"][0]["id"], "PM001")
        bad = self.post(f"/api/runs/{run_id}/reply", {"gate_id": run["gate"]["id"], "text": "PM001 maybe"})
        self.assertEqual(bad.status_code, 400)
        partial = self.post(f"/api/runs/{run_id}/reply", {"gate_id": run["gate"]["id"], "text": "PM001 approve"})
        self.assertEqual(partial.status_code, 400)
        self.assertIn("missing: PM002", partial.json()["detail"])  # One complete submission per sheet revision.
        self.post(f"/api/runs/{run_id}/reply", {"gate_id": run["gate"]["id"], "text": "PM001 approve\nPM002 approve"})
        # A complete resolving submission closes the map-exceptions sheet; no separate closure is requested.
        run = self.settle(run_id)
        self.assertEqual((run["gate"]["kind"], run["gate"]["commands"]), ("chapter_sanity", ["approve chapter"]))
        self.assertEqual(run["gate"]["binding_text"], "He came back.\n")
        # Pausing keeps the run at its next step after a reply until it is resumed.
        self.post(f"/api/runs/{run_id}/pause")
        self.post(f"/api/runs/{run_id}/reply", {"gate_id": run["gate"]["id"], "text": "approve chapter"})
        run = self.settle(run_id)
        self.assertEqual((run["status"], run["worker"]["paused"]), ("READY", True))
        self.post(f"/api/runs/{run_id}/resume")
        run = self.settle(run_id)
        self.assertEqual((run["gate"]["kind"], run["gate"]["chapter_id"]), ("translation_consistency", "_whole"))
        self.assertEqual(run["progress"], {"completed": 2, "total": 2})
        self.assertEqual(run["gate"]["sheet"]["items"][0]["chapter_id"], "story")
        self.assertFalse(next(a for a in run["available_actions"] if a["action"] == "accept")["enabled"])
        self.post(f"/api/runs/{run_id}/reply", {"gate_id": run["gate"]["id"], "text": "C001 approve"})
        run = self.settle(run_id)
        self.assertEqual(run["gate"]["sheet"]["items"][0]["status"], "resolved")
        self.post(f"/api/runs/{run_id}/reply", {"gate_id": run["gate"]["id"], "text": "confirm final closure"})
        run = self.settle(run_id)
        self.assertEqual(run["status"], "WAITING_FOR_ACCEPTANCE")
        self.assertEqual(run["whole_book_status"], "completed")
        accept = next(a for a in run["available_actions"] if a["action"] == "accept")
        self.assertTrue(accept["irreversible"])
        refused = self.post(f"/api/runs/{run_id}/accept", {"acceptance_id": run["acceptance"]["acceptance_id"]})
        self.assertEqual((refused.status_code, refused.json()["code"]), (409, "confirmation_required"))
        self.post(f"/api/runs/{run_id}/accept", {"acceptance_id": run["acceptance"]["acceptance_id"],
                                                 "confirm_final": True})
        run = self.settle(run_id)
        self.assertEqual((run["status"], run["finalized"]), ("COMPLETED", True))
        final_brief = self.client.get(f"/api/runs/{run_id}/chapters/front-matter").json()["reviews"][1]
        # Final views are bound to accepted continuity snapshots, even if a workspace file later changes.
        from workflow.src.service import WorkflowService
        svc = WorkflowService(Path(self.temp.name) / "server")
        try:
            with svc.open_run(run_id) as engine:
                engine.file("translation/glossary.md").write_text("Unpublished workspace edit", encoding="utf-8")
        finally:
            svc.close()
        self.assertEqual(self.client.get(f"/api/runs/{run_id}/chapters/front-matter").json()["reviews"][1],
                         final_brief)

        chapters = self.client.get(f"/api/runs/{run_id}/chapters").json()
        self.assertTrue(chapters["prepared"])
        self.assertEqual([c["chapter_id"] for c in chapters["chapters"]], ["story"])
        self.assertTrue(chapters["overview"]["outputs"]["translate"]["ready"])
        self.assertEqual(chapters["chapters"][0]["outputs"]["translate"]["ready"], True)
        overview = self.client.get(f"/api/runs/{run_id}/overview").json()
        self.assertEqual(overview["source"]["outputs"][0]["text"], "Story\n")
        self.assertEqual(overview["source"]["reviews"][1], final_brief)
        chapter = self.client.get(f"/api/runs/{run_id}/chapters/story").json()
        self.assertEqual((chapter["prepared_text"], chapter["outputs"][0]["text"]), ("# 故事\n\n他回来了。\n",
                                                                                   "He returned.\n"))
        self.assertEqual(chapter["outputs"][0]["consistency_changes"][0]["id"], "C001")
        events = self.client.get(f"/api/runs/{run_id}/events").json()["events"]
        self.assertTrue(events and not any(e["kind"] == "test.turn" for e in events))

        works = self.client.get("/api/works").json()
        self.assertEqual(len(works), 1)
        work = self.client.get(f"/api/works/{works[0]['id']}").json()
        self.assertEqual(work["workflows"]["literary-translation"]["status"], "completed")
        self.assertEqual(work["metadata"]["metadata"]["title"], "Story")
        text = self.client.get(f"/api/works/{work['id']}/artifact",
                               params={"path": "literary-translation/v001/chapters/0002.md"})
        self.assertEqual(text.text, "He returned.\n")
        source = next(a for a in work["heads"] if a.startswith("sources/"))
        self.assertEqual(self.client.get(f"/api/works/{work['id']}/artifact", params={"path": source}).text,
                         self.source.read_text(encoding="utf-8"))
        missing = self.client.get(f"/api/works/{work['id']}/artifact", params={"path": "editing/none.md"})
        self.assertEqual(missing.status_code, 404)
        again = self.post("/api/runs", {"template_id": "literary-translation-v1", "work_id": work["id"]})
        self.assertEqual(again.status_code, 200, again.text)  # A completed run never blocks a new run.
        busy = self.post("/api/runs", {"template_id": "literary-translation-v1", "work_id": work["id"]})
        self.assertEqual((busy.status_code, busy.json()["code"]), (409, "work_busy"))  # One unfinished run per work.
        self.settle(again.json()["id"])

    def test_original_upload_downloads_under_its_name(self):
        data = self.source.read_bytes()
        upload = {"name": "洞 (draft).md", "data": base64.b64encode(data).decode()}
        work = self.post("/api/works", {"upload": upload, "manuscript_language": "zh"}).json()
        response = self.client.get(f"/api/works/{work['id']}/source")
        self.assertEqual((response.status_code, response.content), (200, data))
        self.assertEqual(response.headers["content-disposition"],
                         "attachment; filename=\"_ _draft_.md\"; filename*=UTF-8''%E6%B4%9E%20%28draft%29.md")
        self.assertEqual(self.client.get("/api/works/no-such-work/source").status_code, 404)

    def test_startup_profile_catalog_and_workflow_model_selection(self):
        from fastapi.testclient import TestClient
        from studio.server.app import create_app

        data = profile_data()
        data["models"].append({**data["models"][0], "key": "second-choice", "model": "another-model"})
        profile = ExecutionProfile(data)
        # Mutating the input cannot hot-reload the already constructed profile.
        data["models"][0]["model"] = "changed-outside-server"
        app = create_app(Path(self.temp.name) / "profile-server", execution_profile=profile)
        with TestClient(app, base_url=ORIGIN) as client:
            catalog = client.get("/api/execution").json()
            self.assertEqual(catalog["models"][0]["model"], "vendor/family/test-model")
            self.assertNotIn("api_key_env", json.dumps(catalog))
            work = client.post("/api/works", headers={"Origin": ORIGIN}, json={
                "upload": {"name": "original.md", "data": base64.b64encode(self.source.read_bytes()).decode()},
                "manuscript_language": "zh"}).json()
            payload = {"template_id": "literary-translation-v1", "work_id": work["id"], "start": False}
            rejected = client.post("/api/runs", headers={"Origin": ORIGIN},
                                   json={**payload, "model": "not-configured"})
            self.assertEqual(rejected.status_code, 400)
            self.assertIn("no fallback", rejected.json()["detail"])
            created = client.post("/api/runs", headers={"Origin": ORIGIN},
                                  json={**payload, "model": "second-choice"})
            self.assertEqual(created.status_code, 200, created.text)
            self.assertEqual(created.json()["execution"]["model"], "another-model")
            self.assertEqual(created.json()["execution"]["model_key"], "second-choice")
            self.assertEqual(created.json()["execution"]["endpoint"], "fixture")
            self.assertFalse(app.state.workers.status(created.json()["id"])["active"])

    def test_change_feed_reports_only_real_changes(self):
        from workflow.src.storage import Store
        live = self.app.state.live
        self.addCleanup(live.stop)  # Its read-only connections must close before the temporary folder is removed.
        upload = {"name": "original.md", "data": base64.b64encode(self.source.read_bytes()).decode()}
        work = self.post("/api/works", {"upload": upload, "manuscript_language": "zh"}).json()
        run_id = self.post("/api/runs", {"template_id": "literary-translation-v1", "work_id": work["id"],
                                         "start": False}).json()["id"]
        version = live.scan()
        snapshot = live.current()[1]
        self.assertEqual(set(snapshot["works"]), {work["id"]})
        before = snapshot["runs"][run_id]
        self.assertEqual(before["worker"]["active"], False)
        self.client.get(f"/api/runs/{run_id}")
        self.client.get(f"/api/works/{work['id']}")
        self.assertEqual(live.scan(), version)  # Reading never counts as a change.
        store = Store(Path(self.client.get(f"/api/runs/{run_id}").json()["path"]))
        store.event("item/agentMessage/delta", {})  # Agent streaming that the timeline hides.
        self.assertEqual(live.scan(), version)
        store.event("turn/started", {})
        store.close()
        self.assertEqual(live.scan(), version + 1)
        self.assertGreater(live.current()[1]["runs"][run_id]["event"], before["event"])
        self.post(f"/api/runs/{run_id}/resume")  # Runs preparation up to the metadata review.
        run = self.settle(run_id)
        live.scan()
        after = live.current()[1]["runs"][run_id]
        self.assertEqual(run["gate"]["kind"], "metadata_review")
        self.assertGreater(after["revision"], before["revision"])
        self.assertEqual(after["worker"]["stopped"], "WAITING_FOR_HUMAN")
        # The same fingerprints over HTTP: a snapshot, and a stream whose first message is the current snapshot.
        self.assertEqual(self.client.get("/api/live").json()["runs"][run_id], after)
        with self.client.stream("GET", "/api/live/stream") as response:
            self.assertEqual(response.headers["content-type"].split(";")[0], "text/event-stream")
            first = next(line for line in response.iter_lines() if line.startswith("data:"))
        self.assertEqual(json.loads(first.removeprefix("data:"))["runs"][run_id], after)

    def test_localhost_boundary(self):
        self.assertEqual(self.client.get("/api/works", headers={"Host": "evil.example:8765"}).status_code, 421)
        self.assertEqual(self.client.post("/api/runs", json={}).status_code, 403)
        self.assertEqual(self.client.post("/api/runs", json={}, headers={"Origin": "http://evil.example"}).status_code,
                         403)
        response = self.client.get("/api/templates")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        self.assertIn("literary-editing-v1", [t["id"] for t in response.json()])
        self.assertEqual(self.client.get("/api/runs/unknown").status_code, 404)
        from studio.server.app import create_app
        with self.assertRaisesRegex(ValueError, "loopback"):
            create_app(Path(self.temp.name) / "other", extra_origins=["http://evil.example:80"])


if __name__ == "__main__":
    unittest.main()
