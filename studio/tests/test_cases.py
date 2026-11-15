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

    @unittest.skipUnless(os.environ.get("STUDIO_BROWSER") == "1", "Browser check: build frontend and set STUDIO_BROWSER=1.")
    def test_intake_language_starts_blank_and_does_not_block_upload(self):
        from playwright.sync_api import expect

        def check(page, origin):
            page.goto(origin + "/#/works")
            expect(page.get_by_label("Language hint (optional)")).to_have_value("")
            page.locator('input[type="file"]').set_input_files({
                "name": "story.md", "mimeType": "text/markdown",
                "buffer": b"# A story\n\nThe morning light fell across the empty room.\n",
            })
            button = page.get_by_role("button", name="Add as a new work")
            expect(button).to_be_enabled()
            with page.expect_response(lambda r: r.url == origin + "/api/works" and r.request.method == "POST") as added:
                button.click()
            self.assertTrue(added.value.ok, added.value.text())
            self.assertIsNone(added.value.json()["manuscript_language"])
            expect(page.get_by_text("language pending preparation", exact=False)).to_be_visible()
            author = page.locator(".author-form")
            title = author.locator(".form-row").filter(has=page.locator("label").filter(has_text=re.compile("^Title$"))).locator("input")
            subtitle = author.locator(".form-row").filter(has=page.locator("label").filter(has_text=re.compile("^Subtitle$"))).locator("input")
            expect(title).to_be_visible()
            expect(subtitle).to_be_visible()
            title.fill("My own title, not present in the manuscript")
            with page.expect_response(lambda r: r.url.endswith("/metadata") and r.request.method == "POST") as saved:
                author.get_by_role("button", name=re.compile("^Save")).click()
            self.assertTrue(saved.value.ok, saved.value.text())
            expect(page.get_by_role("heading", name="My own title, not present in the manuscript", exact=True)).to_be_visible()
            workflow = page.get_by_role("heading", name="Start a workflow", exact=True).locator("..")
            workflow.get_by_role("combobox").select_option("literary-translation-v1")
            workflow.locator("summary").filter(has_text="Advanced").click()
            limit = workflow.get_by_label("Maximum passage size", exact=False)
            expect(limit).to_have_attribute("placeholder", "Automatic")
            limit.fill("1100")
            expect(limit).to_have_value("1100")

        with tempfile.TemporaryDirectory() as temporary:
            self.run_in_browser({}, Path(temporary) / "server", lambda: None, check=check)

    @unittest.skipUnless(os.environ.get("STUDIO_BROWSER") == "1", "Browser check: build frontend and set STUDIO_BROWSER=1.")
    def test_editable_interior_design_gate(self):
        """Real API/engine with a scripted skill: edit, save and approve from the browser."""
        import base64
        import time

        from playwright.sync_api import expect
        from .test_web import Scripted, interior_design

        def check(page, origin):
            errors = []
            server_errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("response", lambda response: server_errors.append(response.url)
                    if "/api/" in response.url and response.status >= 500 else None)
            headers = {"Origin": origin}
            work = page.request.post(origin + "/api/works", headers=headers, data={
                "upload": {"name": "synthetic.md", "data": base64.b64encode(b"# Story\n\nA short story.\n").decode()},
                "manuscript_language": "zh",
            }).json()
            page.goto(origin + "/#/works/" + work["id"])
            expect(page.get_by_role("heading", name="Format as DOCX", exact=True)).to_have_count(0)
            start = page.get_by_role("heading", name="Start a workflow", exact=True).locator("..")
            expect(start.get_by_role("combobox").locator('option[value="manuscript-formatting-v1"]')).to_have_count(0)
            start.get_by_role("combobox").select_option("literary-editing-v1")
            with page.expect_response(lambda r: r.url == origin + "/api/runs" and r.request.method == "POST") as created:
                start.get_by_role("button", name="Start", exact=True).click()
            self.assertTrue(created.value.ok, created.value.text())
            run = created.value.json()
            run_url = origin + "/api/runs/" + run["id"]
            for _ in range(100):
                run = page.request.get(run_url).json()
                if run.get("gate"):
                    break
                time.sleep(0.1)
            self.assertEqual(run["gate"]["kind"], "metadata_review")
            confirmed = page.request.post(run_url + "/metadata/confirm", headers=headers, data={
                "gate_id": run["gate"]["id"], "record_revision": run["metadata"]["record_revision"],
            })
            self.assertTrue(confirmed.ok, confirmed.text())
            page.goto(f"{origin}/#/runs/{run['id']}/chapters")
            expect(page.get_by_role("button", name="Format", exact=True)).to_have_count(0)
            expect(page.get_by_role("button", name="Proceed to interior design", exact=True)).to_have_count(0)
            page.get_by_role("button", name="Review manuscript", exact=True).click()
            expect(page.get_by_role("heading", name="Approve manuscript for formatting", exact=True)).to_be_visible()
            expect(page.get_by_label("Purpose", exact=True)).to_have_value("print-ready")
            page.get_by_label("Purpose", exact=True).select_option("editorial-review")
            page.get_by_label("Binding", exact=True).select_option("hardcover")
            page.get_by_label("Print vendor", exact=True).select_option("ingramspark")
            expect(page.get_by_text("Loaded profile: IngramSpark / Hardcover", exact=True)).to_be_visible()
            page.get_by_label("Binding", exact=True).select_option("paperback")
            expect(page.get_by_text("Loaded profile: IngramSpark / Paperback", exact=True)).to_be_visible()
            page.get_by_label("Binding", exact=True).select_option("hardcover")
            approve = page.get_by_role("button", name="Approve manuscript and continue", exact=True)
            expect(approve).to_be_disabled()
            page.get_by_role("checkbox", name="I approve this manuscript for formatting.", exact=True).check()
            approve.click()
            expect(page.get_by_role("heading", name="Review formatting specification")).to_be_visible()
            current = page.request.get(run_url).json()
            self.assertEqual(current["gate"]["design_review"]["proposal"]["vendor_profile"]["variant_id"], "hardcover")
            self.assertEqual(current["gate"]["design_review"]["proposal"]["edition_brief"]["purpose"], "editorial-review")
            expect(page.get_by_label("Purpose", exact=True)).to_have_count(0)
            expect(page.get_by_label("Binding", exact=True)).to_have_count(0)
            expect(page.get_by_label("Print vendor", exact=True)).to_have_count(0)
            expect(page.get_by_role("button", name="Update target and revise proposal", exact=True)).to_have_count(0)
            expect(page.get_by_text("Print vendor: IngramSpark / Hardcover", exact=True)).to_be_visible()
            targets = page.locator("summary").filter(has_text=re.compile(r"^production targets \(1\)$")).locator("..")
            targets.locator("summary").first.click()
            edition = targets.locator("summary").filter(has_text=re.compile("^Output 1$")).locator("..")
            edition.locator("summary").first.click()
            for name in ("id", "vendor id", "binding", "vendor profile ref"):
                expect(edition.get_by_label(name, exact=True)).to_have_count(0)
                expect(edition.get_by_label(name + " (read-only)", exact=True)).to_have_count(0)
            expect(page.get_by_text("vendor_profile/data", exact=False)).to_have_count(0)
            expect(page.get_by_label("preferred page count", exact=True)).to_have_count(0)
            expect(page.get_by_text("Advanced specification JSON", exact=True)).to_have_count(0)
            expect(page.get_by_text("Complete bound proposal (read-only)", exact=True)).to_have_count(0)
            expect(page.get_by_text("Questions before design approval", exact=True)).to_have_count(0)
            self.assertTrue(all(q["kind"] in ("author-input", "design-choice")
                                for q in current["gate"]["design_review"]["proposal"]["questions"]))
            page.locator("summary").filter(has_text=re.compile(r"^styles \(2\)$")).click()
            body = page.locator("summary").filter(has_text=re.compile("^body$")).locator("..")
            body.locator("summary").first.click()
            body.locator("summary").filter(has_text=re.compile("^font$")).click()
            body.get_by_label("family", exact=True).fill("Garamond")
            body.get_by_label("size pt", exact=True).fill("12")
            gutter = page.get_by_label("gutter mm", exact=True)
            expect(gutter).to_have_value("3")
            expect(page.get_by_label("gutter mm in inches", exact=True)).to_have_text("(0.118 in)")
            gutter.fill("5")
            expect(page.get_by_label("gutter mm in inches", exact=True)).to_have_text("(0.197 in)")
            expect(page.get_by_role("button", name="Approve this design specification")).to_be_disabled()
            with page.expect_response(lambda r: r.url == run_url + "/interior-design") as saved:
                page.get_by_role("button", name="Save specification changes").click()
            self.assertTrue(saved.value.ok, saved.value.text())
            expect(page.get_by_text(re.compile("Specification revision 2"))).to_be_visible()
            expect(page.get_by_role("button", name="Save specification changes")).to_be_disabled()
            expect(gutter).to_have_value("5")
            current = page.request.get(run_url).json()
            self.assertEqual(current["gate"]["design_review"]["proposal"]["design_system"]["page"]["gutter_mm"], 5)
            self.assertEqual(current["gate"]["design_review"]["proposal"]["design_system"]["styles"][0]["font"]["family"], "Garamond")
            self.assertEqual(current["gate"]["design_review"]["proposal"]["design_system"]["styles"][0]["font"]["size_pt"], 12)
            self.assertEqual(current["gate"]["design_review"]["proposal"]["revision"], 2)
            self.assertEqual(current["gate"]["design_review"]["proposal"]["vendor_profile"]["variant_id"], "hardcover")
            self.assertEqual(current["gate"]["design_review"]["proposal"]["edition_brief"]["purpose"], "editorial-review")
            evidence = os.environ.get("STUDIO_EVIDENCE_DIR")
            if evidence:
                page.screenshot(path=str(Path(evidence) / "interior-gate-desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            expect(gutter).to_be_visible()
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 391)
            if evidence:
                page.screenshot(path=str(Path(evidence) / "interior-gate-mobile.png"), full_page=True)
            for question in current["gate"]["design_review"]["proposal"]["questions"]:
                if question["blocking"]:
                    page.get_by_label(question["question"], exact=False).fill("Keep the proposed new-page openings.")
            with page.expect_response(lambda r: r.url == run_url + "/interior-design") as approved:
                page.get_by_role("button", name="Approve this design specification").click()
            self.assertTrue(approved.value.ok, approved.value.text())
            expect(page.get_by_text(re.compile("Interior design approved. Deterministic document production"))).to_be_visible()
            current = page.request.get(run_url).json()
            self.assertEqual((current["status"], current["finalized"], current["attempts"]), ("BLOCKED", False, 2))
            page.goto(origin + "/#/works/" + work["id"])
            expect(page.get_by_role("heading", name="Story", exact=True)).to_be_visible()
            expect(page.locator(".metadata tr").filter(
                has=page.locator("th").filter(has_text=re.compile("^Title$")))).to_contain_text("Story")
            expect(page.locator(".metadata tr").filter(
                has=page.locator("th").filter(has_text=re.compile("^Manuscript language$")))).to_contain_text("zh")
            expect(page.get_by_role("heading", name="Detected or measured", exact=True)).to_be_visible()
            self.assertEqual(errors, [])
            self.assertEqual(server_errors, [])

        with tempfile.TemporaryDirectory() as temporary:
            self.run_in_browser({}, Path(temporary) / "server", lambda: Scripted(interior_design), check=check)

    @unittest.skipUnless(os.environ.get("STUDIO_BROWSER") == "1", "Browser check: build the frontend and set STUDIO_BROWSER=1.")
    def test_works_creation_requires_a_compatible_model_and_supports_legacy_execution(self):
        from urllib.parse import urlsplit
        from playwright.sync_api import expect

        def check(page, origin):
            submitted, errors = [], []
            configured = True
            page.on("pageerror", lambda error: errors.append(str(error)))
            work = {"id": "model-work", "title": "Story", "manuscript_language": "en", "source_name": "story.md",
                    "owner": "test", "runs": [], "publications": [], "workflows": {}, "heads": {},
                    "unfinished_run": None, "metadata": None}

            def serve(route):
                path = urlsplit(route.request.url).path
                if path.startswith("/api/live"):
                    return live_feed(route, path, [])
                if path == "/api/execution":
                    body = {"name": "evaluation", "harness": "pi", "default_model": "translation", "models": [
                        {"model_key": key, "model": key, "harness": "pi", "endpoint": "fixture", "workflows": flows}
                        for key, flows in (("translation", ["literary-translation"]), ("editing", ["literary-editing"]),
                                           ("shared", []))] if configured else []}
                elif path == "/api/templates":
                    body = [{"id": name + "-v1", "title": name, "workflow": name, "stages": ["prepare"],
                             "choices": {}} for name in ("literary-translation", "literary-editing")]
                elif path == "/api/works/model-work":
                    body = work
                elif path == "/api/runs" and route.request.method == "POST":
                    submitted.append(route.request.post_data_json)
                    return route.fulfill(status=409, json={"detail": "Fixture stops before agent startup."})
                elif path == "/api/runs":
                    body = []
                else:
                    self.fail(f"Unexpected browser request: {path}")
                route.fulfill(json=body)

            page.route("**/api/**", serve)
            page.goto(f"{origin}/#/works/model-work")
            workflow = page.get_by_role("combobox").first
            workflow.select_option("literary-editing-v1")
            model = page.get_by_role("combobox", name="Model", exact=True)
            start = page.get_by_role("button", name="Start", exact=True)
            expect(model).to_have_value("")
            expect(model.locator("option")).to_have_count(3)
            expect(start).to_be_disabled()
            model.select_option("editing")
            start.click()
            expect(page.get_by_role("alert")).to_contain_text("Fixture stops")
            self.assertEqual(submitted[-1], {"template_id": "literary-editing-v1",
                                           "work_id": "model-work", "model": "editing"})
            workflow.select_option("literary-translation-v1")
            expect(model).to_have_value("translation")
            model.select_option("shared")
            workflow.select_option("literary-editing-v1")
            expect(model).to_have_value("")
            expect(start).to_be_disabled()

            configured = False
            page.reload()
            page.get_by_role("combobox").first.select_option("literary-editing-v1")
            expect(page.get_by_role("combobox", name="Model", exact=True)).to_have_count(0)
            page.get_by_role("button", name="Start", exact=True).click()
            expect(page.get_by_role("alert")).to_contain_text("Fixture stops")
            self.assertNotIn("model", submitted[-1])
            self.assertEqual(errors, [])

        with tempfile.TemporaryDirectory() as temporary:
            self.run_in_browser({}, Path(temporary) / "server",
                                lambda: self.fail("The browser fixture must not run an agent."), check=check)

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
