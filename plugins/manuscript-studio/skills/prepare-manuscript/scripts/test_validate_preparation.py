import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import validate_preparation as validator
import prepare_metadata as metadata

NOW = "2026-10-19T12:00:00Z"
WORKFLOWS = ("literary-editing", "literary-translation", "literary-agent-querying")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.sources = self.base / "originals"
        self.sources.mkdir()
        self.source = self.sources / "original.txt"
        self.source.write_text("# 第一章\n\n原文第一段。\n\n# 第二章\n\n原文第二段。\n", encoding="utf-8", newline="\n")
        self.root = self.base / "prepared-manuscripts/example-work"
        self.revision = self.root / "revisions/r0001"
        (self.revision / "chapters").mkdir(parents=True)
        chapters = []
        for number, text in enumerate(("# 第一章\n\n原文第一段。\n", "# 第二章\n\n原文第二段。\n"), 1):
            path = self.revision / f"chapters/{number:04d}.md"
            path.write_bytes(text.encode("utf-8"))
            chapters.append({
                "chapter_id": f"chapter-{number}", "order": number,
                "source_number": str(number), "title": f"Chapter {number}",
                "role": "front_matter" if number == 1 else "chapter", "file": f"chapters/{number:04d}.md",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "source_spans": [{"source_id": "original", "locator": f"Heading {number} to next heading or EOF"}],
                "status": "verified",
            })
        self.manifest = {
            "schema_version": 1, "work_id": "example-work", "revision": "r0001",
            "status": "verified", "created_at": NOW,
            "sources": [{
                "source_id": "original", "locator": str(self.source), "format": "text",
                "identity": {"kind": "sha256", "value": validator.digest(self.source)},
            }],
            "scope": {"kind": "whole_work", "chapter_ids": ["chapter-1", "chapter-2"]},
            "chapters": chapters, "assets": [],
            "extraction": {"tool": "test-fixture", "method": "Synthetic chapter fixture", "normalization_notes": []},
            "verification": {"performed_by": "test", "verified_at": NOW, "coverage_complete": True, "issues": []},
        }
        self.work = {
            "schema_version": 2, "work_id": "example-work", "record_revision": 1, "updated_at": NOW,
            "metadata": {"title": "Example work", "subtitle": None, "contributors": [], "original_language": None,
                         "manuscript_language": "zh", "work_type": "fiction", "form": None, "genres": [],
                         "audience": None, "keywords": [], "description": None,
                         "edition": {"label": None, "status": None},
                         "series": {"name": None, "position": None, "relationship": None}, "extent": None},
            "metadata_provenance": {},
            "discovery": {"location_kind": "directory", "location": str(self.sources),
                          "recursive": False, "selection_status": "confirmed", "notes": []},
            "preparation": {"status": "ready", "current_revision": "r0001", "blockers": []},
            "workflows": {name: {"status": "not_started", "basis_revision": None, "scope": None,
                                 "operation": None, "state_locator": None, "updated_at": None}
                          for name in WORKFLOWS},
        }
        self.save()

    def save(self):
        write_json(self.root / "work.json", self.work)
        write_json(self.revision / "manifest.json", self.manifest)

    def validate(self, **kwargs):
        self.save()
        return validator.validate(self.root / "work.json", **kwargs)

    def workflow(self, **changes):
        state = {
            "status": "in_progress", "basis_revision": "r0001",
            "scope": copy.deepcopy(self.manifest["scope"]),
            "operation": "chapter-translation", "state_locator": str(self.base / "translation-project"),
            "updated_at": NOW,
        }
        state.update(changes)
        self.work["workflows"]["literary-translation"] = state

    def test_verified_package_and_local_source_hashes_pass(self):
        result = self.validate(check_sources=True)
        self.assertEqual(result["chapters"], 2)
        self.assertTrue(result["local_sources_checked"])
        self.workflow()
        self.assertEqual(self.validate()["preparation_status"], "ready")

    def test_unknown_language_is_inferred_with_evidence_before_ready(self):
        blank = metadata.blank("example-work", None, location=str(self.source), actor="test")
        self.assertIsNone(blank["metadata"]["manuscript_language"])
        self.assertNotIn("/manuscript_language", blank["metadata_provenance"])
        self.work["metadata"]["manuscript_language"] = None
        with self.assertRaisesRegex(ValueError, "determined source language"):
            self.validate()
        self.work["preparation"]["status"] = "in_progress"
        self.save()
        metadata.update(self.root / "work.json", "enrich",
                        proposals=[self.proposal("/manuscript_language", "zh")], actor="prepare-manuscript")
        self.work = self.read_work()
        self.assertEqual(self.work["metadata"]["manuscript_language"], "zh")
        self.assertEqual(self.work["metadata_provenance"]["/manuscript_language"]["review_status"], "proposed")
        self.work["preparation"]["status"] = "ready"
        self.assertEqual(self.validate()["preparation_status"], "ready")

    def test_discovery_only_record_does_not_claim_readiness(self):
        self.work["preparation"] = {"status": "not_started", "current_revision": None, "blockers": []}
        self.work["discovery"]["selection_status"] = "unresolved"
        self.work["metadata"]["manuscript_language"] = None
        self.assertIsNone(self.validate()["current_revision"])
        self.work["preparation"]["status"] = "ready"
        with self.assertRaisesRegex(ValueError, "verified revision"):
            self.validate()

    def test_ready_requires_confirmed_selection_and_no_blockers(self):
        self.work["discovery"]["selection_status"] = "unresolved"
        with self.assertRaisesRegex(ValueError, "confirmed"):
            self.validate()
        self.work["discovery"]["selection_status"] = "confirmed"
        self.work["preparation"]["blockers"] = ["Missing source page"]
        with self.assertRaisesRegex(ValueError, "blockers"):
            self.validate()

    def test_incomplete_or_unverified_chapter_blocks_ready(self):
        for status in ("needs_review", "incomplete"):
            self.manifest["chapters"][0]["status"] = status
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, "Every chapter"):
                self.validate()

    def test_missing_coverage_and_blocking_issues_are_rejected(self):
        self.manifest["verification"]["coverage_complete"] = False
        with self.assertRaisesRegex(ValueError, "coverage"):
            self.validate()
        self.manifest["verification"]["coverage_complete"] = True
        self.manifest["verification"]["issues"] = [{"severity": "blocking", "description": "OCR unclear", "source_locator": "p. 1"}]
        with self.assertRaisesRegex(ValueError, "blocking"):
            self.validate()

    def test_chapter_content_change_is_detected(self):
        (self.revision / "chapters/0001.md").write_bytes(b"Edited prose\n")
        with self.assertRaisesRegex(ValueError, "hash"):
            self.validate()

    def test_raw_html_blocks_and_inline_tags_are_not_prepared_manuscript_content(self):
        for markup in ("<br />", "<BR>", "<p>Text</p>", "<!-- spacer -->",
                       "<!DOCTYPE html>", "<?instruction?>", "<![CDATA[text]]>",
                       "Prose <br/> continues.", "Prose <span>inline</span> text.",
                       "> <br />", "- Prose <em>inline</em>."):
            with self.subTest(markup=markup):
                path = self.revision / "chapters/0001.md"
                path.write_bytes(("# Title\n\n" + markup + "\n").encode("utf-8"))
                self.manifest["chapters"][0]["sha256"] = validator.digest(path)
                with self.assertRaisesRegex(ValueError, r"chapter-1 \(chapters/0001.md\):line 3: Raw HTML"):
                    self.validate()

    def test_blank_spacing_and_literal_angle_text_are_not_html(self):
        text = ("# Title\n\nFirst paragraph.\n\n\nSecond *paragraph*.\n\n"
                "Literal \\<br /> and \\<span>text\\</span> and \\<!-- comment -->.\n\n"
                "&lt;p&gt;, `<!-- literal -->`, and 2 < 3.\n\n"
                "<https://example.com> and <writer@example.com>.\n\n"
                "```html\n<span>literal code</span>\n```\n")
        path = self.revision / "chapters/0001.md"
        path.write_bytes(text.encode("utf-8"))
        self.manifest["chapters"][0]["sha256"] = validator.digest(path)
        before = path.read_bytes()
        self.validate(check_sources=True)
        self.assertEqual(path.read_bytes(), before)

    def test_original_change_is_detected_only_when_source_check_requested(self):
        self.source.write_bytes(b"Changed original\n")
        self.validate()
        with self.assertRaisesRegex(ValueError, "Original source changed"):
            self.validate(check_sources=True)

    def test_order_duplicate_ids_and_unknown_spans_are_rejected(self):
        original = copy.deepcopy(self.manifest)
        self.manifest["chapters"][1]["order"] = 1
        with self.assertRaisesRegex(ValueError, "orders"):
            self.validate()
        self.manifest = copy.deepcopy(original)
        self.manifest["chapters"][1]["chapter_id"] = "chapter-1"
        with self.assertRaisesRegex(ValueError, "unique"):
            self.validate()
        self.manifest = copy.deepcopy(original)
        self.manifest["chapters"][0]["source_spans"][0]["source_id"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unknown source"):
            self.validate()

    def test_nonstandard_paths_unlisted_files_and_line_endings_are_rejected(self):
        original = copy.deepcopy(self.manifest)
        self.manifest["chapters"][0]["file"] = "../outside.md"
        with self.assertRaises(ValueError):
            self.validate()
        self.manifest = original
        extra = self.revision / "chapters/extra.md"
        extra.write_bytes(b"Unexpected text\n")
        with self.assertRaisesRegex(ValueError, "unlisted"):
            self.validate()
        extra.unlink()
        (self.revision / "chapters/0001.md").write_bytes(b"Noncanonical\r\n")
        with self.assertRaisesRegex(ValueError, "LF"):
            self.validate()

    def test_scope_blocks_whole_work_completion_for_selected_chapters(self):
        self.manifest["scope"]["kind"] = "selected_chapters"
        self.workflow(status="completed", scope={"kind": "whole_work", "chapter_ids": ["chapter-1", "chapter-2"]})
        with self.assertRaisesRegex(ValueError, "partial preparation"):
            self.validate()
        self.work["workflows"]["literary-translation"]["scope"]["kind"] = "selected_chapters"
        self.validate()

    def test_invalid_workflow_state_and_stale_completed_basis_are_rejected(self):
        self.work["workflows"]["literary-editing"]["status"] = "approved"
        with self.assertRaises(ValueError):
            self.validate()
        self.work["workflows"]["literary-editing"]["status"] = "not_started"
        self.workflow(status="completed", basis_revision="r0002")
        with self.assertRaisesRegex(ValueError, "current ready"):
            self.validate()
        self.workflow(status="in_progress")
        self.work["preparation"]["status"] = "stale"
        with self.assertRaisesRegex(ValueError, "current ready"):
            self.validate()

    def test_stale_workflow_can_retain_older_source_basis(self):
        target = self.root / "revisions/r0002"
        shutil.copytree(self.revision, target)
        newer = copy.deepcopy(self.manifest)
        newer["revision"] = "r0002"
        write_json(target / "manifest.json", newer)
        self.work["preparation"]["current_revision"] = "r0002"
        self.workflow(status="stale")
        self.validate()

    def test_source_outside_location_and_unapproved_recursion_are_rejected(self):
        outside = self.base / "outside.txt"
        outside.write_bytes(self.source.read_bytes())
        self.manifest["sources"][0]["locator"] = str(outside)
        with self.assertRaisesRegex(ValueError, "outside"):
            self.validate()
        nested = self.sources / "nested"
        nested.mkdir()
        (nested / "book.txt").write_bytes(self.source.read_bytes())
        self.manifest["sources"][0]["locator"] = str(nested / "book.txt")
        with self.assertRaisesRegex(ValueError, "recursive"):
            self.validate()
        self.work["discovery"]["recursive"] = True
        self.validate(check_sources=True)

    def test_assets_are_bound_and_cannot_escape_package(self):
        assets = self.revision / "assets"
        assets.mkdir()
        figure = assets / "figure.png"
        figure.write_bytes(b"synthetic asset")
        self.manifest["assets"] = [{
            "file": "assets/figure.png", "media_type": "image/png", "sha256": validator.digest(figure),
            "source_id": "original", "source_locator": "Chapter 1 figure",
        }]
        self.validate()
        self.manifest["assets"][0]["file"] = "assets/../../../../outside.png"
        with self.assertRaisesRegex(ValueError, "escape"):
            self.validate()

    def test_untitled_source_gets_a_supplied_front_matter_title(self):
        front = self.manifest["chapters"][0]
        path = self.revision / "chapters/0001.md"

        def heading(text, spans=(), **supplied):
            path.write_bytes(text.encode("utf-8"))
            front.update(sha256=validator.digest(path), source_spans=list(spans),
                         supplied_title={"text": "Example work", "basis": "metadata", "evidence": "metadata.title"} | supplied)

        heading("# Example work\n")
        self.assertEqual(self.validate(check_sources=True)["preparation_status"], "ready")
        heading("# Example work\n\n原文第一段。\n", front["source_spans"] or
                [{"source_id": "original", "locator": "Paragraph 1"}])
        self.validate()
        for text, spans, message in (("# Another title\n", (), "opening heading"),
                                     ("Example work\n", (), "opening heading"),
                                     ("# Example work\n\nUnsourced epigraph.\n", (), "needs source spans")):
            heading(text, spans)
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, message):
                self.validate()
        heading("# Example work\n")
        self.manifest["chapters"][1]["supplied_title"] = front["supplied_title"]
        with self.assertRaisesRegex(ValueError, "Only the front matter"):
            self.validate()
        del self.manifest["chapters"][1]["supplied_title"], front["supplied_title"]
        with self.assertRaisesRegex(ValueError, "source_spans"):
            self.validate()

    def test_cli_works_from_another_directory(self):
        result = subprocess.run(
            [sys.executable, "-B", str(Path(validator.__file__).resolve()), str(self.root / "work.json"), "--check-sources"],
            cwd=self.base, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["work_id"], "example-work")

    def proposal(self, field="/genres", value=None, **changes):
        return {
            "field": field, "value": ["Literary fiction"] if value is None else value,
            "origin": "inferred", "confidence": "medium", "basis_revision": "r0001",
            "evidence": [{"chapter_id": "chapter-1", "locator": "Paragraph 1", "quote": "原文第一段。"}],
            "rationale": "Synthetic inference used to test persistence, not classification quality.",
        } | changes

    def read_work(self):
        return validator.load_json(self.root / "work.json")

    def test_extracts_missing_title_without_overwriting_supplied_or_cleared_title(self):
        path = self.root / "work.json"
        proposal = self.proposal("/title", "第一章", origin="extracted",
                                 evidence=[{"chapter_id": "chapter-1", "locator": "Title heading", "quote": "第一章"}])
        self.work["metadata"]["title"] = None
        self.work["preparation"]["status"] = "in_progress"
        self.save()
        updated = metadata.update(path, "enrich", proposals=[proposal], actor="prepare-manuscript")
        self.assertIn("/title", updated["applied"])
        work = self.read_work()
        self.assertEqual(work["metadata"]["title"], "第一章")
        self.assertEqual(work["metadata_provenance"]["/title"]["origin"], "extracted")
        self.assertEqual(work["metadata_provenance"]["/title"]["review_status"], "proposed")
        for value in ("Author's preferred title", None):
            metadata.update(path, "set", field="/title", value=value)
            self.assertIn("/title", metadata.update(path, "enrich", proposals=[proposal])["skipped"])
            self.assertEqual(self.read_work()["metadata"]["title"], value)

    def test_ready_cannot_silently_omit_an_existing_source_title(self):
        self.work["metadata"]["title"] = None
        with self.assertRaisesRegex(ValueError, "record the source title"):
            self.validate()
        self.work["preparation"]["status"] = "in_progress"
        self.save()
        metadata.update(self.root / "work.json", "set", field="/title", value=None, rationale="Author cleared it")
        self.work = self.read_work()
        self.work["preparation"]["status"] = "ready"
        self.assertEqual(self.validate()["preparation_status"], "ready")

    def test_user_confirmed_title_is_grounded_without_source_evidence(self):
        path = self.root / "work.json"
        metadata.update(path, "set", field="/title", value="An author-chosen title absent from the manuscript")
        proposal = self.proposal("/title", "Superseded agent guess", origin="extracted",
                                 evidence=[{"chapter_id": "chapter-1", "locator": "Old guess", "quote": "Not in source"}])
        result = metadata.update(path, "enrich", proposals=[proposal])
        self.assertIn("/title", result["skipped"])
        work = self.read_work()
        self.assertEqual(work["metadata"]["title"], "An author-chosen title absent from the manuscript")
        self.assertEqual(work["metadata_provenance"]["/title"]["review_status"], "confirmed")
        self.assertEqual(work["metadata_provenance"]["/title"]["evidence"], [])
        work["metadata"]["title"] = None
        metadata.record(work, "/title", "provided", actor="user", rationale="Explicitly left blank", review="confirmed")
        write_json(path, work)
        self.assertEqual(validator.validate(path)["preparation_status"], "ready")
        self.assertIn("/title", metadata.update(path, "enrich", proposals=[proposal])["skipped"])
        self.assertIsNone(self.read_work()["metadata"]["title"])

    def test_inference_is_grounded_proposed_and_does_not_replace_existing_values(self):
        for field, value in (("/audience", "adult"),
                             ("/contributors", [{"id": "a", "name": "A", "roles": ["author"]}])):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "provided by the user"):
                metadata.update(self.root / "work.json", "enrich", actor="prepare-manuscript",
                                proposals=[self.proposal(field, value, origin="extracted")])
        proposals = [self.proposal()]
        result = metadata.update(self.root / "work.json", "enrich", proposals=proposals, actor="prepare-manuscript")
        work = self.read_work()
        self.assertEqual(work["metadata"]["genres"], ["Literary fiction"])
        self.assertEqual(work["metadata"]["title"], "Example work")
        self.assertEqual(result["skipped"], [])
        self.assertEqual(work["metadata_provenance"]["/genres"]["review_status"], "proposed")
        self.assertIsNone(work["metadata"]["extent"]["word_count"])
        self.assertGreater(work["metadata"]["extent"]["non_whitespace_character_count"], 0)
        self.assertEqual(work["metadata"]["extent"]["scope"], self.manifest["scope"])
        self.assertFalse(metadata.update(self.root / "work.json", "enrich", proposals=proposals)["written"])

    def test_unfounded_metadata_proposals_leave_the_record_untouched(self):
        self.work["metadata"]["title"] = None
        self.work["preparation"]["status"] = "in_progress"
        self.save()
        before = (self.root / "work.json").read_bytes()
        cases = [
            self.proposal(evidence=[{"chapter_id": "chapter-1", "locator": "Paragraph 1", "quote": "Invented quote"}]),
            self.proposal("/original_language", "zh"),
            self.proposal("/contributors", [{"id": "narrator", "name": "Narrator", "roles": ["author"]}]),
            self.proposal(basis_revision="r0009"),
            self.proposal("/form", "not-a-form"),
            self.proposal(confidence=None),
            self.proposal("/title", "Invented title", origin="extracted"),
            self.proposal("/subtitle", "Invented subtitle", origin="extracted"),
            self.proposal("/title", "第一章"),  # A title is extracted, not creatively inferred.
        ]
        for proposal in cases:
            with self.subTest(proposal=proposal), self.assertRaises(ValueError):
                metadata.update(self.root / "work.json", "enrich", proposals=[proposal])
            self.assertEqual((self.root / "work.json").read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "JSON array"):
            metadata.update(self.root / "work.json", "enrich", proposals={})

    def test_supplied_filename_heading_is_not_extracted_as_a_source_title(self):
        front = self.manifest["chapters"][0]
        path = self.revision / front["file"]
        path.write_bytes(b"# Filename heading\n\n" + path.read_bytes())
        front.update(sha256=validator.digest(path),
                     supplied_title={"text": "Filename heading", "basis": "source_name", "evidence": "upload filename"})
        self.work["metadata"]["title"] = None
        self.save()
        proposal = self.proposal("/title", "Filename heading", origin="extracted",
                                 evidence=[{"chapter_id": front["chapter_id"], "locator": "Heading",
                                            "quote": "Filename heading"}])
        before = (self.root / "work.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "not a supplied title heading"):
            metadata.update(self.root / "work.json", "enrich", proposals=[proposal])
        self.assertEqual((self.root / "work.json").read_bytes(), before)

    def test_direct_metadata_edits_and_deliberate_clearing_survive_enrichment(self):
        path = self.root / "work.json"
        metadata.update(path, "enrich", proposals=[self.proposal()])
        work = self.read_work()
        work["metadata"]["genres"] = ["User correction"]
        write_json(path, work)
        metadata.update(path, "enrich", proposals=[self.proposal()])
        work = self.read_work()
        self.assertEqual(work["metadata"]["genres"], ["User correction"])
        self.assertEqual(work["metadata_provenance"]["/genres"]["origin"], "user_edit")
        self.assertEqual(work["metadata_provenance"]["/genres"]["review_status"], "unreviewed")
        metadata.update(path, "set", field="/genres", value=[])
        metadata.update(path, "enrich", proposals=[self.proposal()])
        self.assertEqual(self.read_work()["metadata"]["genres"], [])
        self.assertEqual(self.read_work()["metadata_provenance"]["/genres"]["review_status"], "confirmed")

    def test_revision_change_marks_metadata_stale_without_overwriting_it(self):
        path = self.root / "work.json"
        metadata.update(path, "enrich", proposals=[self.proposal()])
        work = self.read_work()
        target = self.root / "revisions/r0002"
        shutil.copytree(self.revision, target)
        manifest = copy.deepcopy(self.manifest)
        manifest["revision"] = "r0002"
        write_json(target / "manifest.json", manifest)
        work["preparation"]["current_revision"] = "r0002"
        write_json(path, work)
        result = metadata.update(path, "enrich")
        self.assertEqual(set(result["stale_fields"]), {"/genres", "/extent"})
        self.assertEqual(self.read_work()["metadata"]["genres"], ["Literary fiction"])
        self.assertEqual(self.read_work()["metadata"]["extent"]["basis_revision"], "r0001")

    def test_partial_scope_cannot_infer_whole_work_form(self):
        self.manifest["scope"]["kind"] = "selected_chapters"
        self.save()
        with self.assertRaisesRegex(ValueError, "whole-work coverage"):
            metadata.update(self.root / "work.json", "enrich", proposals=[self.proposal("/form", "novel")])

    def test_extent_counts_visible_text_without_markdown_urls_or_image_labels(self):
        measured = metadata.measure(self.manifest, {
            "chapter-1": "# A title\n\nOne *quiet* [word](https://example.com/hidden).\n\n![not counted](image.png)\n",
        })
        self.assertEqual(measured["word_count"], 5)
        self.assertEqual(measured["non_whitespace_character_count"], len("AtitleOnequietword."))

    def test_metadata_update_rejects_concurrent_edits(self):
        path = self.root / "work.json"
        before = path.read_bytes()
        candidate = copy.deepcopy(self.work)
        candidate["metadata"]["genres"] = ["Fiction"]  # A real change, so the write is attempted.
        self.work["metadata"]["title"] = "Concurrent correction"
        self.save()
        with self.assertRaisesRegex(ValueError, "concurrently"):
            metadata.save(path, before, candidate)
        self.assertEqual(self.read_work()["metadata"]["title"], "Concurrent correction")
        self.assertFalse((self.root / ".metadata.lock").exists())

    def test_extent_cannot_claim_unbound_units_or_whole_work_from_partial_source(self):
        self.manifest["scope"]["kind"] = "selected_chapters"
        self.save()
        path = self.root / "work.json"
        metadata.update(path, "enrich")
        work = self.read_work()
        extent = copy.deepcopy(work["metadata"]["extent"])
        extent["scope"]["kind"] = "whole_work"
        with self.assertRaisesRegex(ValueError, "whole-work coverage"):
            metadata.update(path, "set", field="/extent", value=extent)
        extent = copy.deepcopy(work["metadata"]["extent"])
        extent["scope"]["chapter_ids"] = ["invented"]
        with self.assertRaisesRegex(ValueError, "known units"):
            metadata.update(path, "set", field="/extent", value=extent)
        self.assertEqual(self.read_work(), work)

    def test_metadata_cli_migrates_and_enriches_from_another_directory(self):
        result = subprocess.run(
            [sys.executable, "-B", str(Path(metadata.__file__).resolve()), "enrich", str(self.root / "work.json")],
            cwd=self.base, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/extent", json.loads(result.stdout)["applied"])


if __name__ == "__main__":
    unittest.main()
