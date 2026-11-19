"""Run every case under studio/tests/cases: python -m unittest studio.tests.test_cases -v."""

import importlib.util
import json
import os
import re
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from lxml import etree

from workflow.src.storage import digest
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

    def prepared_input(self, page, origin, work_id, *, metadata=None):
        """Build real Work inputs; individual browser cases then focus on their consumer UI."""
        headers = {"Origin": origin}
        response = page.request.post(origin + f"/api/works/{work_id}/prepare", headers=headers, data={})
        self.assertTrue(response.ok, response.text())
        job_url = origin + "/api/runs/" + response.json()["id"]
        reviewed = False
        for _ in range(200):
            job = page.request.get(job_url).json()
            if job["status"] == "COMPLETED":
                return job["prepared_version_id"]
            if (job.get("gate") or {}).get("kind") == "metadata_review" and not reviewed:
                for field, value in (metadata or {}).items():
                    response = page.request.post(job_url + "/metadata", headers=headers,
                        data={"field": field, "value": value, "rationale": "Explicit synthetic reviewer input."})
                    self.assertTrue(response.ok, response.text())
                job = page.request.get(job_url).json()
                response = page.request.post(job_url + "/metadata/confirm", headers=headers,
                    data={"gate_id": job["gate"]["id"], "record_revision": job["gate"]["record_revision"]})
                self.assertTrue(response.ok, response.text())
                reviewed = True
            self.assertNotIn(job["status"], ("FAILED", "BLOCKED", "PAUSED"), job.get("error"))
            time.sleep(0.1)
        self.fail("Work preparation did not complete.")

    @unittest.skipUnless(os.environ.get("STUDIO_BROWSER") == "1", "Browser check: build frontend and set STUDIO_BROWSER=1.")
    def test_intake_requires_only_a_manuscript_and_defers_metadata_to_overview(self):
        from playwright.sync_api import expect

        def check(page, origin):
            page.goto(origin + "/#/works")
            expect(page.get_by_label("Language hint (optional)")).to_have_count(0)
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
            expect(page.locator(".author-form")).to_have_count(0)
            expect(page.get_by_role("heading", name="About this manuscript", exact=True)).to_have_count(0)
            expect(page.locator(".metadata button")).to_have_count(0)
            expect(page.get_by_text("Prepare this Work to review its metadata.")).to_be_visible()
            workflow = page.get_by_role("heading", name="Start a workflow", exact=True).locator("..")
            workflow.get_by_label("Workflow", exact=True).select_option("literary-translation-v1")
            expect(workflow.get_by_role("button", name="Start", exact=True)).to_be_disabled()
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
        from .test_web import Scripted, context, interior_design

        def design_with_saved_case(request):
            result = interior_design(request, include_openings=True)
            if context(request)["stage"] == "interior-design":
                path = Path(request.cwd) / result["state_path"]
                proposal = json.loads(path.read_bytes())
                proposal["design_system"]["chapter_openings"]["number_template"] = "Chapter {number}"
                proposal["design_system"]["part_openings"]["heading"].update(
                    layout="separated", number_format="arabic", number_case="upper",
                    number_template="Part the {number}")
                path.write_bytes((json.dumps(proposal, ensure_ascii=False) + "\n").encode("utf-8"))
            return result

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
            expect(start.get_by_label("Workflow", exact=True).locator('option[value="manuscript-formatting-v1"]')).to_have_count(0)
            expect(start.get_by_role("button", name="Start", exact=True)).to_be_disabled()
            version_id = self.prepared_input(page, origin, work["id"])
            created = page.request.post(origin + "/api/runs", headers=headers,
                                        data={"template_id": "literary-editing-v1", "work_id": work["id"],
                                              "work_version_id": version_id})
            self.assertTrue(created.ok, created.text())
            run = created.json()
            run_url = origin + "/api/runs/" + run["id"]
            for _ in range(100):
                run = page.request.get(run_url).json()
                if run.get("gate"):
                    break
                time.sleep(0.1)
            self.assertEqual(run["gate"]["kind"], "pass_choice")
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
            expect(page.get_by_role("button", name="Save specification changes")).to_be_disabled()
            chapters = page.locator("summary").filter(has_text=re.compile("^Chapter openings$")).locator("..")
            parts = page.locator("summary").filter(has_text=re.compile("^Part openings$")).locator("..")
            expect(chapters).to_be_visible()
            expect(parts).to_be_visible()
            saved_format = parts.get_by_label("Number format", exact=True)
            expect(saved_format).to_have_value("arabic:upper")
            expect(saved_format.locator("option:checked")).to_have_text("Saved setting: PART THE 4 (Arabic / upper label)")
            expect(page.get_by_role("button", name="Save specification changes")).to_be_disabled()
            chapter_styles = chapters.locator("summary").filter(has_text=re.compile("^Chapter styles$")).locator("..")
            chapter_styles.locator("summary").first.click()
            heading = chapter_styles.locator("summary").filter(has_text=re.compile("^chapter heading$")).locator("..")
            expect(heading).to_have_count(1)
            expect(page.locator("summary").filter(has_text=re.compile("^chapter heading$"))).to_have_count(1)
            heading.locator("summary").first.click()
            heading.locator("summary").filter(has_text=re.compile("^font$")).click()
            heading.get_by_label("size pt preset", exact=True).select_option("14")
            expect(parts.locator("summary").filter(has_text=re.compile("^Part styles$"))).to_have_count(1)
            expect(page.get_by_label("chapter start", exact=True)).to_have_count(0)
            expect(chapters.get_by_label("layout", exact=True)).to_have_value('"preserve-source"')
            expect(page.get_by_label("number case", exact=True)).to_have_count(0)
            navigation = page.locator("summary").filter(has_text=re.compile("^navigation$")).locator("..")
            navigation.locator("summary").first.click()
            navigation.get_by_label("Include table of contents", exact=True).check()
            expect(navigation.get_by_label("TOC depth", exact=True)).to_have_value("1")
            expect(navigation.get_by_label("TOC heading", exact=True)).to_have_value("Contents")
            expect(navigation.get_by_label("TOC heading style", exact=True)).to_have_value("toc-heading")
            navigation.get_by_label("TOC heading", exact=True).fill("Table of Contents")
            toc_styles = navigation.locator("summary").filter(has_text=re.compile("^TOC styles$")).locator("..")
            toc_styles.locator("summary").first.click()
            toc_heading = toc_styles.locator("summary").filter(has_text=re.compile("^toc heading$")).locator("..")
            expect(toc_heading).to_have_count(1)
            toc_heading.locator("summary").first.click()
            toc_heading.locator("summary").filter(has_text=re.compile("^font$")).click()
            toc_heading.get_by_label("size pt preset", exact=True).select_option("24")
            navigation.get_by_label("TOC depth", exact=True).select_option("2")
            navigation.get_by_label("TOC entry style", exact=True).select_option("chapter-heading")
            toc_target = current["gate"]["design_review"]["proposal"]["basis"]["preparation"]["units"][1]["chapter_id"]
            navigation.get_by_label("TOC location", exact=True).select_option(toc_target)
            navigation.get_by_label("Include table of contents", exact=True).uncheck()
            expect(navigation.get_by_label("TOC depth", exact=True)).to_have_count(0)
            navigation.get_by_label("Include table of contents", exact=True).check()
            navigation.get_by_label("TOC depth", exact=True).select_option("2")
            expect(chapters.get_by_label("Number format", exact=True)).to_have_count(0)
            chapters.get_by_label("layout", exact=True).select_option('"separated"')
            number_format = chapters.get_by_label("Number format", exact=True)
            expect(number_format).to_have_value("source")
            expect(chapters.get_by_label("Number label preset", exact=True)).to_have_count(0)
            self.assertEqual(number_format.locator("option").count(), 10)
            for option in ("arabic:title", "roman-upper:title", "roman-lower:title",
                           "words:lower", "words:title", "words:upper",
                           "ordinal-words:lower", "ordinal-words:title", "ordinal-words:upper"):
                number_format.select_option(option)
                expect(chapters.get_by_label("Number label preset", exact=True)).to_have_count(0)
            number_format.select_option("source")
            expect(chapters.get_by_label("Number label preset", exact=True)).to_have_count(0)
            number_format.select_option("roman-lower:title")
            expect(number_format.locator('option[value="arabic:title"]')).to_have_text("Chapter 4 (Arabic)")
            expect(number_format.locator('option[value="roman-upper:title"]')).to_have_text("Chapter IV (Roman uppercase)")
            expect(number_format.locator('option[value="words:upper"]')).to_have_text("CHAPTER FOUR (Words uppercase)")
            chapters.get_by_role("checkbox", name="Number only", exact=True).check()
            expect(chapters.get_by_role("checkbox", name="Number only", exact=True)).to_have_count(1)
            expect(chapters.get_by_label("layout", exact=True)).to_have_value('"separated"')
            expect(number_format).to_have_value("roman-lower:title")
            expect(number_format.locator('option[value="roman-upper:title"]')).to_have_text("IV (Roman uppercase)")
            expect(chapters.get_by_label("Number label preset", exact=True)).to_have_count(0)
            chapters.get_by_role("checkbox", name="Number only", exact=True).uncheck()
            expect(number_format.locator('option[value="roman-upper:title"]')).to_have_text("Chapter IV (Roman uppercase)")
            expect(chapters.get_by_label("number template", exact=True)).to_have_count(0)
            chapters.get_by_label("Opening ornament preset", exact=True).select_option('"* * *"')
            chapters.get_by_label("ornament position", exact=True).select_option('"between"')
            chapters.get_by_label("layout", exact=True).select_option('"combined"')
            expect(chapters.get_by_label("ornament position", exact=True)).to_have_value('"below"')
            chapters.get_by_label("Opening offset (mm) preset", exact=True).select_option("20")
            expect(chapters.get_by_label("combined style", exact=True)).to_have_value("chapter-heading")
            parts.get_by_label("placement", exact=True).select_option('"with-first-chapter"')
            parts.get_by_label("layout", exact=True).select_option('"separated"')
            parts.get_by_label("Number format", exact=True).select_option("ordinal-words:upper")
            expect(parts.get_by_label("Number format", exact=True).locator('option:checked')).to_have_text("PART THE FOURTH (Ordinal uppercase)")
            expect(parts.get_by_label("Number format", exact=True).locator('option[value="roman-upper:title"]')).to_have_text("Part the IV (Roman uppercase)")
            expect(parts.get_by_label("Number label preset", exact=True)).to_have_count(0)
            parts.get_by_role("checkbox", name="Number only", exact=True).check()
            parts.get_by_role("checkbox", name="Number only", exact=True).uncheck()
            expect(parts.get_by_label("Number format", exact=True).locator('option:checked')).to_have_text("PART THE FOURTH (Ordinal uppercase)")
            parts.get_by_role("checkbox", name="Number only", exact=True).check()
            expect(parts.get_by_label("Number format", exact=True).locator('option:checked')).to_have_text("FOURTH (Ordinal uppercase)")
            expect(page.get_by_label("number case", exact=True)).to_have_count(0)
            expect(page.get_by_text("Approval stops before production.", exact=False)).to_have_count(0)
            targets = page.locator("summary").filter(has_text=re.compile(r"^production targets \(1\)$")).locator("..")
            targets.locator("summary").first.click()
            edition = targets.locator("summary").filter(has_text=re.compile("^Output 1$")).locator("..")
            edition.locator("summary").first.click()
            paper = edition.get_by_label("Paper stock preset", exact=True)
            self.assertCountEqual(paper.locator("option").all_text_contents(),
                                  ["Not selected", "White", "Groundwood", "Cream", "Custom value..."])
            paper.select_option("custom")
            edition.get_by_label("Custom Paper stock", exact=True).fill("Author-specified stock")
            paper.select_option("null")
            expect(paper).to_have_value("null")
            paper.select_option('"creme"')
            trim = page.get_by_label("Trim size preset", exact=True)
            expect(trim).to_have_count(1)
            expect(edition.get_by_label("Trim size preset", exact=True)).to_have_count(0)
            trim.first.select_option("5.5x8.5")
            expect(page.get_by_text("Current trim: 5.5 x 8.5 in", exact=False).first).to_be_visible()
            trim.first.select_option("custom")
            page.get_by_label("Custom trim width mm", exact=True).first.fill("137")
            page.get_by_label("Custom trim height mm", exact=True).first.fill("216")
            expect(page.get_by_text("Current trim: 5.394 x 8.504 in", exact=False).first).to_be_visible()
            trim.first.select_option("5.5x8.5")
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
            furniture = page.locator("summary").filter(has_text=re.compile("^furniture$")).locator("..")
            furniture.locator("summary").first.click()
            defaults = furniture.locator("summary").filter(has_text=re.compile("^default section$")).locator("..")
            defaults.locator("summary").first.click()
            defaults.get_by_label("header distance mm preset", exact=True).select_option("custom")
            defaults.get_by_label("Custom header distance mm", exact=True).fill("11")
            expect(defaults.get_by_label("header distance mm in inches", exact=True)).to_have_text("(0.433 in)")

            def part(group, variant):
                collection = defaults.locator("summary").filter(has_text=re.compile("^" + group + "$")).locator("..")
                if not collection.evaluate("(el) => el.open"):
                    collection.locator("summary").first.click()
                item = collection.locator("summary").filter(has_text=re.compile("^" + variant + "$")).locator("..")
                item.locator("summary").first.click()
                item.locator("summary").filter(has_text=re.compile(r"^paragraphs \(\d+\)$")).click()
                return item

            header = part("headers", "default")
            header.get_by_label("Header content", exact=True).select_option("chapter-name")
            expect(header.get_by_label("Header content", exact=True)).to_have_value("chapter-name")
            header.get_by_label("Header content", exact=True).select_option("book-title")
            header.get_by_label("Header content", exact=True).select_option("custom")
            header.locator("summary").filter(has_text=re.compile("^1$")).click()
            header.get_by_label("Custom template", exact=True).fill("Proof {work_title}")
            header.get_by_role("combobox", name="Style", exact=True).select_option("running-head")
            footer = part("footers", "default")
            footer.get_by_label("Footer content", exact=True).select_option("page-x-of-y")
            expect(footer.get_by_label("Footer content", exact=True)).to_have_value("page-x-of-y")
            footer.get_by_label("Footer content", exact=True).select_option("custom")
            footer.locator("summary").filter(has_text=re.compile("^1$")).click()
            footer.get_by_label("Custom template", exact=True).fill("Page {page} / {page_count}")
            blank = part("footers", "first")
            blank.get_by_role("button", name="Add footer paragraph", exact=True).click()
            expect(blank.get_by_role("button", name="Remove paragraph", exact=True)).to_have_count(1)
            blank.get_by_role("button", name="Remove paragraph", exact=True).click()
            blank.get_by_label("Footer content", exact=True).select_option("page-number")
            blank.get_by_label("Footer content", exact=True).select_option("none")
            expect(blank.get_by_label("Footer content", exact=True)).to_have_value("none")
            overrides = furniture.locator("summary").filter(has_text=re.compile(r"^section overrides \(\d+\)$")).locator("..")
            overrides.locator("summary").first.click()
            overrides.get_by_role("button", name="Add section override", exact=True).click()
            expect(overrides.get_by_role("button", name="Remove section override", exact=True)).to_have_count(2)
            overrides.get_by_role("button", name="Remove section override", exact=True).last.click()
            page.locator("summary").filter(has_text=re.compile(r"^Text styles \(3\)$")).click()
            body = page.locator("summary").filter(has_text=re.compile("^body$")).locator("..")
            body.locator("summary").first.click()
            body.locator("summary").filter(has_text=re.compile("^font$")).click()
            body.get_by_label("family preset", exact=True).select_option('"Garamond"')
            body.get_by_label("size pt preset", exact=True).select_option("12")
            body.get_by_label("Line spacing preset", exact=True).select_option(label="1.3 x lines")
            gutter = page.get_by_label("gutter mm preset", exact=True)
            expect(gutter).to_have_value("3")
            expect(page.get_by_label("gutter mm in inches", exact=True)).to_have_text("(0.118 in)")
            gutter.select_option("custom")
            page.get_by_label("Custom gutter mm", exact=True).fill("4.5")
            expect(page.get_by_label("gutter mm in inches", exact=True)).to_have_text("(0.177 in)")
            gutter.select_option("5")
            expect(page.get_by_label("gutter mm in inches", exact=True)).to_have_text("(0.197 in)")
            page.get_by_label("Section starts", exact=True).select_option("recto")
            expect(navigation.get_by_label("TOC start", exact=True)).to_have_value("recto")
            expect(page.get_by_role("button", name="Generate draft DOCX")).to_be_disabled()
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
            self.assertEqual(next(style for style in current["gate"]["design_review"]["proposal"]["design_system"]["styles"]
                                  if style["id"] == "chapter-heading")["font"]["size_pt"], 14)
            self.assertEqual(current["gate"]["design_review"]["proposal"]["revision"], 2)
            self.assertEqual(current["gate"]["design_review"]["proposal"]["opening_structure"][0]["number"], None)
            opening_design = current["gate"]["design_review"]["proposal"]["design_system"]
            self.assertEqual(opening_design["page"]["section_start"], "recto")
            self.assertEqual(opening_design["page"]["blank_policy"], "allow-declared-recto-blanks")
            self.assertEqual(opening_design["chapter_openings"]["start"], "recto")
            self.assertEqual(opening_design["part_openings"]["heading"]["start"], "recto")
            self.assertEqual(opening_design["navigation"]["toc_start"], "recto")
            self.assertEqual(opening_design["navigation"]["include_toc"], True)
            self.assertEqual(opening_design["navigation"]["toc_depth"], 2)
            self.assertEqual(opening_design["navigation"]["toc_style_id"], "chapter-heading")
            self.assertEqual(opening_design["navigation"]["toc_before_chapter_id"], toc_target)
            self.assertEqual(opening_design["navigation"]["toc_heading"], "Table of Contents")
            self.assertEqual(opening_design["navigation"]["toc_heading_style_id"], "toc-heading")
            self.assertEqual(next(s for s in opening_design["styles"] if s["id"] == "toc-heading")["font"]["size_pt"], 24)
            self.assertEqual(opening_design["chapter_openings"]["layout"], "combined")
            self.assertEqual(opening_design["chapter_openings"]["number_format"], "roman-lower")
            self.assertEqual(opening_design["chapter_openings"]["number_case"], "title")
            self.assertEqual(opening_design["chapter_openings"]["number_template"], "Chapter {number}")
            self.assertEqual(opening_design["chapter_openings"]["offset_mm"], 20)
            self.assertEqual(opening_design["chapter_openings"]["ornament_text"], "* * *")
            self.assertEqual(opening_design["part_openings"]["placement"], "with-first-chapter")
            self.assertEqual(opening_design["part_openings"]["heading"]["number_format"], "ordinal-words")
            self.assertEqual(opening_design["part_openings"]["heading"]["number_case"], "upper")
            self.assertEqual(opening_design["part_openings"]["heading"]["number_template"], "{number}")
            expect(parts.get_by_role("checkbox", name="Number only", exact=True)).to_be_checked()
            expect(chapters.get_by_role("checkbox", name="Number only", exact=True)).not_to_be_checked()
            expect(number_format).to_have_value("roman-lower:title")
            expect(parts.get_by_label("Number format", exact=True)).to_have_value("ordinal-words:upper")
            brief = current["gate"]["design_review"]["proposal"]["edition_brief"]
            design = current["gate"]["design_review"]["proposal"]["design_system"]
            self.assertEqual(brief["production_targets"][0]["paper"], "creme")
            self.assertEqual(brief["production_targets"][0]["trim_mm"], {"width": 139.7, "height": 215.9})
            self.assertEqual(design["page"]["trim_mm"], brief["production_targets"][0]["trim_mm"])
            self.assertEqual(design["styles"][0]["font"]["line_spacing"], {"mode": "multiple", "value": 1.3})
            expect(paper).to_have_value('"creme"')
            expect(trim.first).to_have_value("5.5x8.5")
            saved_furniture = current["gate"]["design_review"]["proposal"]["design_system"]["furniture"]
            self.assertEqual(saved_furniture["default_section"]["header_distance_mm"], 11)
            self.assertEqual(saved_furniture["default_section"]["headers"]["default"]["paragraphs"][0]["content"],
                             {"preset": "custom", "template": "Proof {work_title}"})
            self.assertEqual(saved_furniture["default_section"]["footers"]["default"]["paragraphs"][0]["content"],
                             {"preset": "custom", "template": "Page {page} / {page_count}"})
            self.assertEqual(saved_furniture["default_section"]["footers"]["first"],
                             {"link_to_previous": False, "paragraphs": []})
            self.assertEqual(len(saved_furniture["section_overrides"]), 1)
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
                page.get_by_role("button", name="Generate draft DOCX").click()
            self.assertTrue(approved.value.ok, approved.value.text())
            expect(page.get_by_role("heading", name="Approve design and DOCX", exact=True)).to_be_visible()
            current = page.request.get(run_url).json()
            # The run consumes Work preparation/analysis; only proposal authoring calls an agent.
            self.assertEqual((current["status"], current["finalized"], current["attempts"]), ("WAITING_FOR_ACCEPTANCE", False, 1))
            self.assertIsNone(current.get("gate"))
            self.assertEqual(current["production"]["summary"]["toc"]["depth"], 2)
            expect(page.get_by_text("TOC field: update in Word", exact=True)).to_be_visible()
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 391)
            expect(page.get_by_label("I authorize this exact editable-DOCX generation plan.")).to_have_count(0)
            expect(page.get_by_role("button", name="Generate draft DOCX", exact=True)).to_have_count(0)
            expect(page.get_by_role("heading", name="Approve design and DOCX", exact=True)).to_be_visible()
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 391)
            with page.expect_download() as downloaded:
                page.get_by_role("link", name="Download DOCX candidate", exact=True).click()
            self.assertRegex(downloaded.value.suggested_filename, r"^Story-v001-candidate-[0-9a-f]{8}\.docx$")
            current = page.request.get(run_url).json()
            self.assertEqual(digest(Path(downloaded.value.path()).read_bytes()), current["production"]["docx"]["sha256"])
            with zipfile.ZipFile(downloaded.value.path()) as package:
                self.assertIn(b'TOC \\o "1-2"', package.read("word/document.xml"))
                self.assertIn(b"bf_toc_scope", package.read("word/document.xml"))
                self.assertIn(b"Table of Contents", package.read("word/document.xml"))
                self.assertIn(b"BF.toc-heading", package.read("word/document.xml"))
                self.assertIn(b"Update this field in Word", package.read("word/document.xml"))
                xml = etree.fromstring(package.read("word/document.xml"))
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                sections = xml.xpath("//w:sectPr", namespaces=ns)
                self.assertGreaterEqual(len(sections), 3)
                self.assertTrue(all(section.find("w:type", ns).get("{%s}val" % ns["w"]) == "oddPage" for section in sections))
            expect(page.get_by_text("No PDF, rendered-page review", exact=False).first).to_be_visible()
            old_candidate = current
            with page.expect_response(lambda r: r.url == run_url + "/interior-design/reopen") as reopened:
                page.get_by_role("button", name="Revise design", exact=True).click()
            self.assertTrue(reopened.value.ok, reopened.value.text())
            expect(page.get_by_role("heading", name="Review formatting specification")).to_be_visible()
            navigation.locator("summary").first.click()
            expect(navigation.get_by_label("TOC heading", exact=True)).to_have_value("Table of Contents")
            expect(navigation.get_by_label("TOC heading style", exact=True)).to_have_value("toc-heading")
            expect(gutter).to_have_value("5")
            gutter.select_option("6.35")
            with page.expect_response(lambda r: r.url == run_url + "/interior-design") as resaved:
                page.get_by_role("button", name="Save specification changes").click()
            self.assertTrue(resaved.value.ok, resaved.value.text())
            expect(page.get_by_text(re.compile("Specification revision 3"))).to_be_visible()
            revised = page.request.get(run_url).json()
            for question in revised["gate"]["design_review"]["proposal"]["questions"]:
                if question["blocking"]:
                    page.get_by_label(question["question"], exact=False).fill("Keep the proposed new-page openings.")
            page.get_by_role("button", name="Generate draft DOCX", exact=True).click()
            expect(page.get_by_role("heading", name="Approve design and DOCX", exact=True)).to_be_visible()
            current = page.request.get(run_url).json()
            self.assertNotEqual(current["acceptance"]["acceptance_id"], old_candidate["acceptance"]["acceptance_id"])
            self.assertNotEqual(current["production"]["id"], old_candidate["production"]["id"])
            self.assertNotEqual(current["production"]["docx"]["sha256"], old_candidate["production"]["docx"]["sha256"])
            self.assertEqual(current["attempts"], old_candidate["attempts"])  # Settings-only regeneration uses no agent.
            if evidence:
                page.screenshot(path=str(Path(evidence) / "docx-candidate-mobile.png"), full_page=True)
            page.set_viewport_size({"width": 1280, "height": 900})
            if evidence:
                page.screenshot(path=str(Path(evidence) / "docx-candidate-desktop.png"), full_page=True)
            page.get_by_label("I inspected this DOCX and approve its design; this finalizes the run.").check()
            with page.expect_response(lambda r: r.url == run_url + "/accept") as accepted:
                page.get_by_role("button", name="Approve edition and finish", exact=True).click()
            self.assertTrue(accepted.value.ok, accepted.value.text())
            expect(page.get_by_role("link", name="Download accepted DOCX", exact=True)).to_be_visible()
            page.goto(origin + "/#/works/" + work["id"])
            expect(page.get_by_role("heading", name="Story", exact=True)).to_be_visible()
            page.get_by_role("link", name="Review metadata", exact=True).click()
            expect(page.locator(".metadata tr").filter(
                has=page.locator("th").filter(has_text=re.compile("^Title$")))).to_contain_text("Story")
            expect(page.locator(".metadata tr").filter(
                has=page.locator("th").filter(has_text=re.compile("^Manuscript language$")))).to_contain_text("zh")
            expect(page.get_by_role("heading", name="Detected or measured", exact=True)).to_be_visible()
            page.goto(origin + "/#/works/" + work["id"])
            with page.expect_download() as published:
                page.get_by_role("link", name="literary-editing/v001/document.docx", exact=True).click()
            self.assertEqual(published.value.suggested_filename, "Story-v001.docx")
            self.assertEqual(digest(Path(published.value.path()).read_bytes()), current["production"]["docx"]["sha256"])
            self.assertEqual(errors, [])
            self.assertEqual(server_errors, [])

        with tempfile.TemporaryDirectory() as temporary:
            self.run_in_browser({}, Path(temporary) / "server",
                                lambda: Scripted(design_with_saved_case), check=check)

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
                    "unfinished_run": None, "metadata": None, "versions": [
                        {"version_id": "wv-ready", "status": "ready", "kind": "original", "language": "en",
                         "analysis_status": "provisional", "documents": []}]}

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
            form = page.get_by_role("heading", name="Start a workflow", exact=True).locator("..")
            form.get_by_label("Prepared version", exact=True).select_option("wv-ready")
            workflow = form.get_by_label("Workflow", exact=True)
            workflow.select_option("literary-editing-v1")
            model = form.get_by_role("combobox", name="Model", exact=True)
            start = page.get_by_role("button", name="Start", exact=True)
            expect(model).to_have_value("")
            expect(model.locator("option")).to_have_count(3)
            expect(start).to_be_disabled()
            model.select_option("editing")
            start.click()
            expect(page.get_by_role("alert")).to_contain_text("Fixture stops")
            self.assertEqual(submitted[-1], {"template_id": "literary-editing-v1",
                                           "work_id": "model-work", "work_version_id": "wv-ready", "model": "editing"})
            workflow.select_option("literary-translation-v1")
            expect(model).to_have_value("translation")
            model.select_option("shared")
            workflow.select_option("literary-editing-v1")
            expect(model).to_have_value("")
            expect(start).to_be_disabled()

            configured = False
            page.reload()
            form.get_by_label("Prepared version", exact=True).select_option("wv-ready")
            form.get_by_label("Workflow", exact=True).select_option("literary-editing-v1")
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
                    body = [{"id": "model-work", "title": "Story", "manuscript_language": "zh",
                             "versions": [{"version_id": "wv-ready", "status": "ready", "kind": "original", "language": "zh"}]}]
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
            page.get_by_label("Prepared version", exact=True).select_option("wv-ready")
            page.get_by_role("button", name="Create and start", exact=True).click()
            expect(page.get_by_role("alert")).to_contain_text("Fixture stops")
            self.assertEqual(submitted, [{"template_id": "literary-translation-v1",
                                         "work_id": "model-work", "work_version_id": "wv-ready", "model": "two"}])
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
                    "viewer_target": {"kind": "chapter", "chapter_id": chapter},
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
                elif path == prefix + "/approved-sheets":
                    body = []
                elif path == prefix + "/chapters":
                    body = {"prepared": True, "stages": ["translate"], "whole_book": {},
                            "overview": {"title": "Test work", "source_unit_id": None, "outputs": {}}, "chapters": [
                        {"chapter_id": name, "order": i + 1, "display_number": i + 1, "title": name, "role": "chapter",
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
                "viewer_target": {"kind": "overview"},
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
                elif path == prefix + "/approved-sheets":
                    body = []
                elif path == prefix + "/chapters":
                    body = {"prepared": True, "stages": ["developmental"], "whole_book": {"developmental": "in_progress"},
                            "overview": {"title": "Test work", "source_unit_id": None, "outputs": {}},
                            "chapters": [{"chapter_id": "one", "order": 1, "display_number": 1, "title": "One", "role": "chapter",
                                          "outputs": {"developmental": {"status": "completed", "ready": True}}}]}
                elif path == prefix + "/overview":
                    body = {"work_id": "test-work", "title": "Test work", "source_unit_id": None,
                            "prepared": True, "metadata": None, "metadata_fields": [], "source": None}
                elif path == prefix + "/chapters/one":
                    body = {"chapter": {"chapter_id": "one", "order": 1, "title": "One", "role": "chapter"},
                            "prepared_text": "Chapter text.", "outputs": [], "reviews": [], "passage_map": None}
                else:
                    self.fail(f"Unexpected browser request: {path}")
                route.fulfill(json=body)

            page.route("**/api/**", serve)
            follows = "(panel, before) => !!(before.compareDocumentPosition(panel) & Node.DOCUMENT_POSITION_FOLLOWING)"
            for chapter, before in (("/one", ".columns"), ("", ".overview-section")):
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
            expect(page.locator(".facts").first).to_contain_text("1/3 manuscript units")
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
            expect(page.locator(".facts").first).to_contain_text("2/3 manuscript units")
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

    @unittest.skipUnless(os.environ.get("STUDIO_BROWSER") == "1", "Browser check: build frontend and set STUDIO_BROWSER=1.")
    def test_overview_is_shared_but_workflow_specific(self):
        """Real API/engine: overview navigation is distinct, while workflows own their reading/review layouts."""
        import base64
        import time
        from playwright.sync_api import expect
        from .test_web import Scripted, translate

        def check(page, origin):
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            headers = {"Origin": origin}
            for workflow, panes in (("literary-translation", 2), ("literary-editing", 1)):
                with self.subTest(workflow=workflow):
                    work = page.request.post(origin + "/api/works", headers=headers, data={
                        "upload": {"name": "synthetic.md", "data": base64.b64encode(
                            "# 故事\n\n他回来了。\n".encode()).decode()},
                        "manuscript_language": "zh",
                    }).json()
                    version_id = self.prepared_input(page, origin, work["id"], metadata={
                        "/title": "Renamed " + workflow,
                        "/contributors": [{"id": "a-writer", "name": "A. Writer", "roles": ["author"]}],
                    })
                    run = page.request.post(origin + "/api/runs", headers=headers, data={
                        "work_id": work["id"], "template_id": workflow + "-v1", "work_version_id": version_id,
                    }).json()
                    run_url = origin + "/api/runs/" + run["id"]
                    for _ in range(100):
                        run = page.request.get(run_url).json()
                        if run.get("gate"):
                            break
                        time.sleep(0.1)
                    self.assertNotEqual(run["gate"]["kind"], "metadata_review")
                    overview_url = f"{origin}/#/runs/{run['id']}/overview"
                    page.goto(overview_url)
                    expect(page.get_by_role("heading", name="Renamed " + workflow, exact=True)).to_be_visible()
                    expect(page.get_by_role("region", name="Work metadata")).to_be_visible()
                    expect(page.get_by_role("heading", name="Translation brief", exact=True)).to_have_count(
                        1 if workflow == "literary-translation" else 0)
                    expect(page.locator(f".columns.panes-{panes}")).to_be_visible()
                    navigation = page.get_by_role("navigation", name="Manuscript navigation")
                    expect(navigation.locator(".overview-entry")).to_be_visible()
                    expect(navigation.get_by_text("Overview", exact=True)).to_be_visible()
                    expect(navigation.locator(".overview-entry").get_by_text(
                        "awaiting your review: metadata", exact=True)).to_have_count(0)
                    expect(navigation.locator("ol.chapters li")).to_have_count(1)
                    expect(navigation.locator("ol.chapters li")).to_contain_text("1.")
                    self.assertEqual(navigation.locator("ol .overview-entry").count(), 0)
                    navigation.locator("ol.chapters a").first.click()
                    expect(page).to_have_url(re.compile(r"/chapters/story$"))
                    expect(page.locator(".overview-section")).to_have_count(0)
                    navigation.locator(".overview-entry a").click()
                    expect(page).to_have_url(overview_url)
                    original = page.request.get(run_url + "/overview").json()
                    title_row = page.locator(".metadata tr").filter(
                        has=page.locator("th").filter(has_text=re.compile("^Title$")))
                    expect(title_row).to_contain_text("Renamed " + workflow)
                    expect(title_row.get_by_role("button")).to_have_count(0)
                    contributors = page.locator(".metadata tr").filter(
                        has=page.locator("th").filter(has_text=re.compile("^Contributors$")))
                    page.set_viewport_size({"width": 390, "height": 844})
                    self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 391)
                    page.set_viewport_size({"width": 1280, "height": 900})
                    expect(contributors).to_contain_text("A. Writer (author)")
                    expect(navigation.locator(".overview-entry a")).to_have_attribute("href", re.compile(r"/overview$"))
                    current = page.request.get(run_url + "/overview").json()
                    self.assertEqual(current["source"]["prepared_text"], original["source"]["prepared_text"])
                    self.assertEqual(current["source_unit_id"], original["source_unit_id"])
                    # Whole-book findings resolve front-matter unit links to the overview.
                    page.goto(f"{origin}/#/runs/{run['id']}/chapters/{current['source_unit_id']}")
                    expect(page).to_have_url(overview_url)
                    expect(page.get_by_role("region", name="Work metadata")).to_be_visible()
                    evidence = os.environ.get("STUDIO_EVIDENCE_DIR")
                    if evidence:
                        page.screenshot(path=str(Path(evidence) / f"{workflow}-overview-desktop.png"), full_page=True)
                    page.set_viewport_size({"width": 390, "height": 844})
                    self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
                    expect(navigation.locator(".overview-entry")).to_be_visible()
                    if evidence:
                        page.screenshot(path=str(Path(evidence) / f"{workflow}-overview-mobile.png"), full_page=True)
                    page.set_viewport_size({"width": 1280, "height": 900})
                    # Both workflows receive the selected Work reading immediately, with no analysis gate.
                    for _ in range(100):
                        ready = page.request.get(run_url + "/overview").json()
                        if ready.get("analysis"):
                            break
                        time.sleep(0.1)
                    self.assertIsNotNone(ready.get("analysis"))
                    self.assertEqual(ready["analysis"]["approval_status"], "provisional")
                    self.assertEqual(len(ready["analysis"]["documents"]), 5)
                    analysis = page.get_by_role("region", name="Manuscript analysis")
                    expect(analysis.get_by_text("Shared source reading", exact=False)).to_be_visible()
                    subjects = analysis.get_by_role("region", name="Subject proposals")
                    expect(subjects).to_be_visible()
                    for title in ("BISAC Subjects", "Thema Subjects", "Keywords", "Place Subjects"):
                        subjects.locator("summary").filter(has_text=re.compile("^" + title)).click()
                    expect(subjects.get_by_text("Fiction / General", exact=True)).to_be_visible()
                    expect(subjects.get_by_text("Fiction: general and literary", exact=True)).to_be_visible()
                    expect(subjects.get_by_text("Code unresolved", exact=True)).to_have_count(2)
                    expect(subjects.get_by_text("returning home", exact=True)).to_be_visible()
                    expect(subjects.get_by_text("No specific geographic setting established", exact=False)).to_be_visible()
                    subjects.locator("summary").filter(has_text="Source evidence").first.click()
                    expect(subjects.locator("blockquote").first).to_be_visible()
                    expect(subjects.locator("button, input, textarea")).to_have_count(0)
                    self.assertEqual(page.request.get(run_url + "/overview").json()["metadata"]["metadata"]["keywords"],
                                     original["metadata"]["metadata"]["keywords"])
                    expect(analysis.get_by_role("tab")).to_have_count(5)
                    expect(analysis.locator("input, textarea")).to_have_count(0)
                    analysis.get_by_role("tab", name="Synopsis", exact=True).click()
                    expect(analysis.get_by_role("tabpanel")).to_contain_text("Synthetic synopsis")
                    # A workflow shows its pinned metadata, not a second mutable intake editor.
                    audience = page.locator(".metadata tr").filter(
                        has=page.locator("th").filter(has_text=re.compile("^Audience$")))
                    expect(audience.get_by_role("button")).to_have_count(0)
                    expect(page.get_by_text("Metadata is pinned to the selected Work version.", exact=False)).to_be_visible()
                    page.set_viewport_size({"width": 390, "height": 844})
                    self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
                    if evidence:
                        page.screenshot(path=str(Path(evidence) / f"{workflow}-analysis-mobile.png"), full_page=True)
                    page.set_viewport_size({"width": 1280, "height": 900})
            self.assertEqual(errors, [])

        with tempfile.TemporaryDirectory() as temporary:
            self.run_in_browser({}, Path(temporary) / "server", lambda: Scripted(translate), check=check)

    @unittest.skipUnless(os.environ.get("STUDIO_BROWSER") == "1", "Browser check: build frontend and set STUDIO_BROWSER=1.")
    def test_approved_sheet_links_download_markdown_without_disturbing_current_review(self):
        import base64
        import time
        from playwright.sync_api import expect
        from .test_web import Scripted, translate

        def check(page, origin):
            headers = {"Origin": origin}
            work = page.request.post(origin + "/api/works", headers=headers, data={
                "upload": {"name": "reference.md", "data": base64.b64encode("# 故事\n\n他回来了。\n".encode()).decode()},
                "manuscript_language": "zh",
            }).json()
            version_id = self.prepared_input(page, origin, work["id"])
            run = page.request.post(origin + "/api/runs", headers=headers, data={
                "work_id": work["id"], "template_id": "literary-translation-v1", "work_version_id": version_id,
            }).json()
            run_url = origin + "/api/runs/" + run["id"]

            def waiting(kind):
                for _ in range(100):
                    current = page.request.get(run_url).json()
                    if current.get("gate", {}).get("kind") == kind and not current["worker"]["active"]:
                        return current
                    time.sleep(0.1)
                self.fail(f"Did not reach {kind}")

            run = waiting("brief_samples")
            response = page.request.post(run_url + "/reply", headers=headers, data={
                "gate_id": run["gate"]["id"], "text": "S1 choose A: Preserve the plain voice.",
            })
            self.assertTrue(response.ok, response.text())
            run = waiting("translation_brief")
            approved = page.request.get(run_url + "/approved-sheets").json()
            self.assertEqual(len(approved), 1)
            page.goto(f"{origin}/#/runs/{run['id']}/overview")
            active = page.locator(".panel.gate")
            expect(active).to_be_visible()
            draft = active.get_by_placeholder("General comment (optional)")
            draft.fill("Unsent feedback must stay in this review.")
            history = page.get_by_role("region", name="Approved sheets")
            link = history.get_by_role("link", name="Translation samples · revision 1")
            expect(link).to_have_attribute("download", "")
            self.assertIsNone(link.get_attribute("target"))
            requests = []
            page.on("request", lambda request: requests.append(request.method))
            url = page.url
            tabs = len(page.context.pages)
            with page.expect_download() as started:
                link.click()
            download = started.value
            self.assertTrue(download.suggested_filename.endswith(".md"))
            self.assertEqual(Path(download.path()).read_bytes(), b"S1: A / B\n")
            self.assertEqual(len(page.context.pages), tabs)
            expect(page).to_have_url(url)
            expect(draft).to_have_value("Unsent feedback must stay in this review.")
            self.assertFalse(any(method != "GET" for method in requests))
            unchanged = page.request.get(run_url).json()
            self.assertEqual(unchanged["gate"]["id"], run["gate"]["id"])

        with tempfile.TemporaryDirectory() as temporary:
            self.run_in_browser({}, Path(temporary) / "server", lambda: Scripted(translate), check=check)

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
