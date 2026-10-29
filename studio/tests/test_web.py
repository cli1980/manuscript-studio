"""Run: python -m unittest studio.tests.test_web -v (requires studio/requirements.txt)."""

import base64
import importlib.util
import json
import tempfile
import time
import unittest
from pathlib import Path

from workflow.src.storage import digest, now

HAS_WEB = importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx")
ORIGIN = "http://127.0.0.1:8765"


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


def translate(request):
    """A scripted translation agent driven only by the saved receipts it is given."""
    ctx, cwd = context(request), request.cwd
    if ctx["stage"] == "prepare":
        return prepare(request)
    receipt = ctx["user_receipt"] or {}
    command = receipt.get("parsed", {}).get("command") or ""
    if ctx["chapter"]["chapter_id"] == "front-matter":
        # The front matter: an internal map without exceptions, then chapter approval.
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

    def test_translation_runs_through_every_gate_from_the_browser_api(self):
        upload = {"name": "original.md", "data": base64.b64encode(self.source.read_bytes()).decode()}
        refused = self.post("/api/runs", {"template_id": "literary-translation-v1", "upload": upload,
                                          "manuscript_language": "zh"})
        self.assertIn("Works page", refused.json()["detail"])  # Intake belongs to the Works page.
        added = self.post("/api/works", {"upload": upload, "manuscript_language": "zh"})
        self.assertEqual(added.status_code, 200, added.text)
        self.assertEqual((added.json()["runs"], added.json()["unfinished_run"]), ([], None))
        created = self.post("/api/runs", {"template_id": "literary-translation-v1", "work_id": added.json()["id"]})
        self.assertEqual(created.status_code, 200, created.text)
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
        self.assertEqual((run["gate"]["kind"], run["gate"]["chapter_id"]), ("chapter_sanity", "front-matter"))
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
        self.assertEqual(run["status"], "WAITING_FOR_ACCEPTANCE")
        accept = next(a for a in run["available_actions"] if a["action"] == "accept")
        self.assertTrue(accept["irreversible"])
        refused = self.post(f"/api/runs/{run_id}/accept", {"acceptance_id": run["acceptance"]["acceptance_id"]})
        self.assertEqual((refused.status_code, refused.json()["code"]), (409, "confirmation_required"))
        self.post(f"/api/runs/{run_id}/accept", {"acceptance_id": run["acceptance"]["acceptance_id"],
                                                 "confirm_final": True})
        run = self.settle(run_id)
        self.assertEqual((run["status"], run["finalized"]), ("COMPLETED", True))

        chapters = self.client.get(f"/api/runs/{run_id}/chapters").json()
        self.assertTrue(chapters["prepared"])
        self.assertEqual(chapters["chapters"][0]["outputs"]["translate"]["ready"], True)
        chapter = self.client.get(f"/api/runs/{run_id}/chapters/story").json()
        self.assertEqual((chapter["prepared_text"], chapter["outputs"][0]["text"]), ("# 故事\n\n他回来了。\n",
                                                                                   "He came back.\n"))
        events = self.client.get(f"/api/runs/{run_id}/events").json()["events"]
        self.assertTrue(events and not any(e["kind"] == "test.turn" for e in events))

        works = self.client.get("/api/works").json()
        self.assertEqual(len(works), 1)
        work = self.client.get(f"/api/works/{works[0]['id']}").json()
        self.assertEqual(work["workflows"]["literary-translation"]["status"], "completed")
        self.assertEqual(work["metadata"]["metadata"]["title"], "Story")
        text = self.client.get(f"/api/works/{work['id']}/artifact",
                               params={"path": "literary-translation/v001/chapters/0002.md"})
        self.assertEqual(text.text, "He came back.\n")
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
