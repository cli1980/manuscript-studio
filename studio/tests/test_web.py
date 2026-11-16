"""Run: python -m unittest studio.tests.test_web -v (requires studio/requirements.txt)."""

import base64
import contextlib
import importlib.util
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.src.execution import ExecutionProfile
from workflow.src.service import WorkflowService
from workflow.src.storage import digest, now
from workflow.tests.test_execution import profile_data

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
                          for name in ("literary-editing", "literary-translation", "literary-agent-querying",
                                       "format-manuscript")}}
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


class Scripted:
    def __init__(self, action):
        self.action = action

    def run(self, request, on_event, on_thread):
        on_thread("scripted-thread")
        on_event("test.turn", {})
        return self.action(request)


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
        self.post(f"/api/runs/{run_id}/metadata/confirm", {"gate_id": run["gate"]["id"], "record_revision": 1})
        run = self.settle(run_id)
        # The sample poll: each original beside its variants; one choice per sample, reasons optional.
        self.assertEqual((run["gate"]["kind"], run["gate"]["chapter_id"]), ("brief_samples", "front-matter"))
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
        self.assertEqual(chapters["chapters"][0]["outputs"]["translate"]["ready"], True)
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
