import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import validate_proposal as validator

SKILL = Path(__file__).resolve().parents[1]
EXAMPLE = SKILL / "references/proposal.example.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.proposal = validator.load_json(EXAMPLE)

    def with_vendor(self, binding):
        proposal = copy.deepcopy(self.proposal)
        profile = validator.vendor_profiles().resolve("ingramspark", binding)
        proposal["vendor_profile"] = profile
        target = proposal["edition_brief"]["production_targets"][0]
        target.update(vendor_id="ingramspark", binding=binding,
                      vendor_profile_ref={"locator": "vendor_profile/data", "sha256": profile["sha256"]})
        return proposal

    def test_vendor_variants_bind_exact_data_and_remain_proposals(self):
        for binding in ("paperback", "hardcover"):
            with self.subTest(binding=binding):
                proposal = self.with_vendor(binding)
                checked = validator.validate(proposal)
                self.assertFalse(checked["production_verified"])
                self.assertFalse(checked["approved"])
                self.assertEqual(proposal["vendor_profile"]["data"]["variant"]["binding"], binding)
                proposal["vendor_profile"]["data"]["rules"][0]["statement"] = "Fabricated vendor requirement."
                with self.assertRaisesRegex(ValueError, "data/hash"):
                    validator.validate(proposal)
                proposal = self.with_vendor(binding)
                proposal["vendor_profile"]["data"]["docx_guidance"]["mirrored_margins"] = 1
                with self.assertRaisesRegex(ValueError, "data/hash"):
                    validator.validate(proposal)

    def test_binding_mismatch_is_rejected_and_custom_trim_coverage_is_not_a_vendor_wide_ban(self):
        proposal = self.with_vendor("hardcover")
        target = proposal["edition_brief"]["production_targets"][0]
        target["binding"] = "paperback"
        with self.assertRaisesRegex(ValueError, "vendor/binding"):
            validator.validate(proposal)
        target["binding"] = "hardcover"
        target["trim_mm"] = proposal["design_system"]["page"]["trim_mm"] = {"width": 101.6, "height": 152.4}
        self.assertIn("outside the reviewed", validator.validate(proposal)["vendor_warnings"][0])
        paperback = self.with_vendor("paperback")
        paperback["edition_brief"]["production_targets"][0]["trim_mm"] = paperback["design_system"]["page"]["trim_mm"] = {
            "width": 101.6, "height": 152.4}
        self.assertEqual(validator.validate(paperback)["vendor_warnings"], [])

    def test_vendor_profile_requires_selection_not_technical_questionnaire(self):
        proposal = self.with_vendor("paperback")
        proposal["vendor_profile"] = None
        with self.assertRaisesRegex(ValueError, "require"):
            validator.validate(proposal)
        proposal = self.with_vendor("paperback")
        proposal["questions"] = []
        self.assertTrue(validator.validate(proposal)["valid"])

    def test_technical_questions_and_page_count_preference_are_not_proposal_inputs(self):
        for kind in ("capability-check", "vendor-conflict", "unsupported-content"):
            proposal = copy.deepcopy(self.proposal)
            proposal["questions"][0]["kind"] = kind
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validator.validate(proposal)
        self.proposal["edition_brief"]["preferred_page_count"] = 250
        with self.assertRaises(ValueError):
            validator.validate(self.proposal)

    def test_standalone_example_needs_no_workflow_context(self):
        self.assertNotIn("parent_workflow", self.proposal["basis"])
        self.assertNotIn("parent_run_id", self.proposal["basis"])
        result = validator.validate(self.proposal)
        self.assertEqual(result["status"], "proposed")
        for field in ("preparation_checked", "external_artifacts_checked", "approved", "production_verified"):
            self.assertFalse(result[field])

    def test_approval_production_and_unknown_fields_are_rejected(self):
        for path, value in (
            (("status",), "approved"), (("qa",), {"passed": True}),
            (("approval",), {"actor": "human"}), (("output_path",), "book.docx"),
            (("design_system", "page", "mystery"), True),
            (("basis", "parent_workflow"), "literary-editing"),
            (("basis", "parent_run_id"), "example-run"),
        ):
            with self.subTest(path=path):
                candidate = copy.deepcopy(self.proposal)
                owner = candidate
                for key in path[:-1]:
                    owner = owner[key]
                owner[path[-1]] = value
                with self.assertRaises(ValueError):
                    validator.validate(candidate)

    def test_duplicate_and_dangling_ids_are_rejected(self):
        changes = (
            lambda p: p["evidence"].append(copy.deepcopy(p["evidence"][0])),
            lambda p: p["text_roles"][0].update(style_id="missing"),
            lambda p: p["reading"].update(evidence_refs=["missing"]),
            lambda p: p["design_system"]["styles"].append(copy.deepcopy(p["design_system"]["styles"][1])),
            lambda p: p["recommendations"][0].update(path="/design_system/missing"),
            lambda p: p["questions"][0].update(path="/design_system/styles/-1"),
        )
        for change in changes:
            with self.subTest(change=change):
                candidate = copy.deepcopy(self.proposal)
                change(candidate)
                with self.assertRaises(ValueError):
                    validator.validate(candidate)

    def test_inferred_reading_cannot_supply_author_facts(self):
        self.proposal["author_preferences"].update(imprint="Invented Press", evidence_refs=["sample-text"])
        with self.assertRaisesRegex(ValueError, "Author preferences"):
            validator.validate(self.proposal)

    def test_supplied_reading_requires_a_bound_reference(self):
        self.proposal["reading"]["source"] = "supplied"
        with self.assertRaisesRegex(ValueError, "Supplied reading"):
            validator.validate(self.proposal)

    def test_invalid_geometry_type_and_navigation_are_rejected(self):
        changes = (
            lambda p: p["design_system"]["page"]["trim_mm"].update(width=1),
            lambda p: p["design_system"]["styles"][0]["font"].update(size_pt=-1),
            lambda p: p["design_system"]["styles"][1].update(heading_level=None),
            lambda p: p["design_system"]["navigation"].update(toc_depth=1),
            lambda p: p["design_system"]["navigation"].update(ornament="*"),
            lambda p: p["text_roles"][0]["occurrences"][0].update(end_byte=0),
            lambda p: p["basis"]["preparation"]["scope"].update(chapter_ids=["chapter-one"]),
            lambda p: p["design_system"]["page"].update(chapter_start="recto"),
        )
        for change in changes:
            with self.subTest(change=change):
                candidate = copy.deepcopy(self.proposal)
                change(candidate)
                with self.assertRaises(ValueError):
                    validator.validate(candidate)

    def test_all_design_groups_require_rationale(self):
        self.proposal["recommendations"].pop()
        with self.assertRaisesRegex(ValueError, "rationale/evidence"):
            validator.validate(self.proposal)

    def test_duplicate_keys_and_nonfinite_numbers_are_not_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "invalid.json"
            for text in ('{"revision": 1, "revision": 2}', '{"x": NaN}', '{"x": 1e9999}'):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    validator.load_json(path)

    def make_preparation(self, base):
        root = base / "prepared"
        revision = root / "revisions/r0001"
        (revision / "chapters").mkdir(parents=True)
        parts = [b"# Example\n", "## One\n\nCaf\u00e9 is quiet.\n".encode("utf-8")]
        source = base / "original.md"
        source.write_bytes(b"\n".join(parts))
        ids = ["front-matter", "chapter-one"]
        units = []
        for i, (unit_id, data) in enumerate(zip(ids, parts), 1):
            file = f"chapters/{i:04d}.md"
            (revision / file).write_bytes(data)
            units.append({
                "chapter_id": unit_id, "order": i, "source_number": None,
                "title": "Example" if i == 1 else "One",
                "role": "front_matter" if i == 1 else "chapter", "file": file,
                "sha256": digest(data), "source_spans": [{"source_id": "original", "locator": f"Fixture unit {i}"}],
                "status": "verified",
            })
        manifest = {
            "schema_version": 1, "work_id": "example-work", "revision": "r0001",
            "status": "verified", "created_at": "2026-11-13T00:00:00Z",
            "sources": [{"source_id": "original", "locator": str(source), "format": "markdown",
                         "identity": {"kind": "sha256", "value": digest(source.read_bytes())}}],
            "scope": {"kind": "whole_work", "chapter_ids": ids}, "chapters": units, "assets": [],
            "extraction": {"tool": "fixture", "method": "Exact synthetic units", "normalization_notes": []},
            "verification": {"performed_by": "test", "verified_at": "2026-11-13T00:00:00Z",
                             "coverage_complete": True, "issues": []},
        }
        work = validator.load_json(SKILL.parent / "prepare-manuscript/references/work.example.json")
        work["metadata"].update(title="Example", manuscript_language="en-US")
        work["discovery"].update(location_kind="file", location=str(source), selection_status="confirmed")
        work["preparation"].update(status="ready", current_revision="r0001")
        work_path = root / "work.json"
        for path, value in ((work_path, work), (revision / "manifest.json", manifest)):
            path.write_text(json.dumps(value) + "\n", encoding="utf-8")
        self.proposal["basis"]["preparation"].update(
            work_sha256=digest(work_path.read_bytes()), manifest_sha256=digest((revision / "manifest.json").read_bytes()),
            units=[{"chapter_id": u["chapter_id"], "sha256": u["sha256"]} for u in units],
        )
        self.proposal["evidence"][0]["sha256"] = digest(parts[1])
        self.proposal["text_roles"][0]["occurrences"] = [{
            "chapter_id": ids[1], "chapter_sha256": digest(parts[1]),
            "start_byte": 8, "end_byte": len(parts[1]), "text_sha256": digest(parts[1][8:]),
        }]
        return work_path, source

    def test_local_context_checks_sources_and_never_modifies_preparation(self):
        with tempfile.TemporaryDirectory() as folder:
            work, source = self.make_preparation(Path(folder).resolve())
            before = {p: p.read_bytes() for p in work.parent.rglob("*") if p.is_file()}
            self.assertTrue(validator.validate(self.proposal, work_path=work)["preparation_checked"])
            self.assertEqual(before, {p: p.read_bytes() for p in before})
            source.write_bytes(b"Changed source")
            with self.assertRaisesRegex(ValueError, "Original source changed"):
                validator.validate(self.proposal, work_path=work)

    def test_stale_metadata_and_out_of_bounds_or_split_utf8_spans_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            work, _ = self.make_preparation(Path(folder).resolve())
            valid = copy.deepcopy(self.proposal)
            self.proposal["basis"]["preparation"]["work_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "Stale"):
                validator.validate(self.proposal, work_path=work)
            for end in (12, 1000):
                self.proposal = copy.deepcopy(valid)
                self.proposal["text_roles"][0]["occurrences"][0]["end_byte"] = end
                with self.assertRaises((ValueError, UnicodeError)):
                    validator.validate(self.proposal, work_path=work)

    def test_changed_occurrence_hash_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            work, _ = self.make_preparation(Path(folder).resolve())
            self.proposal["text_roles"][0]["occurrences"][0]["text_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "span hash"):
                validator.validate(self.proposal, work_path=work)

    def test_cli_runs_outside_repository(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, "-B", str(SKILL / "scripts/validate_proposal.py"), str(EXAMPLE)],
                                    cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)["approved"])

    def test_important_excerpts_are_bound_like_role_occurrences(self):
        with tempfile.TemporaryDirectory() as folder:
            work, _ = self.make_preparation(Path(folder).resolve())
            excerpt = copy.deepcopy(self.proposal["text_roles"][0]["occurrences"][0])
            self.proposal["reading"]["important_excerpts"] = [excerpt]
            self.assertTrue(validator.validate(self.proposal, work_path=work)["preparation_checked"])
            excerpt["chapter_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "changed prepared unit"):
                validator.validate(self.proposal, work_path=work)

    def test_prepared_evidence_cannot_claim_another_unit_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            work, _ = self.make_preparation(Path(folder).resolve())
            self.proposal["evidence"][0]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "exact bound unit"):
                validator.validate(self.proposal, work_path=work)


if __name__ == "__main__":
    unittest.main()
