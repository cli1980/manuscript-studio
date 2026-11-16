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
            lambda p: p["text_roles"][0]["occurrences"][0].update(paragraph_index=0),
            lambda p: p["basis"]["preparation"]["scope"].update(chapter_ids=["chapter-one"]),
            lambda p: p["design_system"]["page"].update(chapter_start="recto"),
        )
        for change in changes:
            with self.subTest(change=change):
                candidate = copy.deepcopy(self.proposal)
                change(candidate)
                with self.assertRaises(ValueError):
                    validator.validate(candidate)

    def test_widow_orphan_inputs_allow_zero_mixed_and_larger_nonzero_values(self):
        for widow, orphan in ((0, 0), (0, 3), (2, 0), (1, 1), (3, 4), (7, 9)):
            with self.subTest(widow=widow, orphan=orphan):
                candidate = copy.deepcopy(self.proposal)
                paragraph = candidate["design_system"]["styles"][0]["paragraph"]
                paragraph.update(widow_lines=widow, orphan_lines=orphan)
                self.assertTrue(validator.validate(candidate)["valid"])
                self.assertEqual((paragraph["widow_lines"], paragraph["orphan_lines"]), (widow, orphan))
        for field in ("widow_lines", "orphan_lines"):
            for value in (-1, 1.5, True, "2"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    candidate = copy.deepcopy(self.proposal)
                    candidate["design_system"]["styles"][0]["paragraph"][field] = value
                    validator.validate(candidate)

    def test_all_design_groups_require_rationale(self):
        self.proposal["recommendations"].pop()
        with self.assertRaisesRegex(ValueError, "rationale/evidence"):
            validator.validate(self.proposal)

    def test_explicit_header_footer_variants_templates_and_section_overrides(self):
        furniture = self.proposal["design_system"]["furniture"]
        settings = furniture["default_section"]
        self.assertEqual(set(settings["headers"]), {"default", "even", "first"})
        self.assertEqual(set(settings["footers"]), {"default", "even", "first"})
        override = copy.deepcopy(settings)
        override["footer_distance_mm"] = 8
        override["headers"]["default"] = {"link_to_previous": True, "paragraphs": []}
        override["footers"]["first"]["paragraphs"] = [{
            "style_id": "page-footer", "alignment": "center",
            "content": {"preset": "custom", "template": "Page {page} of {page_count} {{draft}}"},
        }]
        furniture["section_overrides"] = [{"chapter_id": "chapter-one", "settings": override}]
        self.assertTrue(validator.validate(self.proposal)["valid"])
        sections = validator.furniture_sections(self.proposal)
        self.assertIs(sections[0][1], settings)
        self.assertIs(sections[1][1], override)
        self.assertEqual(validator.furniture_tokens("{{page}} {work_title} {page}"), {"work_title", "page"})

    def test_header_footer_rejects_unknown_styles_unsafe_templates_and_invalid_linking(self):
        for text in ("{missing}", "{page!r}", "{work_title.upper}", "{page:04d}", "{page", "{0}", "line\nbreak"):
            candidate = copy.deepcopy(self.proposal)
            candidate["design_system"]["furniture"]["default_section"]["headers"]["default"]["paragraphs"][0]["content"] = {
                "preset": "custom", "template": text}
            with self.subTest(text=text), self.assertRaises(ValueError):
                validator.validate(candidate)
        for change in (
            lambda f: f["default_section"].update(header_distance_mm=-1),
            lambda f: f["default_section"].update(footer_distance_mm=1000),
            lambda f: f["default_section"]["headers"]["default"]["paragraphs"][0].update(style_id="missing"),
            lambda f: f["default_section"]["headers"]["default"].update(link_to_previous=True),
            lambda f: f.update(different_odd_even=False),
            lambda f: f["default_section"].update(different_first_page=False,
                headers={**f["default_section"]["headers"], "first": f["default_section"]["headers"]["default"]}),
        ):
            candidate = copy.deepcopy(self.proposal)
            change(candidate["design_system"]["furniture"])
            with self.subTest(change=change), self.assertRaises(ValueError):
                validator.validate(candidate)
        settings = copy.deepcopy(self.proposal["design_system"]["furniture"]["default_section"])
        settings["headers"]["default"] = {"link_to_previous": True, "paragraphs": []}
        self.proposal["design_system"]["furniture"]["default_section"] = settings
        self.proposal["design_system"]["furniture"]["section_overrides"] = []
        with self.assertRaisesRegex(ValueError, "first section"):
            validator.validate(self.proposal)

    def test_header_footer_overrides_must_have_unique_bound_unit_ids(self):
        furniture = self.proposal["design_system"]["furniture"]
        for ids in (["missing"], ["chapter-one", "chapter-one"]):
            furniture["section_overrides"] = [
                {"chapter_id": chapter_id, "settings": copy.deepcopy(furniture["default_section"])}
                for chapter_id in ids
            ]
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                validator.validate(self.proposal)

    def test_header_footer_requires_metadata_only_when_consumed(self):
        with tempfile.TemporaryDirectory() as folder:
            work, _ = self.make_preparation(Path(folder).resolve())
            paragraph = self.proposal["design_system"]["furniture"]["default_section"]["headers"]["default"]["paragraphs"][0]
            paragraph["content"] = {"preset": "author"}
            with self.assertRaisesRegex(ValueError, "Missing author metadata"):
                validator.validate(self.proposal, work_path=work)
            metadata = validator.load_json(work)
            metadata["metadata"]["contributors"] = [
                {"id": "author-one", "name": "First Author", "roles": ["author"]},
                {"id": "translator", "name": "Translator", "roles": ["translator"]},
                {"id": "author-two", "name": "Second Author", "roles": ["author", "editor"]},
            ]
            work.write_text(json.dumps(metadata), encoding="utf-8")
            self.proposal["basis"]["preparation"]["work_sha256"] = digest(work.read_bytes())
            self.assertTrue(validator.validate(self.proposal, work_path=work)["valid"])
            paragraph["content"] = {"preset": "custom", "template": "Literal header {page}"}
            self.assertTrue(validator.validate(self.proposal, work_path=work)["valid"])
            front = self.proposal["design_system"]["furniture"]["section_overrides"][0]["settings"]
            front["headers"]["default"]["paragraphs"][0]["content"] = {"preset": "page-number"}
            with self.assertRaisesRegex(ValueError, "Unnumbered front matter"):
                validator.validate(self.proposal, work_path=work)

    def test_content_presets_are_closed_and_have_one_template_authority(self):
        expected = {"book-title": "{work_title}", "chapter-name": "{chapter_title}", "author": "{author}",
                    "page-number": "{page}", "page-x-of-y": "Page {page} of {page_count}"}
        self.assertEqual(validator.furniture_presets(), expected)
        definition = validator.load_json(validator.SCHEMA)["$defs"]["furniture_content"]
        self.assertEqual(set(definition["properties"]["preset"]["enum"]), set(expected) | {"custom"})
        for preset, template in expected.items():
            with self.subTest(preset=preset):
                candidate = copy.deepcopy(self.proposal)
                candidate["design_system"]["furniture"]["default_section"]["headers"]["default"]["paragraphs"][0]["content"] = {
                    "preset": preset}
                self.assertTrue(validator.validate(candidate)["valid"])
                self.assertEqual(validator.furniture_template({"preset": preset}), template)
        for content in ({}, {"preset": "missing"}, {"preset": "none"}, {"preset": "custom"},
                        {"preset": "custom", "template": ""}, {"preset": "custom", "template": " "},
                        {"preset": "book-title", "template": "Conflicting title"}):
            candidate = copy.deepcopy(self.proposal)
            candidate["design_system"]["furniture"]["default_section"]["headers"]["default"]["paragraphs"][0]["content"] = content
            with self.subTest(content=content), self.assertRaises(ValueError):
                validator.validate(candidate)
        self.proposal["contract"] = "interior-design-proposal/3"
        self.proposal["schema_version"] = 3
        with self.assertRaises(ValueError):
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
            "paragraph_index": 2, "paragraph_sha256": digest("Caf\u00e9 is quiet.".encode("utf-8")),
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

    def reading_excerpt(self, work):
        path = work.parent / "revisions/r0001/chapters/0002.md"
        data = path.read_bytes()
        return {"chapter_id": "chapter-one", "chapter_sha256": digest(data),
                "start_byte": 8, "end_byte": len(data), "text_sha256": digest(data[8:])}

    def test_stale_metadata_and_out_of_bounds_or_split_utf8_excerpts_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            work, _ = self.make_preparation(Path(folder).resolve())
            valid = copy.deepcopy(self.proposal)
            self.proposal["basis"]["preparation"]["work_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "Stale"):
                validator.validate(self.proposal, work_path=work)
            for end in (12, 1000):
                self.proposal = copy.deepcopy(valid)
                excerpt = self.reading_excerpt(work)
                excerpt["end_byte"] = end
                self.proposal["reading"]["important_excerpts"] = [excerpt]
                with self.assertRaises((ValueError, UnicodeError)):
                    validator.validate(self.proposal, work_path=work)

    def test_changed_occurrence_hash_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            work, _ = self.make_preparation(Path(folder).resolve())
            self.proposal["text_roles"][0]["occurrences"][0]["paragraph_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "Paragraph hash"):
                validator.validate(self.proposal, work_path=work)

    def test_cli_runs_outside_repository(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, "-B", str(SKILL / "scripts/validate_proposal.py"), str(EXAMPLE)],
                                    cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)["approved"])

    def test_important_excerpts_remain_byte_bound_reading_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            work, _ = self.make_preparation(Path(folder).resolve())
            excerpt = self.reading_excerpt(work)
            self.proposal["reading"]["important_excerpts"] = [excerpt]
            self.assertTrue(validator.validate(self.proposal, work_path=work)["preparation_checked"])
            excerpt["chapter_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "changed prepared unit"):
                validator.validate(self.proposal, work_path=work)

    def test_catalog_lists_structural_paragraphs_not_inline_spans(self):
        data = ("# Heading\r\n\r\nFirst *italic* &amp; **bold**.\r\n"
                "Still first [link](https://example.com).\r\n\r\n"
                "> Quoted **paragraph**.\r\n>\r\n> Second quote.\r\n\r\n"
                "- Item one\r\n- Item two\r\n\r\n```md\r\nNot a paragraph\r\n\r\n"
                "nor this\r\n```\r\n\r\n---\r\n").encode("utf-8")
        before = data[:]
        catalog = validator.paragraphs(data)
        self.assertEqual([p["paragraph_index"] for p in catalog], [1, 2, 3, 4, 5, 6])
        self.assertEqual([p["kind"] for p in catalog], ["heading"] + ["paragraph"] * 5)
        self.assertEqual([p["markdown"] for p in catalog], [
            "Heading", "First *italic* &amp; **bold**.\nStill first [link](https://example.com).",
            "Quoted **paragraph**.", "Second quote.", "Item one", "Item two",
        ])
        self.assertEqual(data, before)
        unicode_text = "*Caf\u00e9 \U0001f642 e\u0301*  \nnext line\u2028same paragraph"
        self.assertEqual(validator.paragraphs(unicode_text.encode("utf-8")), [{
            "paragraph_index": 1, "paragraph_sha256": digest(unicode_text.encode("utf-8")),
            "kind": "paragraph", "markdown": unicode_text,
        }])

    def test_roles_reject_legacy_inline_ranges_and_duplicate_assignments(self):
        occurrence = self.proposal["text_roles"][0]["occurrences"][0]
        for extra in ({"start_byte": 0}, {"end_byte": 2}, {"text_sha256": "0" * 64},
                      {"start_character": 0}, {"scope": "inline"}):
            candidate = copy.deepcopy(self.proposal)
            candidate["text_roles"][0]["occurrences"][0].update(extra)
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                validator.validate(candidate)
        self.proposal["text_roles"][0]["occurrences"].append(copy.deepcopy(occurrence))
        with self.assertRaisesRegex(ValueError, "only one role"):
            validator.validate(self.proposal)
        self.proposal["text_roles"][0]["occurrences"].pop()
        other = copy.deepcopy(self.proposal["text_roles"][0])
        other["id"] = "another-role"
        self.proposal["text_roles"].append(other)
        with self.assertRaisesRegex(ValueError, "only one role"):
            validator.validate(self.proposal)

    def test_paragraph_bounds_hash_and_empty_roles(self):
        with tempfile.TemporaryDirectory() as folder:
            work, _ = self.make_preparation(Path(folder).resolve())
            valid = copy.deepcopy(self.proposal)
            # JSON Schema integers include numerically integral JSON numbers.
            self.proposal["text_roles"][0]["occurrences"][0]["paragraph_index"] = 2.0
            self.assertTrue(validator.validate(self.proposal, work_path=work)["valid"])
            for changes in ({"paragraph_index": 3}, {"paragraph_index": 1},
                            {"paragraph_sha256": digest(b"quiet.")}):
                self.proposal = copy.deepcopy(valid)
                self.proposal["text_roles"][0]["occurrences"][0].update(changes)
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    validator.validate(self.proposal, work_path=work)
            self.proposal["text_roles"] = []
            self.assertTrue(validator.validate(self.proposal, work_path=work)["valid"])
        repeated = validator.paragraphs(b"Repeat.\n\nRepeat.\n")
        self.assertEqual([p["paragraph_index"] for p in repeated], [1, 2])
        self.assertEqual(repeated[0]["paragraph_sha256"], repeated[1]["paragraph_sha256"])

    def test_catalog_cli_is_standalone_and_requires_ready_verified_preparation(self):
        with tempfile.TemporaryDirectory() as folder:
            work, source = self.make_preparation(Path(folder).resolve())
            before = {p: p.read_bytes() for p in work.parent.rglob("*") if p.is_file()}
            command = [sys.executable, "-B", str(SKILL / "scripts/validate_proposal.py"),
                       "--work", str(work), "--list-paragraphs"]
            result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            catalog = json.loads(result.stdout)
            self.assertEqual(catalog["contract"], "interior-design-paragraphs/1")
            occurrence = self.proposal["text_roles"][0]["occurrences"][0]
            paragraph = catalog["units"][1]["paragraphs"][1]
            self.assertEqual(paragraph["paragraph_sha256"], occurrence["paragraph_sha256"])
            self.assertEqual(before, {p: p.read_bytes() for p in before})
            source.write_bytes(b"Changed source")
            with self.assertRaisesRegex(ValueError, "Original source changed"):
                validator.paragraph_catalog(work)

    def test_old_proposal_contract_requires_regeneration(self):
        for version in (1, 2):
            self.proposal.update(contract=f"interior-design-proposal/{version}", schema_version=version)
            with self.subTest(version=version), self.assertRaises(ValueError):
                validator.validate(self.proposal)

    def test_prepared_evidence_cannot_claim_another_unit_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            work, _ = self.make_preparation(Path(folder).resolve())
            self.proposal["evidence"][0]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "exact bound unit"):
                validator.validate(self.proposal, work_path=work)


if __name__ == "__main__":
    unittest.main()
