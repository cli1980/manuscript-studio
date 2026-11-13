"""Run every case under studio/tests/cases: python -m unittest studio.tests.test_cases -v."""

import importlib.util
import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from .runner import FIXTURES, CaseRunner, load_cases

HAS_WEB = importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx")


def live_feed(route, path, runs, revision=None):
    """Answer the studio's change feed for mocked runs. A run's fingerprint is `revision`, else its gate, so a new
    review counts as a change. The mocked stream ends after one snapshot; the browser reconnects shortly."""
    snapshot = {"version": 1, "works": {}, "runs": {run["id"]: {
        "revision": revision if revision is not None else (run.get("gate") or {}).get("id"),
        "event": 0, "worker": run["worker"]} for run in runs}}
    if path == "/api/live/stream":
        route.fulfill(content_type="text/event-stream", body=f"retry: 300\ndata: {json.dumps(snapshot)}\n\n")
    else:
        route.fulfill(json=snapshot)


@unittest.skipUnless(HAS_WEB, "Install studio/requirements.txt for studio case tests.")
class StudioCaseTests(unittest.TestCase):
    """Each case gets a fresh server root and app; no model runtime is started unless a case asks for one."""

    @unittest.skipUnless(os.environ.get("STUDIO_BROWSER") == "1", "Browser check: build the frontend and set STUDIO_BROWSER=1.")
    def test_workflow_creation_submits_the_selected_model(self):
        from urllib.parse import urlsplit
        from playwright.sync_api import expect

        def check(page, origin):
            submitted, errors = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            run = {"id": "model-run", "workflow": "literary-translation", "status": "READY",
                   "worker": {"active": False, "paused": False}}

            def serve(route):
                path = urlsplit(route.request.url).path
                if path.startswith("/api/live"):
                    return live_feed(route, path, [])
                if path == "/api/execution":
                    body = {"name": "pi-evaluation", "harness": "pi", "default_model": "one", "models": [
                        {"model_key": key, "model": model, "endpoint": endpoint,
                         "workflows": ["literary-translation"]}
                        for key, model, endpoint in (("one", "First model", "first"),
                                                    ("two", "Second model", "second"))]}
                elif path == "/api/templates":
                    body = [{"id": "literary-translation-v1", "title": "Literary translation",
                             "workflow": "literary-translation", "stages": ["prepare"], "choices": {}}]
                elif path == "/api/works":
                    body = [{"id": "model-work", "title": "Story", "manuscript_language": "zh"}]
                elif path == "/api/runs" and route.request.method == "POST":
                    submitted.append(route.request.post_data_json)
                    # Keep the form visible, so this test isolates model selection from run navigation.
                    route.fulfill(status=409, json={"detail": "Fixture stops before starting an agent."})
                    return
                elif path == "/api/runs":
                    body = []
                else:
                    self.fail(f"Unexpected browser request: {path}")
                route.fulfill(json=body)

            page.route("**/api/**", serve)
            page.goto(f"{origin}/#/runs")
            model = page.get_by_role("combobox", name="Model", exact=True)
            expect(model).to_have_value("one")
            model.select_option("two")
            page.get_by_role("combobox", name="Work", exact=True).select_option("model-work")
            page.get_by_role("button", name="Create and start", exact=True).click()
            expect(page.get_by_role("alert")).to_contain_text("Fixture stops")
            self.assertEqual(submitted, [{"template_id": "literary-translation-v1",
                                         "work_id": "model-work", "model": "two"}])
            expect(page.locator("form")).to_contain_text("without an OS sandbox")
            self.assertEqual(errors, [])

        with tempfile.TemporaryDirectory() as temporary:
            self.run_in_browser({}, Path(temporary) / "server",
                                lambda: self.fail("The browser fixture must not run an agent."), check=check)

    @unittest.skipUnless(os.environ.get("STUDIO_BROWSER") == "1", "Browser check: build the frontend and set STUDIO_BROWSER=1.")
    def test_feedback_stays_with_its_review(self):
        """Advance through approvals without reloading; old annotations must never enter the next reply."""
        from urllib.parse import urlsplit
        from playwright.sync_api import expect

        def check(page, origin):
            run_id = "feedback-check"
            passages = {"one": "First passage.", "two": "Second passage."}

            def review(chapter, gate_id, answer=None):
                return {
                    "id": run_id, "workflow": "literary-translation", "template_id": "literary-translation-v1",
                    "work_id": "test-work", "status": "WAITING_FOR_HUMAN", "stage": "translate", "chapter_id": chapter,
                    "worker": {"active": False, "paused": False}, "progress": {"completed": 0, "total": 2},
                    "finalized": False, "engine_current": True, "error": None, "attempts": 1,
                    "available_actions": [], "stage_titles": {"translate": "Translation"},
                    "gate": {"id": gate_id, "kind": "chapter_sanity", "chapter_id": chapter, "stage": "translate",
                             "binding_text": passages[chapter], "message": "No textual changes proposed.",
                             "commands": ["approve chapter"], "documents": [], "sheet": None,
                             "answer_to": {"text": answer, "created_at": "2026-11-06T00:00:00Z"} if answer else None},
                }

            current = review("one", "first-review")
            replies = []
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def serve(route):
                nonlocal current
                path = urlsplit(route.request.url).path
                prefix = f"/api/runs/{run_id}"
                if route.request.method == "POST":
                    self.assertEqual(path, prefix + "/reply")
                    replies.append(route.request.post_data_json)
                    if len(replies) == 1:
                        current = review("two", "second-review")
                    elif len(replies) == 2:
                        route.fulfill(status=409, json={"detail": "Please retry this submission."})
                        return
                    else:
                        current = review("two", "revised-review", replies[-1]["text"])
                    body = current
                elif path.startswith("/api/live"):
                    return live_feed(route, path, [current])
                elif path == "/api/runs":
                    body = [current]
                elif path == prefix:
                    body = current
                elif path == prefix + "/chapters":
                    body = {"prepared": True, "stages": ["translate"], "whole_book": {}, "chapters": [
                        {"chapter_id": name, "order": i + 1, "title": name, "role": "chapter",
                         "outputs": {"translate": {"status": "in_progress", "ready": False}}}
                        for i, name in enumerate(passages)]}
                elif path.startswith(prefix + "/chapters/"):
                    name = path.rsplit("/", 1)[-1]
                    body = {"chapter": {"chapter_id": name, "order": 1, "title": name, "role": "chapter"},
                            "prepared_text": "Original " + passages[name], "outputs": [], "reviews": [],
                            "passage_map": None}
                else:
                    self.fail(f"Unexpected browser request: {path}")
                route.fulfill(json=body)

            page.route("**/api/**", serve)
            page.add_init_script("""localStorage.setItem('comments:first-review:draft', JSON.stringify([
                {id: 'first-note', quote: 'First', start: 0, end: 5, paragraph: 1, note: 'Feedback for chapter one'}
            ]));""")
            page.goto(f"{origin}/#/runs/{run_id}/chapters/one")
            panel = page.locator(".panel.gate")
            expect(panel.locator(".comment-summary")).to_contain_text("Feedback for chapter one")
            general = panel.get_by_placeholder("General comment (optional)")
            general.fill("General for chapter one")
            page.get_by_role("button", name="Approve chapter", exact=True).click()

            # The same mounted viewer advances to the next chapter, with no reload.
            expect(page).to_have_url(re.compile(r"/chapters/two$"))
            expect(panel.locator(".comment-summary")).to_contain_text("Your comments (0)")
            expect(panel).not_to_contain_text("Feedback for chapter one")
            expect(general).to_have_value("")
            expect(panel.get_by_role("button", name="Send feedback", exact=True)).to_be_disabled()

            # A failed submission keeps this review's draft; retry sends only this chapter's feedback.
            general.fill("Feedback only for chapter two")
            page.get_by_role("button", name="Send feedback", exact=True).click()
            expect(page.get_by_role("alert")).to_contain_text("Please retry")
            expect(general).to_have_value("Feedback only for chapter two")
            page.get_by_role("button", name="Send feedback", exact=True).click()
            expect(panel.locator(".conversation")).to_contain_text("Feedback only for chapter two")
            expect(general).to_have_value("")
            expect(panel.locator(".comment-summary")).to_contain_text("Your comments (0)")
            self.assertEqual(replies, [
                {"gate_id": "first-review", "text": "approve chapter"},
                {"gate_id": "second-review", "text": "Feedback only for chapter two"},
                {"gate_id": "second-review", "text": "Feedback only for chapter two"},
            ])
            self.assertEqual(errors, [])

        with tempfile.TemporaryDirectory() as temporary:
            self.run_in_browser({}, Path(temporary) / "server",
                                lambda: self.fail("The browser fixture must not run an agent."), check=check)

    @unittest.skipUnless(os.environ.get("STUDIO_BROWSER") == "1", "Browser check: build the frontend and set STUDIO_BROWSER=1.")
    def test_whole_book_decision_follows_reading_area(self):
        """A decision not tied to one chapter (e.g. the developmental verdict) sits after the reading area."""
        from urllib.parse import urlsplit
        from playwright.sync_api import expect

        def check(page, origin):
            run_id = "placement-check"
            run = {
                "id": run_id, "workflow": "literary-editing", "template_id": "literary-editing-v1",
                "work_id": "test-work", "status": "WAITING_FOR_HUMAN", "stage": "developmental", "chapter_id": "_whole",
                "worker": {"active": False, "paused": False}, "progress": {"completed": 1, "total": 1},
                "finalized": False, "engine_current": True, "error": None, "attempts": 1,
                "available_actions": [], "stage_titles": {"developmental": "Developmental edit"},
                "gate": {"id": "verdict", "kind": "editorial_review", "chapter_id": "_whole", "stage": "developmental",
                         "binding_text": None, "message": "Whole-book verdict: ready.", "commands": ["approve review"],
                         "documents": [], "sheet": None, "answer_to": None},
            }
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def serve(route):
                path = urlsplit(route.request.url).path
                prefix = f"/api/runs/{run_id}"
                if path.startswith("/api/live"):
                    return live_feed(route, path, [run])
                if path == "/api/runs":
                    body = [run]
                elif path == prefix:
                    body = run
                elif path == prefix + "/chapters":
                    body = {"prepared": True, "stages": ["developmental"], "whole_book": {"developmental": "in_progress"},
                            "chapters": [{"chapter_id": "one", "order": 1, "title": "One", "role": "chapter",
                                          "outputs": {"developmental": {"status": "completed", "ready": True}}}]}
                elif path == prefix + "/chapters/one":
                    body = {"chapter": {"chapter_id": "one", "order": 1, "title": "One", "role": "chapter"},
                            "prepared_text": "Chapter text.", "outputs": [], "reviews": [], "passage_map": None}
                else:
                    self.fail(f"Unexpected browser request: {path}")
                route.fulfill(json=body)

            page.route("**/api/**", serve)
            follows = "(panel, before) => !!(before.compareDocumentPosition(panel) & Node.DOCUMENT_POSITION_FOLLOWING)"
            for chapter, before in (("/one", ".columns"), ("", "text=Select a chapter to read it.")):
                page.goto(f"{origin}/#/runs/{run_id}/chapters{chapter}")
                panel = page.locator(".panel.gate")
                expect(panel).to_have_count(1)
                expect(panel).to_contain_text("Whole-book verdict: ready.")
                page.locator(before).wait_for()
                self.assertTrue(panel.evaluate(follows, page.locator(before).element_handle()))
            self.assertEqual(errors, [])

        with tempfile.TemporaryDirectory() as temporary:
            self.run_in_browser({}, Path(temporary) / "server",
                                lambda: self.fail("The browser fixture must not run an agent."), check=check)

    @unittest.skipUnless(os.environ.get("STUDIO_BROWSER") == "1", "Browser check: build the frontend and set STUDIO_BROWSER=1.")
    def test_run_page_follows_the_change_feed_instead_of_polling(self):
        """While the feed reports no change, the run page fetches nothing; a change refreshes it without a reload."""
        from collections import Counter
        from urllib.parse import urlsplit
        from playwright.sync_api import expect

        def check(page, origin):
            run_id = "feed-check"
            run = {
                "id": run_id, "workflow": "literary-editing", "template_id": "literary-editing-v1",
                "template_title": "Literary editing", "work_id": "test-work", "status": "RUNNING", "stage": "line",
                "chapter_id": "two", "worker": {"active": True, "paused": False}, "progress": {"completed": 1, "total": 3},
                "finalized": False, "engine_current": True, "error": None, "attempts": 3, "available_actions": [],
                "stages": ["prepare", "line"], "stage_titles": {}, "passes": [], "manuscript_language": "zh",
                "settings": {}, "gate": None,
                "usage": {"input_tokens": 1200, "output_tokens": 300, "cached_input_tokens": 700,
                          "total_tokens": 1500, "reported_attempts": 2, "attempts": 3,
                          "partial": True, "warnings": ["Some agent turns have not reported token usage."]},
            }
            state = {"revision": 1}
            requests = Counter()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def serve(route):
                path = urlsplit(route.request.url).path
                requests[path] += 1
                if path.startswith("/api/live"):
                    return live_feed(route, path, [run], state["revision"])
                if path == "/api/runs":
                    body = [run]
                elif path == f"/api/runs/{run_id}":
                    body = run
                elif path == f"/api/runs/{run_id}/events":
                    body = {"events": [], "last_id": 0}
                else:
                    self.fail(f"Unexpected browser request: {path}")
                route.fulfill(json=body)

            page.route("**/api/**", serve)
            page.goto(f"{origin}/#/runs/{run_id}")
            expect(page.locator(".facts").first).to_contain_text("1/3 chapters")
            expect(page.locator(".token-usage")).to_contain_text("1,500")
            expect(page.locator(".token-usage")).to_contain_text("(partial)")
            page.wait_for_timeout(1500)  # The initial load and the first snapshot settle.
            settled = requests[f"/api/runs/{run_id}"]
            page.wait_for_timeout(4000)  # Longer than any old polling interval; the feed reconnects meanwhile.
            self.assertGreater(requests["/api/live/stream"], 2)
            self.assertEqual(requests[f"/api/runs/{run_id}"], settled)
            run["progress"] = {"completed": 2, "total": 3}
            run["usage"].update(total_tokens=1800, input_tokens=1500, reported_attempts=3, partial=False, warnings=[])
            state["revision"] = 2
            expect(page.locator(".facts").first).to_contain_text("2/3 chapters")
            expect(page.locator(".token-usage")).to_contain_text("1,800")
            expect(page.locator(".token-usage")).not_to_contain_text("(partial)")
            self.assertEqual(requests[f"/api/runs/{run_id}"], settled + 1)
            self.assertEqual(errors, [])

        with tempfile.TemporaryDirectory() as temporary:
            self.run_in_browser({}, Path(temporary) / "server",
                                lambda: self.fail("The browser fixture must not run an agent."), check=check)

    def run_case(self, case):
        from fastapi.testclient import TestClient
        from studio.server.app import create_app

        def no_runtime():
            raise AssertionError("This case must not start an agent turn.")

        runtime = no_runtime
        live = case.get("runtime")
        if live:
            # Live cases run real agent turns; opt in with STUDIO_LIVE=1 (and CODEX=path if not on PATH).
            if os.environ.get("STUDIO_LIVE") != "1":
                self.skipTest("Live case: set STUDIO_LIVE=1 to run it with Codex.")
            for name in live.get("fixtures", []):
                if not (FIXTURES / name).is_file():
                    self.skipTest(f"Local-only fixture missing: fixtures/{name}")
            from workflow.src.runtime import CodexRuntime
            codex, timeout = os.environ.get("CODEX", "codex"), float(live.get("turn_timeout", 900))
            runtime = lambda: CodexRuntime([codex, "app-server"], timeout)  # noqa: E731
        root = os.environ.get("STUDIO_CASE_ROOT")  # Keep a live case's server root for inspection.
        with tempfile.TemporaryDirectory() as temporary:
            server = Path(root) / case["case_id"] if root else Path(temporary) / "server"
            if live and live.get("client") == "browser":
                self.run_in_browser(case, server, runtime)
                return
            app = create_app(server, runtime_factory=runtime, owner="case-runner")
            with TestClient(app, base_url="http://127.0.0.1:8765") as client:
                CaseRunner(client, case).run()

    def run_in_browser(self, case, server, runtime, *, check=None):
        """Serve the studio on its own port and make every reviewer choice by clicking its pages.

        Watch it at http://127.0.0.1:<STUDIO_CASE_PORT> (default 8766), or show the automated browser with
        STUDIO_HEADED=1 (STUDIO_SLOW_MO=ms slows its clicks). STUDIO_ALLOW_ORIGIN adds a loopback preview origin.
        """
        import threading
        import time

        import httpx
        import uvicorn
        from playwright.sync_api import sync_playwright
        from studio.server.app import create_app

        port = int(os.environ.get("STUDIO_CASE_PORT", "8766"))
        extra = [o for o in os.environ.get("STUDIO_ALLOW_ORIGIN", "").split(",") if o]
        app = create_app(server, port=port, runtime_factory=runtime, owner="case-runner", extra_origins=extra)
        web = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        thread = threading.Thread(target=web.run, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if web.started:
                    break
                time.sleep(0.1)
            origin = f"http://127.0.0.1:{port}"
            with httpx.Client(base_url=origin, timeout=120) as client, sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=os.environ.get("STUDIO_HEADED") != "1",
                                                     slow_mo=int(os.environ.get("STUDIO_SLOW_MO", "0")))
                try:
                    page = browser.new_page()
                    if check:
                        check(page, origin)
                    else:
                        CaseRunner(client, case, origin=origin, page=page).run()
                finally:
                    browser.close()
        finally:
            web.should_exit = True
            thread.join(10)


def _make(case):
    def test(self):
        self.run_case(case)
    test.__doc__ = case.get("title")
    return test


for _case in load_cases():
    setattr(StudioCaseTests, "test_" + _case["case_id"].replace("-", "_"), _make(_case))


if __name__ == "__main__":
    unittest.main()
