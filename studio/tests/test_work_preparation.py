"""Production Work-preparation API and worker tests (no inline-intake templates)."""

import base64
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from studio.server.live import Watcher
from studio.tests import test_web as fixtures
from workflow.src.service import WorkflowService


@unittest.skipUnless(fixtures.HAS_WEB, "Install studio/requirements.txt.")
class WorkPreparationApiTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from studio.server.app import create_app
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name) / "server"
        self.app = create_app(self.root, runtime_factory=lambda: fixtures.Scripted(fixtures.translate), owner="tester")
        self.client = TestClient(self.app, base_url=fixtures.ORIGIN)
        self.addCleanup(self.client.close)

    def post(self, path, payload=None):
        response = self.client.post(path, json=payload or {}, headers={"Origin": fixtures.ORIGIN})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def settle(self, job):
        self.app.state.workers.wait(job, 30)
        self.assertFalse(self.app.state.workers.status(job)["active"])
        return self.client.get(f"/api/runs/{job}").json()

    def test_prepare_once_then_reuse_through_public_api(self):
        work = self.post("/api/works", {"upload": {
            "name": "source.md", "data": base64.b64encode("# Story\n\nHe came back.\n".encode()).decode()}})
        work_id = work["id"]
        refused = self.client.post("/api/runs", json={"template_id": "literary-editing-v1", "work_id": work_id},
                                   headers={"Origin": fixtures.ORIGIN})
        self.assertEqual(refused.json()["code"], "work_not_prepared")
        job = self.post(f"/api/works/{work_id}/prepare")["id"]
        state = self.settle(job)
        self.assertEqual(state["gate"]["kind"], "metadata_review")
        self.assertEqual(self.client.get("/api/runs").json(), [])
        self.post(f"/api/runs/{job}/metadata/confirm", {
            "gate_id": state["gate"]["id"], "record_revision": state["gate"]["record_revision"]})
        state = self.settle(job)
        self.assertEqual(state["status"], "COMPLETED", state)
        self.assertEqual(state["attempts"], 2)
        work = self.client.get(f"/api/works/{work_id}").json()
        self.assertEqual(len(work["versions"]), 1)
        version = work["versions"][0]
        self.assertEqual(version["analysis_status"], "provisional")
        self.assertEqual(work["runs"], [])
        run = self.post("/api/runs", {"template_id": "literary-translation-v1", "work_id": work_id,
                                      "work_version_id": version["version_id"], "start": False})
        self.assertEqual(run["stage"], "brief")
        self.assertEqual(run["input_version"]["analysis_id"], version["analysis_id"])
        self.assertEqual(run["attempts"], 0)
        self.assertEqual([r["id"] for r in self.client.get("/api/runs").json()], [run["id"]])
        watcher = Watcher(self.root, self.app.state.workers)
        try:
            watcher.scan()
            self.assertEqual(set(watcher.current()[1]["runs"]), {job, run["id"]})
        finally:
            watcher.stop()
        document = next(doc for doc in version["documents"] if doc["path"].endswith("reading-profile.md"))
        url = f"/api/works/{work_id}/versions/{version['version_id']}/artifact"
        original = self.client.get(url, params={"path": document["path"]}).json()
        with WorkflowService(self.root) as service:
            service.library(work_id).path(document["artifact"]).write_bytes(b"Changed browsable copy")
        self.assertEqual(self.client.get(url, params={"path": document["path"]}).json(), original)
        self.assertEqual(self.client.get(url, params={"path": "../work.json"}).status_code, 404)


@unittest.skipUnless(fixtures.HAS_WEB and os.environ.get("STUDIO_BROWSER") == "1",
                     "Build the frontend and set STUDIO_BROWSER=1 for desktop/mobile checks.")
class WorkPreparationBrowserTests(unittest.TestCase):
    def test_work_preparation_review_and_version_selection_desktop_mobile(self):
        from playwright.sync_api import expect
        from studio.server import app as app_module
        from studio.tests.test_cases import StudioCaseTests

        def check(page, origin):
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            for width in (1280, 390):
                page.set_viewport_size({"width": width, "height": 900})
                page.goto(origin + "/#/works")
                page.locator('input[type="file"]').set_input_files({
                    "name": f"story-{width}.md", "mimeType": "text/markdown",
                    "buffer": b"# Story\n\nHe came back.\n",
                })
                with page.expect_response(lambda response: response.url == origin + "/api/works"
                                          and response.request.method == "POST") as uploaded:
                    page.get_by_role("button", name="Add as a new work", exact=True).click()
                work_id = uploaded.value.json()["id"]
                start = page.get_by_role("heading", name="Start a workflow", exact=True).locator("..")
                expect(start.get_by_role("button", name="Start", exact=True)).to_be_disabled()
                page.get_by_role("button", name="Prepare and analyze", exact=True).click()
                expect(page.get_by_role("button", name=re.compile(r"^Confirm metadata \(revision"))).to_be_visible(timeout=30000)
                self.assertIn(f"#/works/{work_id}/preparations/", page.url)
                page.get_by_role("button", name=re.compile(r"^Confirm metadata \(revision")).click()
                ready = page.get_by_role("link", name="Choose it for a workflow", exact=True)
                expect(ready).to_be_visible(timeout=30000)
                ready.click()
                detail = page.request.get(origin + f"/api/works/{work_id}").json()
                version = detail["versions"][0]
                self.assertEqual(version["status"], "ready")
                self.assertEqual(detail["runs"], [])
                start = page.get_by_role("heading", name="Start a workflow", exact=True).locator("..")
                start.get_by_label("Prepared version", exact=True).select_option(version["version_id"])
                start.get_by_label("Workflow", exact=True).select_option("literary-translation-v1")
                self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2"),
                    page.evaluate("""() => ({width: innerWidth, scroll: document.documentElement.scrollWidth,
                        overflow: [...document.querySelectorAll('body *')].filter(e =>
                        e.getBoundingClientRect().right > innerWidth + 2).slice(0, 12).map(e =>
                        [e.tagName, e.className, e.textContent?.slice(0, 200)])})"""))
                with page.expect_response(lambda response: response.url == origin + "/api/runs"
                                          and response.request.method == "POST") as created:
                    start.get_by_role("button", name="Start", exact=True).click()
                run = created.value.json()
                self.assertEqual(run["input_version"]["version_id"], version["version_id"])
                self.assertNotIn("prepare", run["stages"])
                self.assertNotIn("analysis", run["stages"])
                expect(page.get_by_role("heading", name="Manuscript Analysis", exact=True)).to_be_visible(timeout=30000)
                self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2"))
            self.assertEqual(errors, [])

        frontend = Path(os.environ["STUDIO_TEST_FRONTEND"]) if os.environ.get("STUDIO_TEST_FRONTEND") else app_module.FRONTEND
        self.assertTrue((frontend / "index.html").is_file(), "Build a test frontend first.")
        with tempfile.TemporaryDirectory() as folder, patch.object(app_module, "FRONTEND", frontend):
            StudioCaseTests().run_in_browser({}, Path(folder) / "server",
                lambda: fixtures.Scripted(fixtures.translate), check=check)
