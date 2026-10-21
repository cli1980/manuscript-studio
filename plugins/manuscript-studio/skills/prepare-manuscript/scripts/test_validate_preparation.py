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
WORKFLOWS = ("literary-editing", "literary-translation", "literary-agent-querying", "format-manuscript")


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
                "role": "chapter", "file": f"chapters/{number:04d}.md",
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
            "schema_version": 1, "work_id": "example-work", "record_revision": 1, "updated_at": NOW,
            "metadata": {"title": "Example work", "authors": [], "source_language": "zh",
                         "work_type": "fiction", "genre": None, "edition": None},
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

    def test_discovery_only_record_does_not_claim_readiness(self):
        self.work["preparation"] = {"status": "not_started", "current_revision": None, "blockers": []}
        self.work["discovery"]["selection_status"] = "unresolved"
        self.work["metadata"]["source_language"] = None
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

    def test_metadata_migration_preserves_source_and_existing_workflow_state(self):
        self.work["metadata"]["authors"] = ["作者甲", "Author B"]
        self.work["metadata"]["genre"] = "Literary fiction"
        self.work["metadata"]["edition"] = "Author revision"
        self.workflow(status="completed")
        self.save()
        original_manifest = (self.revision / "manifest.json").read_bytes()
        before = (self.root / "work.json").read_bytes()
        result = metadata.update(self.root / "work.json", "migrate")
        work = self.read_work()
        self.assertTrue(result["written"])
        self.assertEqual(work["schema_version"], 2)
        self.assertEqual(validator.legacy_metadata(work), self.work["metadata"])
        self.assertIsNone(work["metadata"]["original_language"])
        self.assertEqual(work["workflows"], self.work["workflows"])
        self.assertEqual((self.revision / "manifest.json").read_bytes(), original_manifest)
        self.assertEqual(next((self.root / "metadata-history").iterdir()).read_bytes(), before)
        self.assertFalse(metadata.update(self.root / "work.json", "migrate")["written"])

    def test_inference_is_grounded_proposed_and_does_not_replace_existing_values(self):
        proposals = [self.proposal(), self.proposal("/title", "Different title", origin="extracted")]
        result = metadata.update(self.root / "work.json", "enrich", proposals=proposals, actor="prepare-manuscript")
        work = self.read_work()
        self.assertEqual(work["metadata"]["genres"], ["Literary fiction"])
        self.assertEqual(work["metadata"]["title"], "Example work")
        self.assertEqual(result["skipped"], ["/title"])
        self.assertEqual(work["metadata_provenance"]["/genres"]["review_status"], "proposed")
        self.assertIsNone(work["metadata"]["extent"]["word_count"])
        self.assertGreater(work["metadata"]["extent"]["non_whitespace_character_count"], 0)
        self.assertEqual(work["metadata"]["extent"]["scope"], self.manifest["scope"])
        self.assertFalse(metadata.update(self.root / "work.json", "enrich", proposals=proposals)["written"])

    def test_unfounded_metadata_proposals_leave_the_record_untouched(self):
        before = (self.root / "work.json").read_bytes()
        cases = [
            self.proposal(evidence=[{"chapter_id": "chapter-1", "locator": "Paragraph 1", "quote": "Invented quote"}]),
            self.proposal("/original_language", "zh"),
            self.proposal("/contributors", [{"id": "narrator", "name": "Narrator", "roles": ["author"]}]),
            self.proposal(basis_revision="r0009"),
            self.proposal("/form", "not-a-form"),
            self.proposal(confidence=None),
        ]
        for proposal in cases:
            with self.subTest(proposal=proposal), self.assertRaises(ValueError):
                metadata.update(self.root / "work.json", "enrich", proposals=[proposal])
            self.assertEqual((self.root / "work.json").read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "JSON array"):
            metadata.update(self.root / "work.json", "enrich", proposals={})

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
        candidate = metadata.migrate(self.work)
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
