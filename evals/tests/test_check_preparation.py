import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_preparation as checker

NOW = "2026-10-19T12:00:00Z"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class PreparationEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "evals"
        self.case_dir = self.root / "cases/prepare-manuscript/markdown-test-001"
        self.inputs = self.root / "fixtures/manuscripts/sample"
        self.references = self.root / "fixtures/reference-outputs/sample"
        self.candidate = self.base / "candidate"
        self.revision = self.candidate / "revisions/r0001"
        for directory in (self.case_dir, self.inputs, self.references, self.revision / "chapters"):
            directory.mkdir(parents=True, exist_ok=True)
        self.texts = ["# First\n\nA *quiet* beginning.\n\nAnother paragraph.\n",
                      "# Second\n\n> A quotation.\n\nThe ending.\n"]
        self.source = self.inputs / "manuscript.md"
        self.source.write_bytes("\n".join(self.texts).encode())
        chapters, units = [], []
        for number, text in enumerate(self.texts, 1):
            filename = f"{number:04d}.md"
            golden = self.references / filename
            actual = self.revision / "chapters" / filename
            golden.write_bytes(text.encode())
            actual.write_bytes(text.encode())
            title = ("First", "Second")[number - 1]
            chapters.append({
                "chapter_id": f"chosen-by-worker-{number}", "order": number, "source_number": str(number),
                "title": title, "role": "chapter", "file": "chapters/" + filename, "sha256": checker.digest(actual),
                "source_spans": [{"source_id": "worker-source", "locator": title}], "status": "verified",
            })
            units.append({
                "unit_id": f"reference-{number}", "title": title, "source_number": str(number), "role": "chapter",
                "file": "../../../fixtures/reference-outputs/sample/" + filename, "sha256": checker.digest(golden),
                "source_locator": title,
            })
        self.case = {
            "schema_version": 1, "case_id": "markdown-test-001", "task": "manuscript-preparation",
            "input_location": "../../../fixtures/manuscripts/sample", "recursive": False,
            "sources": [{"source_id": "reference-source", "file": "manuscript.md", "sha256": checker.digest(self.source)}],
            "reference_file": "reference-map.json", "expected_metadata": {"title": "Example", "source_language": "en"},
            "expected_preparation_status": "ready", "scope_kind": "whole_work",
            "expected_workflows": {name: {"status": "not_started"} for name in (
                "literary-editing", "literary-translation", "literary-agent-querying", "format-manuscript")},
            "require_trace": False, "manual_checks": [],
        }
        self.reference = {
            "schema_version": 1, "case_id": self.case["case_id"],
            "review": {"status": "approved", "reviewed_by": "synthetic-test-fixture", "reviewed_at": NOW},
            "source_hashes": {"reference-source": checker.digest(self.source)},
            "profile": {"name": "commonmark-v1", "check_inline_formatting": True,
                        "check_block_structure": True, "check_links": True},
            "units": units, "assets": [], "notes": ["Synthetic expected content; not an LLM assessment."],
        }
        self.manifest = {
            "schema_version": 1, "work_id": "worker-selected-id", "revision": "r0001", "status": "verified", "created_at": NOW,
            "sources": [{"source_id": "worker-source", "locator": str(self.source), "format": "markdown",
                         "identity": {"kind": "sha256", "value": checker.digest(self.source)}}],
            "scope": {"kind": "whole_work", "chapter_ids": [c["chapter_id"] for c in chapters]},
            "chapters": chapters, "assets": [],
            "extraction": {"tool": "test fixture", "method": "synthetic example", "normalization_notes": []},
            "verification": {"performed_by": "test", "verified_at": NOW, "coverage_complete": True, "issues": []},
        }
        self.work = {
            "schema_version": 1, "work_id": "worker-selected-id", "record_revision": 1, "updated_at": NOW,
            "metadata": {"title": "Example", "authors": [], "source_language": "en",
                         "work_type": "fiction", "genre": None, "edition": None},
            "discovery": {"location_kind": "directory", "location": str(self.inputs), "recursive": False,
                          "selection_status": "confirmed", "notes": []},
            "preparation": {"status": "ready", "current_revision": "r0001", "blockers": []},
            "workflows": {name: {"status": "not_started", "basis_revision": None, "scope": None,
                                "operation": None, "state_locator": None, "updated_at": None}
                          for name in ("literary-editing", "literary-translation", "literary-agent-querying", "format-manuscript")},
        }
        self.save()

    def save(self):
        write_json(self.case_dir / "case.json", self.case)
        write_json(self.case_dir / "reference-map.json", self.reference)
        write_json(self.candidate / "work.json", self.work)
        write_json(self.revision / "manifest.json", self.manifest)

    def evaluate(self, **kwargs):
        self.save()
        return checker.evaluate(self.case_dir / "case.json", self.candidate / "work.json", eval_root=self.root, **kwargs)

    def changed_chapter(self, text, index=0):
        chapter = self.manifest["chapters"][index]
        path = self.revision / chapter["file"]
        path.write_bytes(text.encode())
        chapter["sha256"] = checker.digest(path)

    def statuses(self, report):
        return {c["check"]: c["status"] for c in report["checks"]}

    def add_ground_truth(self):
        # Hand-authored visible paragraphs, independently of Markdown parsing.
        paragraphs = [["First", "A quiet beginning.", "Another paragraph."],
                      ["Second", "A quotation.", "The ending."]]

        def statistics(values):
            stripped = ["".join(value.split()) for value in values]
            return {
                "nonempty_paragraphs": len(stripped),
                "characters_excluding_whitespace": sum(map(len, stripped)),
                "text_sha256_excluding_whitespace": hashlib.sha256("".join(stripped).encode()).hexdigest(),
                "paragraph_sequence_sha256": hashlib.sha256(
                    json.dumps(stripped, separators=(",", ":")).encode()
                ).hexdigest(),
            }

        truth = {
            "schema_version": 1, "case_id": self.case["case_id"], "status": "verified",
            "counting_policy": "unicode-codepoints-without-whitespace-v1",
            "source_hashes": self.reference["source_hashes"],
            "verification": {"method": "hand-authored synthetic source paragraphs"},
            "counts": {"prepared_markdown_units": 2},
            "totals": {"whole_document": statistics(sum(paragraphs, []))},
            "units": [
                {**{key: unit[key] for key in ("unit_id", "title", "source_number", "role")},
                 "statistics": statistics(text)}
                for unit, text in zip(self.reference["units"], paragraphs)
            ],
            "notes": ["Synthetic source baseline for evaluator tests."],
        }
        path = self.case_dir / "ground-truth.json"
        write_json(path, truth)
        self.case.update(ground_truth_file="ground-truth.json", ground_truth_sha256=checker.digest(path))
        return path

    def test_source_ground_truth_counts_and_fingerprints_are_checked(self):
        self.add_ground_truth()
        report = self.evaluate()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["source_statistics"]["actual"]["characters_excluding_whitespace"], 65)
        self.assertEqual(self.statuses(report)["source_character_and_paragraph_counts"], "passed")
        self.assertEqual(self.statuses(report)["source_text_fingerprints"], "passed")
        self.changed_chapter(self.texts[0].replace("quiet", "loud!"))
        report = self.evaluate()
        self.assertEqual(self.statuses(report)["source_character_and_paragraph_counts"], "passed")
        self.assertEqual(self.statuses(report)["source_text_fingerprints"], "failed")

    def test_character_count_uses_unicode_codepoints_and_excludes_unicode_whitespace(self):
        stats = checker.visible_statistics([
            {"text": "甲 \t乙\n，\u3000A\u00a0😀"}, {"text": "\t\n"},
        ])
        self.assertEqual(stats["characters_excluding_whitespace"], 5)
        self.assertEqual(stats["nonempty_paragraphs"], 1)
        self.assertEqual(stats["text_sha256_excluding_whitespace"],
                         hashlib.sha256("甲乙，A😀".encode("utf-8")).hexdigest())

    def test_reference_cannot_disagree_with_fixed_source_ground_truth(self):
        self.add_ground_truth()
        path = self.references / "0001.md"
        path.write_text(self.texts[0].replace("quiet", "loud!"), encoding="utf-8")
        self.reference["units"][0]["sha256"] = checker.digest(path)
        with self.assertRaisesRegex(ValueError, "Reference content differs from source ground truth"):
            self.evaluate()

    def test_frozen_ground_truth_hash_cannot_be_silently_rewritten(self):
        path = self.add_ground_truth()
        truth = json.loads(path.read_text())
        truth["totals"]["whole_document"]["characters_excluding_whitespace"] += 1
        write_json(path, truth)
        with self.assertRaisesRegex(ValueError, "Frozen ground-truth hash"):
            self.evaluate()

    def test_generic_case_passes_without_requiring_worker_generated_ids(self):
        self.assertEqual(self.evaluate()["status"], "passed")

    def test_equivalent_markdown_serialization_passes(self):
        self.changed_chapter("First\n=====\n\nA _quiet_ beginning.\n\nAnother paragraph.\n")
        self.assertEqual(self.evaluate()["status"], "passed")

    def test_missing_duplicated_rewritten_and_reordered_text_fail_even_with_updated_hashes(self):
        variants = [
            "# First\n\nA *quiet* beginning.\n",
            self.texts[0] + "\nAnother paragraph.\n",
            self.texts[0].replace("quiet", "loud"),
            "# First\n\nAnother paragraph.\n\nA *quiet* beginning.\n",
        ]
        for text in variants:
            with self.subTest(text=text):
                self.changed_chapter(text)
                report = self.evaluate()
                self.assertEqual(self.statuses(report)["package_contract"], "passed")
                self.assertEqual(self.statuses(report)["content_preservation"], "failed")
                self.assertEqual(report["status"], "failed")

    def test_chapter_boundaries_cannot_be_hidden_by_preserving_total_text(self):
        self.changed_chapter(self.texts[0] + "\n> A quotation.\n")
        self.changed_chapter("# Second\n\nThe ending.\n", 1)
        self.assertEqual(self.statuses(self.evaluate())["content_preservation"], "failed")

    def test_formatting_loss_is_reported(self):
        self.changed_chapter(self.texts[1].replace("> ", ""), 1)
        self.assertEqual(self.statuses(self.evaluate())["chapter_boundaries_and_structure"], "failed")

    def test_draft_reference_and_missing_trace_or_visual_review_cannot_pass(self):
        self.reference["review"] = {"status": "draft", "reviewed_by": None, "reviewed_at": None}
        self.case["require_trace"] = True
        self.case["manual_checks"] = ["visual-layout"]
        report = self.evaluate()
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(self.statuses(report)["content_preservation"], "passed")
        for name in ("reference_review", "observed_access_scope", "visual_review"):
            self.assertEqual(self.statuses(report)[name], "not_checked")

    def test_metadata_and_premature_downstream_progress_fail(self):
        self.work["metadata"]["title"] = "Wrong title"
        self.work["workflows"]["literary-translation"] = {
            "status": "in_progress", "basis_revision": "r0001", "scope": copy.deepcopy(self.manifest["scope"]),
            "operation": "translate", "state_locator": "translation-state", "updated_at": NOW,
        }
        report = self.evaluate()
        self.assertEqual(self.statuses(report)["metadata"], "failed")
        self.assertEqual(self.statuses(report)["downstream_ownership"], "failed")

    def test_resume_case_can_require_preservation_of_existing_workflow_state(self):
        existing = {
            "status": "completed", "basis_revision": "r0001", "scope": copy.deepcopy(self.manifest["scope"]),
            "operation": "translate", "state_locator": "existing-translation-project", "updated_at": NOW,
        }
        self.work["workflows"]["literary-translation"] = copy.deepcopy(existing)
        self.case["expected_workflows"]["literary-translation"] = copy.deepcopy(existing)
        self.assertEqual(self.evaluate()["status"], "passed")
        self.work["workflows"]["literary-translation"]["state_locator"] = "discarded-and-replaced"
        self.assertEqual(self.statuses(self.evaluate())["downstream_ownership"], "failed")

    def test_rebound_candidate_source_cannot_escape_case_location(self):
        outside = self.base / "private.txt"
        outside.write_text("unrelated", encoding="utf-8")
        self.work["discovery"]["location"] = str(self.base)
        self.manifest["sources"][0]["locator"] = str(outside)
        with patch.object(checker.CONTRACT, "validate", side_effect=AssertionError("Do not inspect arbitrary source paths")):
            self.assertEqual(self.evaluate()["status"], "failed")

    def test_source_mutation_fails(self):
        self.source.write_bytes(b"changed source")
        self.assertEqual(self.statuses(self.evaluate())["source_integrity"], "failed")

    def test_trusted_trace_and_review_receipt_are_candidate_bound(self):
        self.case["require_trace"] = True
        self.case["manual_checks"] = ["visual-layout"]
        first = self.evaluate()
        trace = self.base / "trace.json"
        receipt = self.base / "review.json"
        data = {
            "case_id": self.case["case_id"], "producer": "harness", "complete": True,
            "candidate_fingerprint": first["candidate_fingerprint"],
            "case_sha256": first["case_sha256"],
            "events": [{"operation": "read", "path": str(self.source)}],
        }
        write_json(trace, data)
        write_json(receipt, {
            "case_id": self.case["case_id"], "candidate_fingerprint": first["candidate_fingerprint"],
            "case_sha256": first["case_sha256"], "reference_sha256": first["reference_sha256"],
            "reviewer": "test-reviewer", "reviewed_at": NOW, "checks": {"visual-layout": "passed"},
        })
        self.assertEqual(self.evaluate(trace_path=trace, visual_review_path=receipt)["status"], "passed")
        data["events"].append({"operation": "read", "path": str(self.case_dir / "reference-map.json")})
        write_json(trace, data)
        self.assertEqual(self.statuses(self.evaluate(trace_path=trace))["observed_access_scope"], "failed")
        self.changed_chapter(self.texts[0].replace("*quiet*", "_quiet_"))
        self.assertEqual(self.statuses(self.evaluate(visual_review_path=receipt))["visual_review"], "failed")

    def test_invalid_candidate_schema_returns_failure_report(self):
        write_json(self.candidate / "work.json", {"metadata": "invalid"})
        report = checker.evaluate(self.case_dir / "case.json", self.candidate / "work.json", eval_root=self.root)
        self.assertEqual(report["status"], "failed")

    def test_reference_hashes_are_enforced(self):
        (self.references / "0001.md").write_text("modified oracle", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Reference Markdown hash"):
            self.evaluate()

    def test_images_compare_by_content_hash_not_output_filename(self):
        golden_assets = self.references / "assets"
        actual_assets = self.revision / "assets"
        golden_assets.mkdir()
        actual_assets.mkdir()
        original, renamed = golden_assets / "original.png", actual_assets / "renamed.png"
        original.write_bytes(b"fixture image")
        renamed.write_bytes(original.read_bytes())
        golden = self.references / "0001.md"
        golden.write_text("# First\n\n![Caption](assets/original.png)\n", encoding="utf-8")
        self.reference["units"][0]["sha256"] = checker.digest(golden)
        self.reference["assets"] = [{
            "file": "../../../fixtures/reference-outputs/sample/assets/original.png", "sha256": checker.digest(original),
        }]
        self.manifest["assets"] = [{
            "file": "assets/renamed.png", "sha256": checker.digest(renamed), "media_type": "image/png",
            "source_id": "worker-source", "source_locator": "Figure 1",
        }]
        self.changed_chapter("# First\n\n![Caption](../assets/renamed.png)\n")
        self.assertEqual(self.evaluate()["status"], "passed")

    def test_tables_code_and_unsupported_markup_are_handled_explicitly(self):
        profile = self.reference["profile"]
        first = checker.canonical_markdown("| A | B |\\n|---|---|\\n| x | y |".replace("\\n", "\n"), profile)
        second = checker.canonical_markdown("| A | B |\\n|---|---|\\n| y | x |".replace("\\n", "\n"), profile)
        self.assertNotEqual(first, second)
        self.assertEqual(checker.canonical_markdown("```\ncode\n```\n", profile),
                         checker.canonical_markdown("    code\n", profile))
        with self.assertRaisesRegex(ValueError, "HTML"):
            checker.canonical_markdown("<div>Hidden structure</div>", profile)
        with self.assertRaisesRegex(ValueError, "Footnote"):
            checker.canonical_markdown("Text[^1]\n\n[^1]: Note", profile)
        checker.canonical_markdown("`[^1]` is literal code.\n\n```\n[^1]: literal\n```\n", profile)

    def test_concurrent_candidate_change_cannot_pass(self):
        original = checker.differences

        def changed(expected, actual):
            result = original(expected, actual)
            (self.revision / "chapters/0001.md").write_bytes(b"Changed after comparison\n")
            return result

        with patch.object(checker, "differences", side_effect=changed):
            report = self.evaluate()
        self.assertEqual(report["status"], "failed")
        self.assertEqual(self.statuses(report)["inputs_stable"], "failed")

    def test_blocked_case_can_expect_no_prepared_revision(self):
        self.case["expected_preparation_status"] = "blocked"
        self.reference["units"] = []
        self.work["preparation"] = {"status": "blocked", "current_revision": None, "blockers": ["Unsupported source adapter"]}
        self.assertEqual(self.evaluate()["status"], "passed")

    def test_missing_source_case_can_expect_blocked_without_invented_content(self):
        self.source.unlink()
        self.case["sources"] = []
        self.case["expected_preparation_status"] = "blocked"
        self.reference["source_hashes"] = {}
        self.reference["units"] = []
        self.work["preparation"] = {"status": "blocked", "current_revision": None, "blockers": ["No manuscript found"]}
        self.work["discovery"]["selection_status"] = "unresolved"
        report = self.evaluate()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(self.statuses(report)["source_integrity"], "not_checked")

    def test_candidate_package_cannot_overlap_hidden_reference_data(self):
        write_json(self.references / "work.json", self.work)
        with self.assertRaisesRegex(ValueError, "separate"):
            checker.evaluate(self.case_dir / "case.json", self.references / "work.json", eval_root=self.root)

    def test_cli_writes_machine_readable_report(self):
        result = subprocess.run([
            sys.executable, "-B", str(Path(checker.__file__).resolve()), "--data-dir", str(self.root),
            "--case", self.case["case_id"], "--work", str(self.candidate / "work.json"),
        ], cwd=self.base, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        reports = list((self.root / "results").glob("preparation-*/evaluation.json"))
        self.assertEqual(len(reports), 1)
        self.assertEqual(json.loads(reports[0].read_text())["status"], "passed")


if __name__ == "__main__":
    unittest.main()
