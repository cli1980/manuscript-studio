"""Classification proposals are source-bound suggestions, never metadata writes."""

import copy
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from workflow.src.analysis import ManuscriptAnalysisPhase


class SubjectProposalTests(unittest.TestCase):
    def setUp(self):
        self.phase = ManuscriptAnalysisPhase()
        self.phase.root = Path(__file__).resolve().parents[2] / "plugins/manuscript-studio"
        self.sources = {"chapter-one": "He returned to London, remembering the fictional city of Lantern Bay."}
        term = {"label": "returning home", "confidence": "medium", "rationale": "A recurring source-grounded theme.",
                "evidence": [{"chapter_id": "chapter-one", "locator": "Opening paragraph",
                              "quote": "He returned to London"}]}
        self.proposals = {
            "bisac_subjects": {"status": "proposed", "reason": None, "items": [
                {**copy.deepcopy(term), "label": "Fiction / General", "code": None,
                 "scheme_version": None, "reference": None}]},
            "thema_subjects": {"status": "proposed", "reason": None, "items": [
                {**copy.deepcopy(term), "label": "Fiction: general and literary", "code": None,
                 "scheme_version": None, "reference": None}]},
            "keywords": {"status": "proposed", "reason": None, "items": [copy.deepcopy(term)]},
            "place_subjects": {"status": "proposed", "reason": None, "items": [
                {**copy.deepcopy(term), "label": "London", "kind": "real"},
                {**copy.deepcopy(term), "label": "Lantern Bay", "kind": "fictional",
                 "evidence": [{"chapter_id": "chapter-one", "locator": "Opening paragraph",
                               "quote": "the fictional city of Lantern Bay"}]}]},
        }

    def test_schema_and_source_bound_proposals_allow_unresolved_codes_and_distinct_place_kinds(self):
        Draft202012Validator.check_schema(self.phase.analysis_subject_schema())
        self.phase.validate_subject_proposals(self.proposals, self.sources)
        self.assertIsNone(self.proposals["bisac_subjects"]["items"][0]["code"])
        for key in ("bisac_subjects", "thema_subjects", "keywords", "place_subjects"):
            for status in ("undetermined", "not_applicable"):
                proposals = copy.deepcopy(self.proposals)
                proposals[key] = {"status": status, "reason": "No sufficiently supported term.", "items": []}
                self.phase.validate_subject_proposals(proposals, self.sources)

    def test_codes_require_syntax_version_and_reference_but_are_not_catalogue_certification(self):
        for key, code in (("bisac_subjects", "FIC000000"), ("thema_subjects", "FBA")):
            proposals = copy.deepcopy(self.proposals)
            item = proposals[key]["items"][0]
            item.update(code=code, scheme_version="Synthetic catalogue edition", reference="Fixture catalogue row")
            self.phase.validate_subject_proposals(proposals, self.sources)
            for field in ("scheme_version", "reference"):
                bad = copy.deepcopy(proposals)
                bad[key]["items"][0][field] = None
                with self.assertRaisesRegex(ValueError, "Analysis subject proposals"):
                    self.phase.validate_subject_proposals(bad, self.sources)

    def test_missing_unassessed_forged_duplicate_or_malformed_proposals_are_rejected(self):
        for mutation in ("absent", "missing-group", "pending", "unexplained", "empty-proposed", "unproposed-items",
                         "blank-label", "bad-confidence", "unknown-unit", "forged-quote", "blank-quote",
                         "no-evidence", "bad-bisac-code", "thema-qualifier", "missing-place-kind", "duplicate"):
            with self.subTest(mutation=mutation):
                proposals = copy.deepcopy(self.proposals)
                item = proposals["keywords"]["items"][0]
                if mutation == "absent":
                    proposals = None
                elif mutation == "missing-group":
                    proposals.pop("place_subjects")
                elif mutation == "pending":
                    proposals["keywords"]["status"] = "pending"
                elif mutation == "unexplained":
                    proposals["place_subjects"] = {"status": "undetermined", "reason": " ", "items": []}
                elif mutation == "empty-proposed":
                    proposals["keywords"]["items"] = []
                elif mutation == "unproposed-items":
                    proposals["keywords"].update(status="not_applicable", reason="No supported terms.")
                elif mutation == "blank-label":
                    item["label"] = " "
                elif mutation == "bad-confidence":
                    item["confidence"] = "verified"
                elif mutation == "unknown-unit":
                    item["evidence"][0]["chapter_id"] = "outside-source"
                elif mutation == "forged-quote":
                    item["evidence"][0]["quote"] = "He never returned."
                elif mutation == "blank-quote":
                    item["evidence"][0]["quote"] = " "
                elif mutation == "no-evidence":
                    item["evidence"] = []
                elif mutation in ("bad-bisac-code", "thema-qualifier"):
                    key = "bisac_subjects" if mutation == "bad-bisac-code" else "thema_subjects"
                    proposals[key]["items"][0].update(
                        code="FIC123" if mutation == "bad-bisac-code" else "1DBK",
                        scheme_version="Fixture edition", reference="Fixture catalogue row")
                elif mutation == "missing-place-kind":
                    proposals["place_subjects"]["items"][0].pop("kind")
                elif mutation == "duplicate":
                    proposals["keywords"]["items"].append({**copy.deepcopy(item), "label": "RETURNING HOME"})
                with self.assertRaisesRegex(ValueError, "Analysis subject proposal"):
                    self.phase.validate_subject_proposals(proposals, self.sources)
