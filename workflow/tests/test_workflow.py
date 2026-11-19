"""Run: python -m unittest workflow.tests.test_workflow -v."""

import json
import re
import contextlib
import copy
import io
import importlib.util
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from pathlib import Path

from ..src import cli, prepared, registry
from ..src.engine import Engine, WorkflowError, result_schema
from ..src.execution import ExecutionProfile
from ..src.runtime import CodexRuntime, Request
from ..src.service import WorkflowService
from ..src.storage import digest, now
from ..src.translation import TranslationEngine
from ..src import document_adapters
from . import run_e2e
from . import monitor_performance
from .test_execution import profile_data
from .interior_fixture import apply_target, proposal_for
from .analysis_fixture import analyze, analysis_context
from .inline_intake_fixture import inline_intake_templates

TRANSLATION = "literary-translation-v1"
FORMATTING = "manuscript-formatting-v1"
RESULT_SCHEMA = result_schema(["map_exceptions", "translation_issue", "chapter_sanity", "continuation", "question"])


def result(outcome="completed", **fields):
    return dict(outcome=outcome, message="Saved operation result.", state_path=None,
                work_record=None, output_path=None, gate=None, review_path=None,
                binding_path=None) | fields


class ScriptedRuntime:
    """A deterministic test double, never presented as a model translation."""

    def __init__(self, action, *, analysis_action=analyze):
        self.action = action
        self.analysis_action = analysis_action

    def run(self, request, on_event, on_thread):
        on_thread("test-thread")
        on_event("test.turn", {"model": request.model})
        if self.analysis_action and '{\n  "stage"' in request.prompt and analysis_context(request)["stage"] == "analysis":
            return self.analysis_action(request)
        return self.action(request)


class MetadataHelperTests(unittest.TestCase):
    def test_concurrent_helpers_keep_their_contract_and_restore_the_module_alias(self):
        contracts = [object() for _ in range(16)]
        absent = object()
        original = sys.modules.get("validate_preparation", absent)

        def import_helper(path):
            time.sleep(0.01)
            return sys.modules.get("validate_preparation")

        try:
            with patch.object(prepared, "module_at", side_effect=import_helper), ThreadPoolExecutor(4) as pool:
                loaded = list(pool.map(lambda contract: prepared.load_metadata_helper(Path("unused"), contract), contracts))
            self.assertEqual(loaded, contracts)
            self.assertIs(sys.modules.get("validate_preparation", absent), original)
        finally:
            if original is absent:
                sys.modules.pop("validate_preparation", None)
            else:
                sys.modules["validate_preparation"] = original


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.enterContext(inline_intake_templates(self.base))
        self.source = self.base / "original.md"
        self.source.write_bytes("# 故事\n\n他回来了。\n".encode())
        self.service = WorkflowService(self.base / "server with spaces", owner="tester")
        self.addCleanup(self.service.close)
        self.engine = None
        self.addCleanup(lambda: self.engine and self.engine.close())
        self.new_engine()

    def new_engine(self, **options):
        """Each upload creates a new work; the engine is opened with that work's library."""
        if self.engine:
            self.engine.close()
        self.run_id = self.service.create_run(TRANSLATION, upload=self.source, manuscript_language="zh", **options)
        row = self.service._run_row(self.run_id)
        self.work_id = row["work_id"]
        self.engine = Engine.open(Path(row["path"]), library=self.service.library(self.work_id))
        self.workspace = self.engine.workspace
        return self.engine

    def reopen(self):
        self.engine.close()
        self.engine = Engine.open(Path(self.service._run_row(self.run_id)["path"]),
                                  library=self.service.library(self.work_id))
        self.workspace = self.engine.workspace
        return self.engine

    def write(self, relative, content):
        path = self.workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, indent=2) + "\n"
        path.write_bytes(content.encode())
        return relative

    def preparation(self, request):
        source = self.engine.root / "input" / self.engine.state()["source_name"]
        content = source.read_bytes()
        parts = getattr(self, "parts", [content.decode()])
        # Every prepared revision starts with exactly one front-matter unit (here the title heading).
        units = [("front-matter", "front_matter", "# 故事\n")] + [
            ("story" if len(parts) == 1 else f"chapter-{index}", "standalone" if len(parts) == 1 else "chapter", part)
            for index, part in enumerate(parts, 1)]
        chapters = [{
            "chapter_id": chapter_id, "order": order, "source_number": None, "title": "故事", "role": role,
            "file": f"chapters/{order:04d}.md", "sha256": digest(text.encode()),
            "source_spans": [{"source_id": "original", "locator": f"Source unit {order}"}], "status": "verified",
        } for order, (chapter_id, role, text) in enumerate(units, 1)]
        parts = [text for _, _, text in units]
        manifest = {
            "schema_version": 1, "work_id": self.work_id, "revision": "r0001", "status": "verified",
            "created_at": now(), "sources": [{
                "source_id": "original", "locator": str(source), "format": "markdown",
                "identity": {"kind": "sha256", "value": digest(content)},
            }],
            "scope": {"kind": "whole_work", "chapter_ids": [c["chapter_id"] for c in chapters]},
            "chapters": chapters, "assets": [],
            "extraction": {"tool": "test", "method": "Exact fixture copy", "normalization_notes": []},
            "verification": {"performed_by": "test", "verified_at": now(),
                             "coverage_complete": True, "issues": []},
        }
        work = {
            "schema_version": 2, "work_id": self.work_id, "record_revision": 1, "updated_at": now(),
            "metadata": {"title": "Story", "subtitle": None, "contributors": [], "original_language": None, "manuscript_language": getattr(self, "language", "zh"), "work_type": "fiction", "form": None, "genres": [], "audience": None, "keywords": [], "description": None, "edition": {"label": None, "status": None}, "series": {"name": None, "position": None, "relationship": None}, "extent": None},
            "metadata_provenance": {},
            "discovery": {"location_kind": "file", "location": str(source), "recursive": False,
                          "selection_status": "confirmed", "notes": []},
            "preparation": {"status": "ready", "current_revision": "r0001", "blockers": []},
            "workflows": {name: {"status": "not_started", "basis_revision": None, "scope": None,
                                 "operation": None, "state_locator": None, "updated_at": None}
                          for name in ("literary-editing", "literary-translation",
                                       "literary-agent-querying")},
        }
        for chapter, part in zip(chapters, parts):
            self.write(f"prepared/{self.work_id}/revisions/r0001/" + chapter["file"], part)
        self.write(f"prepared/{self.work_id}/revisions/r0001/manifest.json", manifest)
        return result(work_record=self.write(f"prepared/{self.work_id}/work.json", work))

    def prepare(self):
        """Prepare, confirm metadata and the translation brief on the front matter, and translate the front matter."""
        self.engine.advance(ScriptedRuntime(self.preparation))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm metadata")
        self.engine.advance(ScriptedRuntime(analyze))
        if self.engine.state()["workflow"] == "literary-translation":
            self.approve_brief()
            self.translate_chapter()

    def test_preparation_rejects_generated_html_before_metadata_or_manuscript_approval(self):
        self.parts = ["# Story\n\nFirst paragraph.\n\n<br />\n\nSecond paragraph.\n"]
        with self.assertRaisesRegex(ValueError, r"story .*:line 5: Raw HTML"):
            self.engine.advance(ScriptedRuntime(self.preparation))
        state = self.engine.state()
        self.assertEqual(state["stage"], "prepare")
        self.assertIsNone(state["prepared"])
        self.assertIsNone(state["metadata_approval"])
        self.assertIsNone(state["gate"])

    def test_language_can_be_unknown_until_preparation_and_sets_passage_defaults(self):
        for language, settings, maximum in (("en", None, 800), ("zh", None, 1500),
                                             ("en", {"passage_size": 1200}, 1200)):
            with self.subTest(language=language, settings=settings):
                self.engine.close()
                self.language = language  # Scripted preparation result, not a language-detection benchmark.
                self.source.write_bytes(b"# Story\n\nHe returned home.\n" if language == "en" else
                                        "# 故事\n\n他回来了。\n".encode())
                self.run_id = self.service.create_run(TRANSLATION, upload=self.source, settings=settings)
                row = self.service._run_row(self.run_id)
                self.work_id = row["work_id"]
                self.engine = Engine.open(Path(row["path"]), library=self.service.library(self.work_id))
                self.workspace = self.engine.workspace
                initial = self.engine.state()
                self.assertIsNone(initial["manuscript_language"])
                self.assertIsNone(self.service.get_work(self.work_id)["manuscript_language"])
                self.assertIsNone(self.engine.passage_limit(initial))
                state = self.engine.advance(ScriptedRuntime(self.preparation))
                self.assertEqual(state["manuscript_language"], language)
                self.assertEqual(self.engine.passage_limit(state),
                                 {"max": maximum, "unit": "words" if language == "en" else "cjk_chars"})
                self.engine.reply(state["gate"]["id"], "confirm metadata")
                self.service.get_run(self.run_id)  # Refresh the index from the ready preparation.
                self.service.reindex()
                self.assertEqual(self.service.get_work(self.work_id)["manuscript_language"], language)

    def samples_sheet(self, revision="1", original=True):
        rows = ([{"label": "Location", "value": "story, paragraph 1"}]
                + ([{"label": "Original", "value": "他回来了。"}] if original else [])
                + [{"label": "A", "value": "He came back."}, {"label": "About A", "value": "Close to the source."},
                   {"label": "B", "value": "He was back."}, {"label": "About B", "value": "Freer rhythm."}])
        return {
            "schema_version": "1.0", "sheet_id": "brief-samples", "revision": revision, "title": "Translation samples",
            "bindings": [{"label": "Samples", "value": "translation/brief-samples.md"}],
            "decisions": [
                {"id": "choose-a", "command": "choose A", "label": "A", "requires_note": False, "effect": "resolve"},
                {"id": "choose-b", "command": "choose B", "label": "B", "requires_note": False, "effect": "resolve"},
                {"id": "none", "command": "none of these", "label": "None of these", "requires_note": True,
                 "effect": "reopen"},
            ],
            "items": [{"id": "S1", "summary": "story, paragraph 1", "details": rows, "status": "pending",
                       "status_label": "Pending", "allowed_decisions": ["choose-a", "choose-b", "none"],
                       "dependencies": [], "response": None}],
            "gate": {"status": "awaiting-choices", "closure_required": False, "final_closure": "not-required",
                     "ready_state": "not-ready"},
            "presentation": {"mode": "all", "note_label": "Reasons", "note_placeholder": "Optional",
                             "submit_label": "Submit"},
            "submission": {"instruction": "Choose one variant per sample.", "rules": ["Decide every sample."],
                           "closure_command": "confirm final closure", "closure_label": "Confirm"},
        }

    def samples_gate(self, request, original=True):
        self.write("translation/glossary.md", "| 故事 | Story | title | provisional |\n")
        self.write("translation/voice.md", "## Narrator · story · home\nPlain, restrained. Status: provisional\n")
        return result("needs_human_input", gate="brief_samples", message="Choose the sample variants.",
                      binding_path=self.write("translation/brief-samples.md", "S1: 他回来了。 A / B\n"),
                      review_path=self.write("translation/brief-samples.json", self.samples_sheet(original=original)))

    def brief_gate(self, request):
        self.write("translation/brief-samples.md", "S1: 他回来了。 A accepted (keeps the restraint); B rejected\n")
        return result("needs_human_input", gate="translation_brief", message="Proposed glossary, voice, and samples.")

    def approve_brief(self):
        if self.engine.state()["stage"] == "analysis":
            self.engine.advance(ScriptedRuntime(analyze))
        self.engine.advance(ScriptedRuntime(self.samples_gate))
        self.engine.reply(self.engine.state()["gate"]["id"], "S1 choose A: keeps the restraint")
        self.engine.advance(ScriptedRuntime(self.brief_gate))
        self.engine.reply(self.engine.state()["gate"]["id"], "approve brief")

    def gate_receipts(self):
        # Receipts for the story chapter (metadata review and the front matter are covered by prepare()).
        return [r for r in self.engine.state()["receipts"]
                if r["gate"]["kind"] != "metadata_review" and r["gate"].get("chapter_id") != "front-matter"]

    def test_analysis_handoff_is_frozen_provisional_and_survives_reopen(self):
        self.engine.advance(ScriptedRuntime(self.preparation))
        self.engine.edit_metadata("/keywords", ["author-supplied keyword"], gate_id=self.engine.state()["gate"]["id"],
                                  reason="Preserve confirmed discovery terms")
        state = self.engine.reply(self.engine.state()["gate"]["id"], "confirm metadata")
        self.assertEqual((state["stage"], state["status"]), ("analysis", "READY"))
        receipts = copy.deepcopy(state["receipts"])
        metadata_before = self.engine._work_path(state).read_bytes()
        state = self.engine.advance(ScriptedRuntime(analyze))
        self.assertEqual((state["stage"], state["status"]), ("brief", "READY"))
        self.assertEqual(state["receipts"], receipts)  # No manufactured analysis approval.
        analysis = copy.deepcopy(state["analysis"])
        self.assertEqual(analysis["approval_status"], "provisional")
        self.assertEqual(len(analysis["coverage"]), len(state["chapters"]))
        self.assertEqual(len(analysis["artifacts"]), 5)
        self.assertEqual(self.engine._work_path(state).read_bytes(), metadata_before)
        self.assertEqual(set(analysis["subject_proposals"]),
                         {"bisac_subjects", "thema_subjects", "keywords", "place_subjects"})
        self.assertEqual(analysis["subject_proposals"]["keywords"]["items"][0]["label"], "returning home")
        self.assertIsNone(analysis["subject_proposals"]["bisac_subjects"]["items"][0]["code"])
        self.reopen()
        handoff = json.loads(self.prompt(self.engine.state())[self.prompt(self.engine.state()).index('{\n  "stage"'):])[
            "manuscript_analysis"]
        self.assertEqual(handoff["manifest"]["sha256"], analysis["manifest"]["sha256"])
        self.assertEqual(handoff["subject_proposals"], analysis["subject_proposals"])
        self.assertTrue(handoff["current_text_matches_source"])
        files = self.engine.delivery_files(self.engine.state())
        for artifact in [analysis["manifest"], *analysis["artifacts"].values()]:
            self.assertEqual(digest(files[artifact["path"]]), artifact["sha256"])
        self.assertEqual(json.loads(files[analysis["manifest"]["path"]])["subject_proposals"],
                         analysis["subject_proposals"])
        forged = copy.deepcopy(self.engine.state())
        forged["analysis"]["subject_proposals"]["keywords"]["items"][0]["label"] = "Unbound replacement"
        with self.assertRaisesRegex(ValueError, "subject proposals differ"):
            self.engine.verify_analysis(forged)
        ledger = analysis["artifacts"]["ledger"]
        self.write(ledger["path"], "Changed after completion")
        with self.assertRaisesRegex(ValueError, "analysis changed"):
            self.engine.advance(ScriptedRuntime(self.samples_gate))

    def test_analysis_rejects_incomplete_stale_forged_or_changed_packages(self):
        mutations = ("missing-unit", "wrong-order", "stale-source", "bad-quote", "outside-path",
                     "missing-subjects", "forged-subject-quote",
                     "bad-hash", "empty-file", "failed-audit", "claimed-approval", "metadata-edit")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.new_engine()
                self.engine.advance(ScriptedRuntime(self.preparation))
                self.engine.reply(self.engine.state()["gate"]["id"], "confirm metadata")

                def malformed(request):
                    response = analyze(request)
                    manifest = json.loads(self.engine.file(response["state_path"]).read_bytes())
                    if mutation == "missing-unit":
                        manifest["coverage"].pop()
                    elif mutation == "wrong-order":
                        manifest["coverage"].reverse()
                    elif mutation == "stale-source":
                        manifest["basis"]["source_sha256"] = "0" * 64
                    elif mutation == "bad-quote":
                        manifest["coverage"][0]["evidence"][0]["quote"] = "Invented source quote"
                    elif mutation == "missing-subjects":
                        manifest.pop("subject_proposals")
                    elif mutation == "forged-subject-quote":
                        manifest["subject_proposals"]["keywords"]["items"][0]["evidence"][0]["quote"] = "Invented keyword"
                    elif mutation == "outside-path":
                        manifest["artifacts"]["ledger"]["path"] = "../outside.md"
                    elif mutation == "bad-hash":
                        manifest["artifacts"]["ledger"]["sha256"] = "0" * 64
                    elif mutation == "empty-file":
                        artifact = manifest["artifacts"]["ledger"]
                        self.write(artifact["path"], "")
                        artifact["sha256"] = digest(b"")
                    elif mutation == "failed-audit":
                        manifest["evidence_audit"] = "failed"
                    elif mutation == "claimed-approval":
                        manifest["approval_status"] = "approved"
                    elif mutation == "metadata-edit":
                        work = json.loads(self.engine._work_path(self.engine.state()).read_bytes())
                        work["metadata"]["title"] = "Unauthorized analysis metadata edit"
                        self.write(self.engine.state()["prepared"]["work_record"], work)
                    self.write(response["state_path"], manifest)
                    return response

                with self.assertRaisesRegex(ValueError, "[Aa]nalysis"):
                    self.engine.advance(ScriptedRuntime(malformed, analysis_action=None))
                self.assertIsNone(self.engine.state()["analysis"])
                self.assertEqual((self.engine.state()["stage"], self.engine.state()["status"]), ("analysis", "FAILED"))

    def test_analysis_restart_creates_new_revision_and_blocks_partial_reading(self):
        self.engine.advance(ScriptedRuntime(self.preparation))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm metadata")
        self.engine.advance(ScriptedRuntime(analyze))
        old = copy.deepcopy(self.engine.state()["analysis"])
        state = self.engine.restart_stage("analysis", reason="Refresh the reading")
        self.assertIsNone(state["analysis"])
        self.assertIsNotNone(state["metadata_approval"])
        self.assertFalse((self.workspace / old["manifest"]["path"]).exists())
        state = self.engine.advance(ScriptedRuntime(
            lambda request: result("blocked", message="Partial reading; ending unavailable."), analysis_action=None))
        self.assertEqual((state["status"], state["stage"], state["analysis"]), ("BLOCKED", "analysis", None))
        self.engine.retry()
        state = self.engine.advance(ScriptedRuntime(analyze))
        self.assertNotEqual(state["analysis"]["analysis_id"], old["analysis_id"])
        self.assertEqual(state["stage"], "brief")

    def test_editing_analysis_precedes_pass_selection_and_marks_changed_text(self):
        state = self.start_editing()
        self.assertEqual(state["gate"]["kind"], "pass_choice")
        self.assertIsNotNone(state["analysis"])
        manifest = state["analysis"]["manifest"]
        self.choose("run line")
        state = self.engine.state()
        handoff = self.engine.analysis_handoff(state)
        self.assertTrue(handoff["current_text_matches_source"])
        path = next(iter(state["manuscript"].values()))
        self.write(path, self.engine.file(path).read_text(encoding="utf-8") + "\nChanged text.\n")
        handoff = self.engine.analysis_handoff(state)
        self.assertFalse(handoff["current_text_matches_source"])
        self.assertEqual(handoff["manifest"], manifest)
        self.assertEqual(handoff["basis_kind"], "prepared-source")
        self.assertEqual(handoff["approval_status"], "provisional")

    def prepare_v2(self, request):
        response = self.preparation(request)
        path = self.workspace / response["work_record"]
        work = json.loads(path.read_text(encoding="utf-8"))
        work["metadata"]["genres"] = ["Historical fiction"]
        self.write(response["work_record"], work)
        return response

    def test_metadata_review_gate_precedes_translation(self):
        self.engine.advance(ScriptedRuntime(self.preparation))
        state = self.engine.state()
        gate = state["gate"]
        self.assertEqual((state["stage"], state["status"], gate["kind"]), ("metadata", "WAITING_FOR_HUMAN", "metadata_review"))
        self.assertEqual(gate["chapter_id"], "front-matter")  # Metadata review belongs to the front-matter unit.
        self.assertEqual(gate["record_revision"], 1)
        self.assertIn('/title: "Story"', gate["message"])
        self.assertIsNone(state["metadata_approval"])
        with self.assertRaisesRegex(ValueError, "WAITING_FOR_HUMAN"):
            self.engine.advance(ScriptedRuntime(self.translation))
        with self.assertRaisesRegex(ValueError, "confirm metadata"):
            self.engine.reply(gate["id"], "looks fine")
        self.assertEqual(self.engine.state()["receipts"], [])
        state = self.engine.reply(gate["id"], "confirm metadata")
        self.assertEqual((state["stage"], state["status"]), ("analysis", "READY"))  # Shared analysis precedes the brief.
        self.assertIsNone(state["next_input"])
        approval = state["metadata_approval"]
        self.assertEqual((approval["record_revision"], approval["sha256"], approval["decision_source"]),
                         (1, gate["binding"]["sha256"], "human"))
        self.assertEqual(approval["receipt_id"], state["receipts"][0]["id"])
        self.assertIn('"metadata_approval"', self.prompt(state))
        self.assertEqual(self.engine.store.events()[-1]["kind"], "metadata.confirmed")
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.reply(gate["id"], "confirm metadata")
        # Confirmation publishes the shared record to the work library with the receipt.
        head = self.service.library(self.work_id).head("work.json")
        self.assertEqual((head["run_id"], head["stage"], head["receipts"]), (state["id"], "metadata", [approval["receipt_id"]]))
        self.assertEqual(state["library_heads"]["work.json"], head["id"])

    def test_untitled_source_is_prepared_with_a_supplied_title_for_review(self):
        def untitled(request):
            response = self.preparation(request)
            revision = self.workspace / f"prepared/{self.work_id}/revisions/r0001"
            manifest = json.loads((revision / "manifest.json").read_text(encoding="utf-8"))
            front = manifest["chapters"][0]
            self.write(f"prepared/{self.work_id}/revisions/r0001/{front['file']}", "# Story\n")
            front.update(sha256=digest("# Story\n".encode()), source_spans=[],
                         supplied_title={"text": "Story", "basis": "metadata", "evidence": "metadata.title"})
            self.write(f"prepared/{self.work_id}/revisions/r0001/manifest.json", manifest)
            return response

        self.assertIn("a missing title does not", self.prompt(self.engine.state()))
        state = self.engine.advance(ScriptedRuntime(untitled))
        self.assertEqual((state["stage"], state["status"]), ("metadata", "WAITING_FOR_HUMAN"))
        self.assertEqual(state["chapters"][0]["supplied_title"]["basis"], "metadata")
        self.assertIn('title heading "Story" was supplied from metadata (metadata.title)', state["gate"]["message"])

    def prompt(self, state):
        return self.engine.stage_prompt(state, self.engine.stage_def(state))

    def test_translation_brief_is_reviewed_with_the_front_matter(self):
        self.engine.advance(ScriptedRuntime(self.preparation))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm metadata")
        self.engine.advance(ScriptedRuntime(analyze))
        for action, error in ((lambda r: result(), "completes when the user approves"),
                              (lambda r: result("needs_human_input", gate="translation_brief"), "sample choices"),
                              (lambda r: self.samples_gate(r, original=False), "needs an 'Original' row")):
            with self.assertRaisesRegex(ValueError, error):
                self.engine.advance(ScriptedRuntime(action))
            self.engine.retry()
        # The sample poll: one variant per sample, with reasons; a complete resolving submission closes it.
        state = self.engine.advance(ScriptedRuntime(self.samples_gate))
        self.assertEqual((state["gate"]["kind"], state["gate"]["chapter_id"]), ("brief_samples", "front-matter"))
        state = self.engine.reply(state["gate"]["id"], "S1 choose A: keeps the restraint")
        self.assertEqual((state["stage"], state["status"]), ("brief", "READY"))
        self.assertTrue(state["next_input"]["parsed"]["implied_closure"])
        self.assertIn("brief_samples", state["approvals"])
        self.assertEqual(state["next_input"]["parsed"]["dispositions"][0]["note"], "keeps the restraint")
        state = self.engine.advance(ScriptedRuntime(self.brief_gate))
        gate = state["gate"]
        self.assertEqual((state["stage"], gate["kind"], gate["chapter_id"]), ("brief", "translation_brief", "front-matter"))
        self.assertEqual([d["path"] for d in gate["documents"]],
                         ["translation/glossary.md", "translation/voice.md", "translation/brief-samples.md"])
        self.assertEqual(self.engine.gate_commands(state, gate), ["approve brief"])
        self.assertTrue(self.engine.summary(state)["gate_review"])
        # Corrections are feedback for the agent; they do not approve the brief.
        state = self.engine.reply(gate["id"], "Render 故事 as Tale.")
        self.assertEqual((state["stage"], state["status"], state["next_input"]["parsed"]["type"]), ("brief", "READY", "feedback"))
        self.assertEqual(state["front_matter_approvals"], {})
        gate = self.engine.advance(ScriptedRuntime(self.brief_gate))["gate"]
        original = (self.workspace / "translation/voice.md").read_text(encoding="utf-8")
        self.write("translation/voice.md", "Changed after presentation.\n")
        with self.assertRaisesRegex(ValueError, "Review changed"):
            self.engine.reply(gate["id"], "approve brief")
        self.write("translation/voice.md", original)
        state = self.engine.reply(gate["id"], "approve brief")
        # Approval completes the stage without another agent turn; the approved files seed the chapter stage.
        self.assertEqual((state["stage"], state["status"], state["next_input"]), ("translate", "READY", None))
        approval = state["front_matter_approvals"]["translation_brief"]
        self.assertEqual((approval["documents"], approval["receipt_id"]), (gate["documents"], state["receipts"][-1]["id"]))
        self.assertEqual(state["continuity_seed"]["translation/glossary.md"]["sha256"], gate["documents"][0]["sha256"])
        self.assertEqual(state["continuity_seed"]["translation/brief-samples.md"]["sha256"], gate["documents"][2]["sha256"])
        self.assertIn('"translation_brief_approval"', self.prompt(state))
        state = self.engine.restart_stage("brief", reason="Revisit the brief")
        self.assertEqual((state["stage"], state["status"], state["front_matter_approvals"]), ("brief", "READY", {}))

    def test_metadata_edits_are_versioned_and_rebind_the_gate(self):
        self.engine.advance(ScriptedRuntime(self.prepare_v2))
        first = self.engine.state()["gate"]
        self.assertIn('/genres: ["Historical fiction"] [no provenance]', first["message"])
        self.assertIn("/subtitle", first["message"].split("Unknown: ")[1])
        with self.assertRaisesRegex(ValueError, "locked"):
            self.engine.edit_metadata("/manuscript_language", "fr", gate_id=first["id"])
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.edit_metadata("/genres", ["Literary fiction"], gate_id="old-gate")
        state = self.engine.edit_metadata("/genres", ["Literary fiction"], reason="Author correction",
                                          gate_id=first["id"])
        gate = state["gate"]
        self.assertNotEqual(gate["id"], first["id"])
        self.assertEqual(gate["record_revision"], 2)
        self.assertIn('/genres: ["Literary fiction"] [user_edit, confirmed]', gate["message"])
        work_path = self.engine.file(state["prepared"]["work_record"])
        work = json.loads(work_path.read_text(encoding="utf-8"))
        self.assertEqual(work["metadata_provenance"]["/genres"]["rationale"], "Author correction")
        history = list((work_path.parent / "metadata-history").glob("1-*.json"))
        self.assertEqual(len(history), 1)
        self.assertEqual(json.loads(history[0].read_text(encoding="utf-8"))["metadata"]["genres"], ["Historical fiction"])
        self.assertEqual(self.engine.store.content(first["binding"]), history[0].read_bytes())
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.reply(first["id"], "confirm metadata")
        value = self.base / "title.json"
        value.write_text('"Corrected title"', encoding="utf-8")
        from ..src import cli
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = cli.main(["--server-root", str(self.service.root), "metadata", self.run_id, "--gate", gate["id"],
                             "--field", "/title", "--value-file", str(value)])
        self.assertEqual(code, 0)
        self.assertIn('/title: "Corrected title"', output.getvalue())
        state = self.engine.state()
        self.assertEqual(state["gate"]["record_revision"], 3)
        self.assertEqual([e["kind"] for e in self.engine.store.events()].count("metadata.edited"), 2)
        with self.assertRaisesRegex(ValueError, "Stale metadata revision"):
            self.service.confirm_metadata(self.run_id, state["gate"]["id"], 2)
        self.service.confirm_metadata(self.run_id, state["gate"]["id"], 3)
        state = self.engine.state()
        self.assertEqual(state["metadata_approval"]["record_revision"], 3)
        self.assertIn("Corrected title", self.prompt(state))
        # Every inspected version is retained and can be read back.
        history = self.service.metadata_history(self.run_id)
        self.assertEqual([v["record_revision"] for v in history], [1, 2, 3])
        self.assertEqual(self.service.metadata_version(self.run_id, 2)["metadata"]["genres"], ["Literary fiction"])
        self.assertEqual(self.service.metadata_version(self.run_id, 1)["metadata"]["genres"], ["Historical fiction"])

    def test_metadata_edits_after_confirmation_are_history_only(self):
        self.engine.advance(ScriptedRuntime(self.prepare_v2))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm metadata")
        self.engine.advance(ScriptedRuntime(analyze))
        receipts = len(self.engine.state()["receipts"])
        with self.assertRaisesRegex(ValueError, "locked"):
            self.engine.edit_metadata("/manuscript_language", "fr")
        state = self.engine.edit_metadata("/genres", ["Literary fiction"], reason="Late correction")
        self.assertEqual((state["stage"], state["status"], state["gate"]), ("brief", "READY", None))
        self.assertEqual(state["metadata_approval"]["record_revision"], 1)  # No re-confirmation.
        self.assertEqual(len(state["receipts"]), receipts)
        self.assertEqual(state["metadata_versions"][-1]["actor"], "user")
        library = self.service.library(self.work_id)
        self.assertEqual(library.head("work.json")["stage"], "metadata_edit")
        self.assertEqual(json.loads(library.read(library.head("work.json")))["metadata"]["genres"], ["Literary fiction"])

        def agent_edit(request):
            path = self.engine.file(self.engine.state()["prepared"]["work_record"])
            work = json.loads(path.read_text(encoding="utf-8"))
            work["metadata"]["title"] = "Agent-found title"
            work["record_revision"] += 1
            path.write_text(json.dumps(work, ensure_ascii=False), encoding="utf-8")
            return self.samples_gate(request)

        state = self.engine.advance(ScriptedRuntime(agent_edit))
        self.assertEqual(state["metadata_versions"][-1]["actor"], "agent")
        self.assertIn("metadata.changed_by_agent", [e["kind"] for e in self.engine.store.events()])
        self.assertEqual(library.head("work.json")["stage"], "metadata_agent_edit")
        with self.assertRaisesRegex(ValueError, "Stale or unavailable"):
            self.engine.edit_metadata("/genres", [], gate_id=state["gate"]["id"])

    def test_external_metadata_change_requires_a_refreshed_gate(self):
        self.engine.advance(ScriptedRuntime(self.prepare_v2))
        gate = self.engine.state()["gate"]
        relative = self.engine.state()["prepared"]["work_record"]
        work = json.loads(self.engine.file(relative).read_text(encoding="utf-8"))
        work["metadata"]["title"] = "Edited outside the gate"
        self.write(relative, work)
        with self.assertRaisesRegex(ValueError, "Review changed"):
            self.engine.reply(gate["id"], "confirm metadata")
        with self.assertRaisesRegex(ValueError, "Metadata changed"):
            self.engine.edit_metadata("/genres", [], gate_id=gate["id"])
        self.engine.retry(refresh_gate=True)
        state = self.engine.advance(None)
        self.assertEqual((state["stage"], state["status"]), ("metadata", "WAITING_FOR_HUMAN"))
        self.assertNotEqual(state["gate"]["id"], gate["id"])
        self.assertIn("Edited outside the gate", state["gate"]["message"])
        self.engine.reply(state["gate"]["id"], "confirm metadata")
        self.assertEqual(self.engine.state()["stage"], "analysis")

    def test_editable_v2_metadata_does_not_change_prepared_source_identity(self):
        self.engine.advance(ScriptedRuntime(self.prepare_v2))
        state = self.engine.reply(self.engine.state()["gate"]["id"], "confirm metadata")
        relative = state["prepared"]["work_record"]
        work = json.loads(self.engine.file(relative).read_text(encoding="utf-8"))
        work["metadata"]["title"] = "Corrected title"
        work["metadata"]["genres"] = ["Literary fiction"]
        work["record_revision"] += 1
        self.write(relative, work)
        self.engine.verify(state)
        self.assertIn("Corrected title", self.prompt(state))
        work["metadata"]["manuscript_language"] = "fr"
        self.write(relative, work)
        with self.assertRaisesRegex(ValueError, "language metadata differs"):
            self.engine.verify(state)

    def sheet(self, revision="1", resolved=False):
        return {
            "schema_version": "1.0", "sheet_id": "map-story", "revision": revision,
            "title": "Passage map", "bindings": [{"label": "Chapter", "value": "story"}],
            "decisions": [
                {"id": "approve", "command": "approve", "label": "Approve", "requires_note": False, "effect": "resolve"},
                {"id": "revise", "command": "revise", "label": "Revise", "requires_note": True, "effect": "reopen"},
            ],
            "items": [{
                "id": "PM001", "summary": "One passage: complete story",
                "details": [{"label": "Original", "value": "他回来了。"}],
                "status": "resolved" if resolved else "pending", "status_label": "Reviewed" if resolved else "Pending",
                "allowed_decisions": ["approve", "revise"], "dependencies": [],
                "response": {"decision": "approve", "note": "", "date": now()} if resolved else None,
            }],
            "gate": {"status": "awaiting-approval", "closure_required": True,
                     "final_closure": "pending", "ready_state": "not-ready"},
            "presentation": {"mode": "all", "note_label": "Feedback", "note_placeholder": "Required for revision",
                             "submit_label": "Submit"},
            "submission": {"instruction": "Review this map.", "rules": ["Do not translate before closure."],
                           "closure_command": "confirm final closure", "closure_label": "Confirm"},
        }

    def write_map(self, exceptions=True, kind="special"):
        """The agent's internal passage map: one passage covering the chapter, optionally with one exception."""
        state = self.engine.state()
        chapter_id = self.engine.current_iteration(state)["chapter_id"]
        chapter = next(c for c in state["chapters"] if c["chapter_id"] == chapter_id)
        text = self.engine.store.content(state["prepared"]["files"][chapter["path"]]).decode("utf-8")
        count = len([block for block in re.split(r"\n\s*\n", text.strip()) if block.strip()])
        data = {"chapter_id": chapter_id, "passages": [{"id": "P1", "first_paragraph": 1, "last_paragraph": count}],
                "exceptions": [{"id": "PM001", "kind": kind, "first_paragraph": 1, "last_paragraph": 1,
                                "reason": "Keep the heading in its original form."}] if exceptions else []}
        return self.write(f"translation/maps/{chapter_id}.json", data)

    def map_gate(self, revision="1", resolved=False, kind="special"):
        return result(
            "needs_human_input", message="Review the passage-map exception.",
            gate="map_exceptions", state_path=self.write("translation/state.md", "Passage map pending.\n"),
            binding_path=self.write_map(kind=kind),
            review_path=self.write("translation/map-review.json", self.sheet(revision, resolved)),
        )

    def approve_map(self):
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        gate = self.engine.state()["gate"]["id"]
        self.engine.reply(gate, "PM001 approve")
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate("2", True)))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm final closure")

    def sanity_gate(self, request):
        return result(
            "needs_human_input", gate="chapter_sanity", message="He came back.\nNo textual changes proposed.",
            state_path=self.write("translation/sanity.md", "No textual changes proposed\n"),
            binding_path=self.write("translation/assembled.md", "He came back.\n"),
        )

    def translation(self, request):
        chapter_id = self.engine.current_iteration(self.engine.state())["chapter_id"]
        self.write("translation/glossary.md", f"# Glossary\nThrough {chapter_id}.\n")
        self.write("translation/voice.md", "# Voice\n")
        english = getattr(self, "english", {}).get(chapter_id, "Story\n" if chapter_id == "front-matter" else "He came back.\n")
        return result(state_path=self.write("translation/state.md", "Chapter finalized.\n"),
                      output_path=self.write(f"translation/translated_english/{chapter_id}.md", english))

    def translate_chapter(self, *, consistency=True):
        self.approve_map()
        self.engine.advance(ScriptedRuntime(self.sanity_gate))
        self.engine.reply(self.engine.state()["gate"]["id"], "approve chapter")
        state = self.engine.advance(ScriptedRuntime(self.translation))
        if consistency:
            self.finish_consistency()
        return self.engine.state()

    def consistency_gate(self, request=None, *, changes=None, revision="1", dispositions=None):
        state = self.engine.state()
        item = self.engine.current_iteration(state)
        context = self.engine.consistency_context(state, item)
        plan = {"chapters": {
            chapter["chapter_id"]: {"source_sha256": chapter["source_sha256"],
                                     "translation_sha256": chapter["translation"]["sha256"],
                                     "evidence": "Synthetic fixture: compared names, voice, and references."}
            for chapter in context["chapters"]}, "changes": changes or []}
        sheet = None
        if changes:
            sheet = self.sheet(revision)
            sheet.update(sheet_id="whole-book-consistency", title="Whole-book consistency", items=[])
            sheet["decisions"].append({"id": "reject", "command": "reject", "label": "Reject",
                                       "requires_note": False, "effect": "resolve"})
            for change in changes:
                response = (dispositions or {}).get(change["id"])
                sheet["items"].append({
                    "id": change["id"], "summary": change["reason"],
                    "details": [{"label": label, "value": change[key]} for label, key in (
                        ("Chapter", "chapter_id"), ("Original", "source_quote"), ("Before", "before"),
                        ("After", "after"), ("Reason", "reason"))],
                    "status": "resolved" if response else "pending", "status_label": "Reviewed" if response else "Pending",
                    "allowed_decisions": ["approve", "reject", "revise"], "dependencies": [],
                    "response": {"decision": response, "note": "", "date": now()} if response else None,
                })
        folder = context["plan_path"].rsplit("/", 1)[0]
        return result("needs_human_input", gate="translation_consistency",
                      message="Review whole-book fixes." if changes else "No inconsistencies found.",
                      state_path=self.write(folder + "/review.md", "Synthetic whole-book coverage.\n"),
                      binding_path=self.write(context["plan_path"], plan),
                      review_path=self.write(folder + "/sheet.json", sheet) if sheet else None)

    def consistency_apply(self, request=None):
        state = self.engine.state()
        item = self.engine.current_iteration(state)
        context = self.engine.consistency_context(state, item)
        review = context["review"]
        plan = json.loads(self.engine.store.content(review["plan"]))
        report = {"chapters": {}}
        for chapter in context["chapters"]:
            changes = [change for change in plan["changes"] if change["id"] in review["approved_ids"]
                       and change["chapter_id"] == chapter["chapter_id"]]
            if not changes:
                continue
            before = self.engine.store.content(chapter["translation"]).decode("utf-8")
            text = before
            for change in sorted(changes, key=lambda change: before.index(change["before"]), reverse=True):
                start = before.index(change["before"])
                text = text[:start] + change["after"] + text[start + len(change["before"]):]
            self.write(chapter["candidate_path"], text)
            report["chapters"][chapter["chapter_id"]] = {
                "source_sha256": chapter["source_sha256"], "output_sha256": digest(text.encode()),
                "evidence": "Synthetic fixture: source comparison confirms only the approved replacement."}
        self.write(context["report_path"], report)
        return result(state_path=self.write(context["plan_path"].rsplit("/", 1)[0] + "/review.md",
                                            "Approved fixes applied and re-verified.\n"))

    def finish_consistency(self):
        item = self.engine.current_iteration(self.engine.state())
        if item and item["chapter_id"] == "_whole":
            self.engine.advance(ScriptedRuntime(self.consistency_gate))
            self.engine.reply(self.engine.state()["gate"]["id"], "confirm consistency")
            self.engine.advance(ScriptedRuntime(self.consistency_apply))

    def complete_translation(self):
        """Prepare (including the front matter), then translate the story chapter."""
        self.prepare()
        self.translate_chapter()

    def finalize_translation(self):
        self.complete_translation()
        self.engine.accept(self.engine.state()["acceptance_id"], confirm_final=True)
        return self.engine.advance(None)

    def test_consistency_is_required_even_without_findings(self):
        self.prepare()
        self.translate_chapter(consistency=False)
        state = self.engine.state()
        self.assertEqual((state["stage"], state["status"]), ("translate", "READY"))
        self.assertEqual(self.engine.current_iteration(state)["chapter_id"], "_whole")
        summary = self.engine.summary(state)
        self.assertEqual(summary["progress"], {"completed": 2, "total": 2})
        self.assertFalse(next(a for a in self.engine.available_actions(state) if a["action"] == "accept")["enabled"])
        with self.assertRaisesRegex(ValueError, "separate review closure"):
            self.engine.advance(ScriptedRuntime(lambda r: result(state_path=self.write("translation/unreviewed.md", "Done"))))
        self.engine.retry()
        self.engine.advance(ScriptedRuntime(self.consistency_gate))
        gate = self.engine.state()["gate"]
        self.assertEqual((gate["kind"], gate["chapter_id"]), ("translation_consistency", "_whole"))
        self.assertEqual(self.engine.gate_commands(self.engine.state(), gate), ["confirm consistency"])
        self.engine.reply(gate["id"], "Please check recurring names again.")
        self.assertNotIn("translation_consistency", self.engine.state()["approvals"])
        self.engine.advance(ScriptedRuntime(self.consistency_gate))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm consistency")
        self.reopen()
        self.engine.advance(ScriptedRuntime(self.consistency_apply))
        self.assertEqual(self.engine.state()["status"], "WAITING_FOR_ACCEPTANCE")
        self.assertEqual(self.engine.summary(self.engine.state())["whole_book_status"], "completed")

    def consistency_fixes(self):
        return [
            {"id": "C001", "chapter_id": "story", "source_quote": "他回来了。",
             "before": "He came back.", "after": "He returned.", "reason": "Synthetic terminology correction."},
            {"id": "C002", "chapter_id": "front-matter", "source_quote": "故事",
             "before": "Story", "after": "Tale", "reason": "Synthetic title correction."},
        ]

    def test_consistency_promotes_only_approved_fixes_after_bound_reverification(self):
        self.prepare()
        self.translate_chapter(consistency=False)
        original_outputs = self.engine.state()["outputs"]
        fixes = self.consistency_fixes()
        self.engine.advance(ScriptedRuntime(lambda r: self.consistency_gate(r, changes=fixes)))
        gate = self.engine.state()["gate"]
        with self.assertRaisesRegex(ValueError, "missing: C002"):
            self.engine.reply(gate["id"], "C001 approve")
        with self.assertRaisesRegex(ValueError, "unresolved"):
            self.engine.reply(gate["id"], "confirm final closure")
        self.engine.reply(gate["id"], "C001 approve\nC002 reject")
        self.assertEqual(self.engine.state()["outputs"], original_outputs)
        self.engine.advance(ScriptedRuntime(lambda r: self.consistency_gate(
            r, changes=fixes, revision="2", dispositions={"C001": "approve", "C002": "reject"})))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm final closure")
        self.reopen()

        def extra_edit(request):
            response = self.consistency_apply(request)
            context = self.engine.consistency_context(self.engine.state(), self.engine.current_iteration(self.engine.state()))
            story = next(c for c in context["chapters"] if c["chapter_id"] == "story")
            self.write(story["candidate_path"], "He returned, smiling.\n")
            return response

        with self.assertRaisesRegex(ValueError, "exact approved fixes"):
            self.engine.advance(ScriptedRuntime(extra_edit))
        self.assertEqual(self.engine.state()["outputs"], original_outputs)
        self.engine.retry()

        def wrong_verification(request):
            response = self.consistency_apply(request)
            context = self.engine.consistency_context(self.engine.state(), self.engine.current_iteration(self.engine.state()))
            self.write(context["report_path"], {"chapters": {"story": {"source_sha256": "stale", "output_sha256": "stale"}}})
            return response

        with self.assertRaisesRegex(ValueError, "matching hashes"):
            self.engine.advance(ScriptedRuntime(wrong_verification))
        self.engine.retry()
        self.engine.advance(ScriptedRuntime(self.consistency_apply))
        state = self.engine.state()
        self.assertEqual(state["outputs"][0], original_outputs[0])  # Rejection leaves the title untouched.
        self.assertEqual(self.engine.store.content(state["outputs"][1]), b"He returned.\n")
        self.assertEqual(self.engine.file(original_outputs[1]["path"]).read_bytes(), b"He came back.\n")
        self.assertEqual([c["id"] for c in state["outputs"][1]["consistency_changes"]], ["C001"])
        self.engine.accept(state["acceptance_id"], confirm_final=True)
        self.engine.advance(None)
        self.assertEqual((self.engine.root / "export/0002.md").read_bytes(), b"He returned.\n")
        library = self.service.library(self.work_id)
        record = json.loads(library.read(library.head("literary-translation/v001/run.json")))
        fix = record["chapters"][1]["consistency_changes"][0]
        self.assertEqual((fix["before"], fix["after"]), ("He came back.", "He returned."))
        self.assertEqual(fix["receipt_id"], record["consistency"]["review"]["receipt_id"])

    def test_consistency_rejects_stale_coverage_and_unreviewed_proposals(self):
        self.prepare()
        self.translate_chapter(consistency=False)
        for bad, error in (("coverage", "matching hashes"), ("overlap", "overlap"), ("receipt", "no matching human")):
            with self.subTest(bad=bad):
                def invalid(request):
                    fixes = self.consistency_fixes()
                    if bad == "overlap":
                        fixes.append({**fixes[0], "id": "C003", "before": "came back", "after": "returned"})
                    response = self.consistency_gate(
                        request, changes=fixes, dispositions={"C001": "approve", "C002": "reject"} if bad == "receipt" else None)
                    if bad == "coverage":
                        plan = json.loads(self.engine.file(response["binding_path"]).read_text(encoding="utf-8"))
                        plan["chapters"]["story"]["translation_sha256"] = "stale"
                        self.write(response["binding_path"], plan)
                    return response
                with self.assertRaisesRegex(ValueError, error):
                    self.engine.advance(ScriptedRuntime(invalid))
                self.engine.retry()

    def test_consistency_promotes_multiple_chapters_together_and_preserves_other_bytes(self):
        self.english = {"story": "He came back.\r\n", "front-matter": "Story\r\n"}
        self.prepare()
        self.translate_chapter(consistency=False)
        original = self.engine.state()["outputs"]
        fixes = self.consistency_fixes()
        fixes[0].update(before="came back", after="returned")
        fixes.append({**fixes[0], "id": "C003", "before": "He", "after": "The narrator"})
        self.engine.advance(ScriptedRuntime(lambda r: self.consistency_gate(r, changes=fixes)))
        self.engine.reply(self.engine.state()["gate"]["id"], "C001 approve\nC002 approve\nC003 approve")
        self.engine.advance(ScriptedRuntime(lambda r: self.consistency_gate(
            r, changes=fixes, revision="2", dispositions={fix["id"]: "approve" for fix in fixes})))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm final closure")

        def incomplete(request):
            response = self.consistency_apply(request)
            state = self.engine.state()
            context = self.engine.consistency_context(state, self.engine.current_iteration(state))
            story = next(c for c in context["chapters"] if c["chapter_id"] == "story")
            self.write(story["candidate_path"], "Incomplete")
            return response

        with self.assertRaisesRegex(ValueError, "exact approved fixes"):
            self.engine.advance(ScriptedRuntime(incomplete))
        self.assertEqual(self.engine.state()["outputs"], original)  # No partial promotion of the title.
        self.engine.retry()
        self.engine.advance(ScriptedRuntime(self.consistency_apply))
        outputs = self.engine.state()["outputs"]
        self.assertEqual([self.engine.store.content(output) for output in outputs],
                         [b"Tale\r\n", b"The narrator returned.\r\n"])
        self.engine.restart_chapter("_whole", reason="Check corrected versions again")
        self.finish_consistency()
        self.assertEqual(self.engine.state()["outputs"], outputs)
        self.engine.verify(self.engine.state())

    def test_chapter_restart_invalidates_pending_and_completed_consistency(self):
        self.prepare()
        self.translate_chapter(consistency=False)
        self.engine.advance(ScriptedRuntime(self.consistency_gate))
        old_gate = self.engine.state()["gate"]["id"]
        self.engine.restart_chapter("story", reason="Revise before closing book review")
        self.assertEqual(self.engine.state()["iterations"][-1]["attempt"], 2)
        self.translate_chapter()
        old_acceptance = self.engine.state()["acceptance_id"]
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.reply(old_gate, "confirm consistency")
        self.engine.restart_chapter("story", reason="New terminology after the book review")
        whole = self.engine.state()["iterations"][-1]
        self.assertEqual((whole["status"], whole["attempt"]), ("pending", 3))
        self.assertNotIn("review", whole)
        self.assertNotIn("acceptance_id", self.engine.state())
        self.translate_chapter()
        self.assertNotEqual(old_acceptance, self.engine.state()["acceptance_id"])
        # Restart the whole-book job itself without discarding or retranslating any chapter.
        outputs = self.engine.state()["outputs"]
        self.engine.restart_chapter("_whole", reason="Repeat consistency check")
        self.assertEqual(self.engine.state()["outputs"], outputs)
        self.finish_consistency()
        self.assertEqual(self.engine.state()["status"], "WAITING_FOR_ACCEPTANCE")

    def test_restart_gates_acceptance_and_export_preserve_original(self):
        original = self.source.read_bytes()
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        gate_id = self.engine.state()["gate"]["id"]
        self.reopen()
        self.assertEqual(self.engine.state()["gate"]["id"], gate_id)
        with self.assertRaisesRegex(ValueError, "WAITING_FOR_HUMAN"):
            self.engine.advance(ScriptedRuntime(lambda r: result()))
        with self.assertRaisesRegex(ValueError, "unresolved"):
            self.engine.reply(gate_id, "confirm final closure")
        self.engine.reply(gate_id, "PM001 approve")
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.reply(gate_id, "PM001 approve")
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate("2", True)))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm final closure")
        self.engine.advance(ScriptedRuntime(self.sanity_gate))
        self.engine.reply(self.engine.state()["gate"]["id"], "approve chapter")
        self.engine.advance(ScriptedRuntime(self.translation))
        self.finish_consistency()
        self.assertEqual(self.engine.state()["status"], "WAITING_FOR_ACCEPTANCE")
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.accept("incorrect-acceptance", confirm_final=True)
        acceptance = next(a for a in self.service.get_run(self.run_id)["available_actions"] if a["action"] == "accept")
        self.assertTrue(acceptance["enabled"] and acceptance["irreversible"])
        self.assertIn("can never change", acceptance["confirmation"])
        with self.assertRaises(WorkflowError) as refused:
            self.engine.accept(self.engine.state()["acceptance_id"])
        self.assertEqual(refused.exception.code, "confirmation_required")
        self.engine.accept(self.engine.state()["acceptance_id"], confirm_final=True)
        self.assertTrue(self.engine.state()["acceptance"]["finalization"]["confirmed"])
        state = self.engine.advance(None)
        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual((Path(state["export_path"]) / "0002.md").read_text(), "He came back.\n")
        self.assertEqual(self.source.read_bytes(), original)
        self.assertTrue(any(event["kind"] == "review.received" for event in self.engine.store.events()))

    def test_run_passage_size_is_fixed_per_run_and_enforced(self):
        self.assertEqual(self.engine.state()["settings"], {"passage_size": 1500})  # The template's CJK default.
        for settings, error in (({"passage_size": 50}, "whole number"), ({"pace": 1}, "Unknown run settings")):
            with self.assertRaisesRegex(ValueError, error):
                self.service.create_run(TRANSLATION, upload=self.source, manuscript_language="zh", settings=settings)
        self.parts = ["他回来了。" * 30 + "\n"]  # One 150-character paragraph.
        self.new_engine(settings={"passage_size": 100})
        self.prepare()
        self.assertIn('"passage_limit": {\n    "max": 100,\n    "unit": "cjk_chars"', self.prompt(self.engine.state()))
        with self.assertRaisesRegex(ValueError, "150 characters, over this run's maximum of 100"):
            self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        self.engine.retry()
        # An oversize exception for the exact range goes to the user like any other map exception.
        state = self.engine.advance(ScriptedRuntime(lambda request: self.map_gate(kind="oversize")))
        self.assertEqual(state["gate"]["kind"], "map_exceptions")
        new_id = self.service.restart_workflow(self.run_id, reason="Start again")
        with self.service.open_run(new_id) as engine:
            self.assertEqual(engine.state()["settings"], {"passage_size": 100})

    def test_passage_map_is_internal_unless_it_has_exceptions(self):
        self.prepare()
        story = lambda passages, exceptions=(): self.write("translation/maps/story.json", {  # noqa: E731
            "chapter_id": "story", "passages": passages, "exceptions": list(exceptions)})
        cases = [
            (lambda: None, "Save the chapter's passage map"),
            (lambda: story([{"id": "P1", "first_paragraph": 2, "last_paragraph": 2}]), "once, in order"),
            (lambda: story([{"id": "P1", "first_paragraph": 1, "last_paragraph": 1},
                            {"id": "P2", "first_paragraph": 1, "last_paragraph": 2}]), "once, in order"),
            (lambda: story([{"id": "P1", "first_paragraph": 1, "last_paragraph": 1}]), "but the chapter has"),
            (lambda: story([{"id": "P1", "first_paragraph": 1, "last_paragraph": 2}],
                           [{"id": "X1", "kind": "exclude", "first_paragraph": 1, "last_paragraph": 1,
                             "reason": "Epigraph"}]), "raise a map_exceptions sheet"),
        ]
        for write_map, message in cases:
            with self.subTest(message=message):
                def action(request, write_map=write_map):
                    write_map()
                    return self.sanity_gate(request)
                with self.assertRaisesRegex(ValueError, message):
                    self.engine.advance(ScriptedRuntime(action))
                self.engine.retry()

        def covered(request):
            story([{"id": "P1", "first_paragraph": 1, "last_paragraph": 2}])
            return self.sanity_gate(request)
        self.engine.advance(ScriptedRuntime(covered))  # No exceptions: no map gate at all.
        self.assertEqual(self.engine.state()["gate"]["kind"], "chapter_sanity")

    def test_complete_resolving_submission_closes_advice_but_not_chapter_edits(self):
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        self.engine.reply(self.engine.state()["gate"]["id"], "PM001 approve")
        state = self.engine.state()
        self.assertIn("map_exceptions", state["approvals"])  # Implied closure: no separate confirmation.
        self.assertTrue(state["receipts"][-1]["parsed"]["implied_closure"])
        rules = state["definition"]["gates"]
        self.assertEqual((rules["translation_issue"]["closure"], rules["chapter_sanity"]["closure"]),
                         ("implied", "required"))

    def test_empty_diff_approval_needs_an_explicit_recorded_statement(self):
        self.prepare()

        def sanity(message, saved):
            def action(request):
                self.write("translation/maps/story.json", {
                    "chapter_id": "story", "passages": [{"id": "P1", "first_paragraph": 1, "last_paragraph": 2}],
                    "exceptions": []})
                return result("needs_human_input", gate="chapter_sanity", message=message,
                              state_path=self.write("translation/sanity.md", saved),
                              binding_path=self.write("translation/assembled.md", "He came back.\n"))
            return action

        with self.assertRaisesRegex(ValueError, "explicit statement"):
            self.engine.advance(ScriptedRuntime(sanity("He came back.", "Phase: chapter-sanity-await\n")))
        self.engine.retry()
        # The statement in the persisted gate message suffices when the saved state omits it.
        self.engine.advance(ScriptedRuntime(sanity("**No textual changes proposed**.", "Phase: chapter-sanity-await\n")))
        self.assertEqual(self.engine.state()["gate"]["kind"], "chapter_sanity")

    def test_cannot_complete_translation_without_domain_gates(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "chapter approval"):
            self.engine.advance(ScriptedRuntime(self.translation))
        self.assertEqual(self.engine.state()["status"], "FAILED")
        self.assertEqual([o["chapter_id"] for o in self.engine.state()["outputs"]], ["front-matter"])
        self.engine.retry()
        self.assertEqual(self.engine.state()["stage"], "translate")
        self.assertIsNone(self.engine.state()["thread_id"])

    def two_chapter_engine(self):
        self.parts = ["# 第一章\n\n他回来了。\n", "# 第二章\n\n她走了。\n"]
        self.english = {"chapter-1": "He came back.\n", "chapter-2": "She left.\n"}
        self.source.write_bytes("".join(self.parts).encode())
        return self.new_engine()

    def test_second_chapter_has_new_context_and_cannot_inherit_first_chapter_gates(self):
        self.two_chapter_engine()
        self.complete_translation()
        state = self.engine.state()
        self.assertEqual(state["status"], "READY")
        self.assertEqual([i["status"] for i in state["iterations"]], ["completed", "completed", "pending", "pending"])
        self.assertEqual(self.engine.current_iteration(state)["chapter_id"], "chapter-2")
        self.assertIsNone(state["thread_id"])
        self.assertEqual(state["approvals"], {})
        self.assertEqual(len(state["outputs"]), 2)
        self.assertEqual(set(state["continuity"]), {"glossary", "voice", "brief-samples"})
        with self.assertRaisesRegex(ValueError, "chapter approval"):
            self.engine.advance(ScriptedRuntime(self.translation))

    def test_malformed_result_is_persisted_as_failure(self):
        with self.assertRaisesRegex(ValueError, "Invalid runtime result"):
            self.engine.advance(ScriptedRuntime(lambda request: {"outcome": "completed"}))
        self.assertEqual(self.engine.state()["status"], "FAILED")
        self.assertEqual(self.engine.state()["stage"], "prepare")

    def test_empty_sanity_diff_still_requires_explicit_approval(self):
        self.prepare()
        self.approve_map()
        self.engine.advance(ScriptedRuntime(self.sanity_gate))
        self.engine.reply(self.engine.state()["gate"]["id"], "continue")
        self.assertNotIn("chapter_sanity", self.engine.state()["approvals"])
        with self.assertRaisesRegex(ValueError, "chapter approval"):
            self.engine.advance(ScriptedRuntime(self.translation))

    def test_agent_cannot_claim_resolved_items_without_human_receipts(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "no matching human"):
            self.engine.advance(ScriptedRuntime(lambda request: self.map_gate("1", True)))
        self.assertNotIn("map_exceptions", self.engine.state()["approvals"])

    def test_changed_review_and_changed_source_block_responses(self):
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        gate_id = self.engine.state()["gate"]["id"]
        self.write("translation/maps/story.json", {"chapter_id": "story", "passages": [], "exceptions": []})
        with self.assertRaisesRegex(ValueError, "Review changed"):
            self.engine.reply(gate_id, "PM001 approve")
        self.write(f"prepared/{self.work_id}/revisions/r0001/chapters/0001.md", "Tampered original\n")
        with self.assertRaisesRegex(ValueError, "Prepared source changed"):
            self.engine.retry(refresh_gate=True)

    def test_wrong_revision_envelope_is_rejected(self):
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        sheet = self.sheet()
        payload = "\n".join([sheet["submission"]["instruction"], "Approval sheet: map-story",
                             "Revision: old", *sheet["submission"]["rules"], "", "PM001 approve"])
        with self.assertRaises(ValueError):
            self.engine.reply(self.engine.state()["gate"]["id"], payload)
        self.assertEqual(self.gate_receipts(), [])

    def test_changed_proposal_cannot_reuse_old_disposition(self):
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        self.engine.reply(self.engine.state()["gate"]["id"], "PM001 approve")

        def changed(request):
            output = self.map_gate("2", True)
            sheet = self.sheet("2", True)
            sheet["items"][0]["details"][0]["value"] = "A different boundary"
            self.write(output["review_path"], sheet)
            return output

        with self.assertRaisesRegex(ValueError, "no matching human"):
            self.engine.advance(ScriptedRuntime(changed))

    def test_source_failure_and_path_escape_do_not_promote(self):
        def invalid(request):
            output = self.preparation(request)
            path = self.workspace / output["work_record"]
            work = json.loads(path.read_text())
            work["preparation"]["blockers"] = ["Missing page"]
            path.write_text(json.dumps(work), encoding="utf-8")
            return output

        with self.assertRaisesRegex(ValueError, "blockers"):
            self.engine.advance(ScriptedRuntime(invalid))
        self.assertEqual(self.engine.state()["stage"], "prepare")
        self.engine.retry()
        with self.assertRaisesRegex(ValueError, "escapes"):
            self.engine.advance(ScriptedRuntime(lambda r: result(work_record="../outside.json")))

    def test_failure_keeps_receipt_and_restart_requires_explicit_recovery(self):
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        self.engine.reply(self.engine.state()["gate"]["id"], "PM001 approve")
        receipt = self.engine.state()["next_input"]["id"]

        def fail(request):
            raise RuntimeError("Interrupted provider")

        with self.assertRaisesRegex(RuntimeError, "Interrupted"):
            self.engine.advance(ScriptedRuntime(fail))
        self.engine.retry()
        self.assertEqual(self.engine.state()["next_input"]["id"], receipt)
        self.assertEqual(len(self.gate_receipts()), 1)

    def test_profile_restart_preserves_completed_work_and_pending_receipt(self):
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        revision, state = self.engine.store.load()
        state.update(execution={"profile": "previous-profile", "harness": "codex"},
                     thread_id="old-codex-thread")
        self.engine.store.save(revision, state, "test.profile_selected")
        gate, outputs = state["gate"], state["outputs"]
        self.reopen()  # A new controller sees exactly the same pending review.
        self.assertEqual(self.engine.state()["gate"], gate)
        self.engine.reply(gate["id"], "PM001 approve")
        receipt = self.engine.state()["next_input"]
        approvals = self.engine.state()["approvals"]
        with patch.dict("os.environ", {"TEST_INFERENCE_KEY": "fixture-key"}):
            profile = ExecutionProfile(profile_data())

        def fail(request, on_event, on_thread):
            self.assertIsNone(request.thread_id)  # Never resume the old harness's conversation.
            self.assertIn(receipt["id"], request.prompt)
            on_thread("fresh-pi-thread")
            raise RuntimeError("Interrupted Pi operation")

        with patch("workflow.src.harnesses.PiRuntime") as adapter:
            adapter.return_value.run.side_effect = fail
            with self.assertRaisesRegex(RuntimeError, "Interrupted Pi"):
                self.engine.advance(profile.runtime())
        state = self.engine.state()
        self.assertEqual(state["execution"]["harness"], "pi")
        self.assertEqual(state["execution"]["model"], "vendor/family/test-model")
        self.assertEqual(state["outputs"], outputs)
        self.assertEqual(state["approvals"], approvals)
        self.assertEqual(state["next_input"], receipt)
        count = len(state["receipts"])
        self.engine.retry()
        self.assertEqual(self.engine.state()["next_input"], receipt)
        self.assertEqual(len(self.engine.state()["receipts"]), count)
        with patch("workflow.src.harnesses.PiRuntime") as adapter:
            def complete(request, on_event, on_thread):
                self.assertIsNone(request.thread_id)
                self.assertIn(receipt["id"], request.prompt)
                on_thread("fresh-pi-retry")
                return self.map_gate("2", True)
            adapter.return_value.run.side_effect = complete
            state = self.engine.advance(profile.runtime())
        self.assertIsNone(state["next_input"])
        self.assertEqual(len(state["receipts"]), count)
        self.assertEqual(state["outputs"], outputs)
        self.assertEqual(state["status"], "WAITING_FOR_HUMAN")
        self.assertEqual(state["gate"]["kind"], "map_exceptions")
        self.engine.reply(state["gate"]["id"], "confirm final closure")
        self.assertEqual(self.engine.state()["status"], "READY")
        attempts = [e for e in self.engine.store.events() if e["kind"] == "execution.started"]
        self.assertEqual(attempts[-1]["payload"]["execution"], state["execution"])

    def test_profile_execution_refuses_an_unconfigured_runtime(self):
        revision, state = self.engine.store.load()
        state["execution"] = {"profile": "explicit"}
        self.engine.store.save(revision, state, "test.profile_selected")
        with self.assertRaisesRegex(ValueError, "requires an execution profile"):
            self.engine.advance(ScriptedRuntime(self.preparation))
        self.assertEqual(self.engine.state()["status"], "READY")

    def test_export_conflict_is_not_overwritten(self):
        self.complete_translation()
        self.engine.accept(self.engine.state()["acceptance_id"], confirm_final=True)
        export = self.engine.root / "export"
        export.mkdir()
        (export / "0001.md").write_bytes(b"User file")
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            self.engine.advance(None)
        self.assertEqual((export / "0001.md").read_bytes(), b"User file")

    def test_run_lock_excludes_another_process_handle(self):
        second = Engine.open(self.engine.root)
        try:
            with self.engine.store.locked():
                with self.assertRaisesRegex(ValueError, "Another process"):
                    with second.store.locked():
                        self.fail("Acquired an already-held lock")
        finally:
            second.close()

    def test_reject_unsupported_language_or_invalid_template(self):
        template = registry.get(TRANSLATION)
        template["target_language"] = "fr-FR"
        with self.assertRaisesRegex(ValueError, "US English"):
            TranslationEngine.create(self.base / "french", template, source=self.source, manuscript_language="zh",
                                     work_id="story")
        template = registry.get(TRANSLATION)
        template["stages"][2]["gates"].append("undeclared_gate")
        with self.assertRaisesRegex(ValueError, "undeclared gate"):
            registry.validate(template)
        template = registry.get(TRANSLATION)
        template["stages"].append(template["stages"].pop(-2))  # Acceptance after export.
        with self.assertRaisesRegex(ValueError, "export must be the final stage"):
            registry.validate(template)
        template = registry.get(TRANSLATION)
        template["stages"].insert(0, template["stages"].pop(3))  # The brief before preparation.
        with self.assertRaisesRegex(ValueError, "front-matter stage"):
            registry.validate(template)
        template = registry.get(TRANSLATION)
        del template["gates"]["translation_brief"]["command"]
        with self.assertRaisesRegex(ValueError, "needs an approval command"):
            registry.validate(template)
        with self.assertRaisesRegex(ValueError, "Unknown agent"):
            TranslationEngine.create(self.base / "models", registry.get(TRANSLATION), source=self.source,
                                     manuscript_language="zh", work_id="story", agent_models={"edit": "m"})
        self.assertFalse((self.base / "french").exists())

    def e2e_case(self):
        spec = {
            "schema_version": 1, "case_id": "fixture-e2e", "revision": 1,
            "task": "literary-translation-workflow",
            "input": {
                "manuscript": {"file": str(self.source), "format": "markdown", "sha256": digest(self.source.read_bytes())},
                "manuscript_language": "zh", "target_language": "en-US", "scope": "whole_work",
                "template_id": TRANSLATION, "task_specification": "task.md",
                "runtime": {"adapter": "codex-app-server", "model": None, "human_responses": "interactive"},
            },
            "source_inventory": {"title": "Synthetic fixture"},
            "expected_output": {
                "stage_sequence": ["prepare", "metadata", "analysis", "brief", "translate", "accept", "export"],
                "required_files": ["state.sqlite3", "export/manifest.json", "export/glossary.md", "export/voice.md"],
            },
            "checks": [
                {"id": name, "evaluation": method, "expectation": f"Verify {name} on the synthetic fixture."}
                for name, method in (
                    ("source-integrity", "deterministic"), ("coverage", "source-comparison"),
                    ("domain-gates", "receipts-and-domain-review"), ("recovery", "interactive-scenario"),
                    ("stale-response", "interactive-scenario"), ("continuity", "domain-review"),
                    ("export-provenance", "deterministic"), ("fidelity-routing", "trace-and-domain-review"),
                )
            ],
        }
        (self.base / "task.md").write_text("Translate the complete synthetic fixture.", encoding="utf-8")
        path = self.base / "case.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        case = run_e2e.load_case(path)
        run_e2e.bind_case(self.engine, case, {"executable": "test-only", "version": "scripted fixture"})
        return case

    def test_e2e_launcher_requires_an_explicit_case(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as stopped:
            run_e2e.parser().parse_args([])
        self.assertEqual(stopped.exception.code, 2)

    def test_e2e_launcher_interactive_loop_and_honest_report(self):
        case = self.e2e_case()
        actions = iter([
            self.preparation, self.samples_gate, self.brief_gate,
            *[lambda r: self.map_gate(), lambda r: self.map_gate("2", True), self.sanity_gate, self.translation] * 2,
            self.consistency_gate, self.consistency_apply,
        ])
        prompts = []

        def action(request):
            prompts.append(request.prompt)
            return next(actions)(request)

        chapter = ["PM001 approve", ".", "confirm final closure", ".", "approve chapter", "."]
        replies = iter(["confirm metadata", ".", "S1 choose A", ".", "approve brief", ".", *chapter * 2,
                        "confirm consistency", ".", "accept", "skip", "skip", "skip", "skip"])
        runtime = run_e2e.CaseRuntime(ScriptedRuntime(action), case["task"])
        with contextlib.redirect_stdout(io.StringIO()):
            code = run_e2e.drive(self.engine, case, runtime, input_fn=lambda _: next(replies))
        self.assertEqual(code, 2)  # Execution completed, manual checks not claimed as passed.
        self.assertTrue(all("Translate the complete synthetic fixture." in prompt for prompt in prompts))
        report = json.loads((self.engine.root / "e2e-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["workflow_status"], "COMPLETED")
        self.assertEqual(report["e2e_status"], "needs-review")
        checks = {c["id"]: c for c in report["checks"]}
        for name in ("recovery", "stale-response", "source-integrity", "export-provenance"):
            self.assertEqual(checks[name]["status"], "passed")
        self.assertEqual(checks["domain-gates"]["status"], "not-checked")
        self.assertEqual(report["literary_quality"]["status"], "not-checked")
        self.assertEqual((self.engine.root / "candidate.en.txt").read_text(), "Story\n\nHe came back.\n")
        self.assertEqual(len(self.engine.state()["receipts"]), 10)  # Includes whole-book closure.
        self.assertEqual(report["automated_checks"]["closure-receipts"]["status"], "passed")
        self.assertEqual(report["automated_checks"]["stage-order"]["evidence"],
                         ["prepare", "metadata", "analysis", "brief", "translate", "accept", "export"])
        # A completed run can finish its human evidence review without another model call.
        evidence = iter(["pass", "Synthetic test evidence"] * 4)
        with contextlib.redirect_stdout(io.StringIO()):
            code = run_e2e.drive(self.engine, case, None, input_fn=lambda _: next(evidence))
        self.assertEqual(code, 0)
        report = json.loads((self.engine.root / "e2e-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["e2e_status"], "passed")
        self.assertEqual(report["literary_quality"]["status"], "not-checked")

    def test_e2e_launcher_eof_preserves_gate_and_can_bind_resume(self):
        case = self.e2e_case()
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda r: self.map_gate()))
        gate_id = self.engine.state()["gate"]["id"]

        def eof(_):
            raise EOFError

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_e2e.drive(self.engine, case, None, input_fn=eof), 2)
        self.assertEqual(self.engine.state()["gate"]["id"], gate_id)
        self.assertEqual(self.gate_receipts(), [])
        run_e2e.bind_case(self.engine, case, {"version": "test"}, resume=True)
        changed = dict(case, task_sha256="changed")
        with self.assertRaisesRegex(ValueError, "Changed task_sha256"):
            run_e2e.bind_case(self.engine, changed, {}, resume=True)

    def test_e2e_report_detects_corrupt_export_and_does_not_write_candidate(self):
        case = self.e2e_case()
        self.finalize_translation()
        (self.engine.root / "export/0001.md").write_bytes(b"Unaccepted replacement")
        report = run_e2e.write_report(self.engine, case)
        self.assertEqual(report["e2e_status"], "failed")
        self.assertEqual(report["automated_checks"]["export-provenance"]["status"], "failed")
        run_e2e.collect_candidate(self.engine, report)
        self.assertFalse((self.engine.root / "candidate.en.txt").exists())

    def test_e2e_case_check_has_no_run_or_runtime_side_effects(self):
        case = self.e2e_case()
        unused = self.base / "unused-server"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run_e2e.main(["--case", case["case_path"], "--check-case", "--server-root", str(unused)])
        self.assertEqual(code, 0)
        self.assertFalse(unused.exists())
        self.source.write_bytes(b"Changed source")
        with self.assertRaisesRegex(ValueError, "manuscript hash"):
            run_e2e.load_case(Path(case["case_path"]))

    def test_recommended_approvals_complete_without_claiming_human_review(self):
        case = self.e2e_case()
        actions = iter([
            (self.preparation, "accept", "confirm metadata"),
            (self.samples_gate, "accept", "S1 choose A"),
            (self.brief_gate, "accept", "approve brief"),
            *[(lambda r: self.map_gate(), "accept", "PM001 approve"),
              (lambda r: self.map_gate("2", True), "accept", "confirm final closure"),
              (self.sanity_gate, "accept", "approve chapter"),
              (self.translation, "accept", "accept")] * 2,
            (self.consistency_gate, "accept", "confirm consistency"),
            (self.consistency_apply, "accept", "accept"),
        ])

        def action(request):
            operation, recommended, response = next(actions)
            self.assertIn("approval_recommendation", request.output_schema["required"])
            return operation(request) | {"approval_recommendation": {
                "action": recommended, "response": response, "reason": "Synthetic fixture recommendation",
            }}

        runtime = run_e2e.CaseRuntime(ScriptedRuntime(action), case["task"], auto_approve_recommended=True)
        with contextlib.redirect_stdout(io.StringIO()):
            code = run_e2e.drive(self.engine, case, runtime, auto_approve_recommended=True,
                                 input_fn=lambda _: self.fail("Automation must not read stdin."))
        self.assertEqual(code, 2)
        state = self.engine.state()
        self.assertEqual(state["status"], "COMPLETED")
        self.assertTrue(all(r["decision_source"] == "delegated-automation" for r in state["receipts"]))
        self.assertEqual(state["acceptance"]["decision_source"], "delegated-automation")
        report = json.loads((self.engine.root / "e2e-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["e2e_status"], "needs-review")
        self.assertEqual(report["delegated_decisions"], 10)
        self.assertEqual(state["metadata_approval"]["decision_source"], "delegated-automation")
        self.assertEqual(report["literary_quality"]["status"], "not-checked")

    def test_automation_does_not_confirm_unrecommended_or_edited_metadata(self):
        case = self.e2e_case()
        for recommendation, edit, reason in [
            ({"action": "needs_review", "response": "", "reason": "Genre needs the author's judgment"}, False,
             "Recommendation requires review"),
            ({"action": "accept", "response": "confirm metadata", "reason": "Synthetic fixture"}, True,
             "Metadata changed after the recommendation"),
        ]:
            with self.subTest(edit=edit):
                self.new_engine()
                run_e2e.bind_case(self.engine, case, {"executable": "test-only", "version": "scripted fixture"})
                runtime = run_e2e.CaseRuntime(
                    ScriptedRuntime(lambda r: self.prepare_v2(r) | {"approval_recommendation": recommendation}),
                    case["task"], auto_approve_recommended=True,
                )
                self.engine.advance(runtime)
                if edit:
                    self.engine.edit_metadata("/genres", [], gate_id=self.engine.state()["gate"]["id"])
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    code = run_e2e.drive(self.engine, case, runtime, auto_approve_recommended=True,
                                         input_fn=lambda _: self.fail("Must stop without reading stdin."))
                self.assertEqual(code, 2)
                self.assertIn(reason, output.getvalue())
                state = self.engine.state()
                self.assertEqual((state["stage"], state["status"]), ("metadata", "WAITING_FOR_HUMAN"))
                self.assertEqual(state["receipts"], [])

    def test_automation_stops_on_review_or_nonaccepting_recommendation(self):
        case = self.e2e_case()
        self.prepare()
        for recommendation in [
            {"action": "needs_review", "response": "", "reason": "Ambiguous source needs user input"},
            {"action": "accept", "response": "PM001 revise: move boundary", "reason": "Invalid accepting action"},
        ]:
            with self.subTest(recommendation=recommendation):
                if self.engine.state()["status"] == "WAITING_FOR_HUMAN":
                    self.engine.retry(refresh_gate=True)
                runtime = run_e2e.CaseRuntime(
                    ScriptedRuntime(lambda r: self.map_gate() | {"approval_recommendation": recommendation}),
                    case["task"], auto_approve_recommended=True,
                )
                with contextlib.redirect_stdout(io.StringIO()):
                    code = run_e2e.drive(self.engine, case, runtime, auto_approve_recommended=True,
                                         input_fn=lambda _: self.fail("Must stop without reading stdin."))
                self.assertEqual(code, 2)
                self.assertEqual(self.engine.state()["status"], "WAITING_FOR_HUMAN")
                self.assertEqual(self.gate_receipts(), [])

    def open_run(self, run_id):
        row = self.service._run_row(run_id)
        engine = Engine.open(Path(row["path"]), library=self.service.library(row["work_id"]))
        self.addCleanup(engine.close)
        return engine

    def test_removed_formatter_cannot_be_created(self):
        self.assertNotIn(FORMATTING, registry.templates())
        with self.assertRaisesRegex(ValueError, "Unknown workflow template"):
            self.service.create_derived_run(self.work_id, FORMATTING)

    def test_removed_workflow_history_is_read_only_and_does_not_block_new_runs(self):
        self.prepare()
        revision, state = self.engine.store.load()
        state["template_id"] = FORMATTING
        state["definition"]["id"] = FORMATTING
        state["definition"]["engine"] = "workflow.src.formatting:FormattingEngine"
        state.update(status="WAITING_FOR_HUMAN", gate={
            "id": "retired-format-gate", "kind": "format_spec", "stage": state["stage"],
            "chapter_id": None, "message": "Historical format specification.",
        })
        self.engine.store.save(revision, state, "fixture.removed_workflow")
        recorded = self.engine.store.load()
        view = self.service.get_run(self.run_id)
        self.assertEqual((view["status"], view["recorded_status"], view["retired"]),
                         ("RETIRED", "WAITING_FOR_HUMAN", True))
        self.assertNotIn("gate", view)
        self.assertEqual(view["available_actions"], [])
        with self.service.open_run(self.run_id) as archived:
            with self.assertRaises(WorkflowError) as removed:
                archived.reply(state["gate"]["id"], "FM001 approve")
            self.assertEqual(removed.exception.code, "workflow_removed")
        self.assertEqual(self.engine.store.load(), recorded)
        self.assertIsNone(self.service.get_work(self.work_id)["unfinished_run"])
        self.service.reindex()
        self.assertTrue(self.service.get_run(self.run_id)["retired"])
        new_run = self.service.create_run(TRANSLATION, work_id=self.work_id)
        self.assertNotEqual(new_run, self.run_id)

    def test_metadata_revision_drops_retired_workflow_without_rewriting_history(self):
        self.prepare()
        self.engine.cancel()
        library = self.service.library(self.work_id)
        head = library.head("work.json")
        legacy = json.loads(library.read(head))
        legacy["workflows"]["format-manuscript"] = dict(legacy["workflows"]["literary-editing"])
        [historical] = library.publish_many([{
            "artifact": "work.json", "data": (json.dumps(legacy) + "\n").encode(), "expected_head": head["id"],
        }], run_id=None, workflow=None, stage="fixture")
        self.service.edit_work_metadata(self.work_id, "/title", "User-confirmed title", "Author's choice")
        current = json.loads(library.read(library.head("work.json")))
        self.assertEqual(current["metadata"]["title"], "User-confirmed title")
        self.assertNotIn("format-manuscript", current["workflows"])
        self.assertIn("format-manuscript", json.loads(library.read(historical))["workflows"])

    # ----- M1: registry, restarts, library, service ---------------------------------------

    def test_test_only_template_registers_and_runs_without_engine_changes(self):
        template_id = registry.register(Path(__file__).parent / "templates/test-echo-v1/template.json")
        self.addCleanup(registry.unregister, template_id)
        self.assertIn(template_id, [t["id"] for t in self.service.list_templates()])
        run_id = self.service.create_run(template_id, upload=self.source, manuscript_language="zh")
        echo = self.open_run(run_id)

        def copy(request):
            self.assertIn("output/echo.md", request.prompt)
            target = echo.workspace / "output/echo.md"
            target.parent.mkdir()
            target.write_bytes((echo.root / "input/original.md").read_bytes())
            return result(output_path="output/echo.md")

        self.assertEqual(echo.advance(ScriptedRuntime(copy))["status"], "WAITING_FOR_ACCEPTANCE")
        echo.accept(echo.state()["acceptance_id"], confirm_final=True)
        state = echo.advance(None)
        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual((echo.root / "export/0001.md").read_bytes(), self.source.read_bytes())
        work = echo.state()["work_id"]
        self.assertEqual(self.service.get_work(work)["workflows"]["test-echo"]["status"], "completed")
        self.assertTrue(self.service.create_run(template_id, work_id=work))  # A completed run never blocks a new one.

    def chapter_two_with_provisional_glossary(self):
        def map_with_scratch(request):
            workdir = f"translation/.literary-translation-work/{self.work_id}/chapter-2/"
            self.write(workdir + "review-state.md", "Abandoned attempt.\n")
            self.write("translation/glossary.md", "# Glossary\nProvisional term.\n")
            return self.map_gate()

        self.engine.advance(ScriptedRuntime(map_with_scratch))

    def test_restart_chapter_archives_work_restores_continuity_and_keeps_order(self):
        self.two_chapter_engine()
        self.complete_translation()
        self.chapter_two_with_provisional_glossary()
        with self.assertRaisesRegex(ValueError, "Finish or restart chapter chapter-2"):
            self.engine.restart_chapter("chapter-1", reason="Too early")
        receipts = len(self.engine.state()["receipts"])
        state = self.engine.restart_chapter("chapter-2", reason="Inconsistent records after an exception")
        item = state["iterations"][2]
        self.assertEqual((item["status"], item["attempt"], state["status"], state["gate"]), ("pending", 2, "READY", None))
        self.assertEqual(len(state["receipts"]), receipts)
        archive = self.engine.root / state["restarts"][-1]["archive"]
        self.assertEqual((archive / f"translation/.literary-translation-work/{self.work_id}/chapter-2/review-state.md")
                         .read_text(encoding="utf-8"), "Abandoned attempt.\n")
        self.assertEqual((archive / "translation/glossary.md").read_text(encoding="utf-8"), "# Glossary\nProvisional term.\n")
        self.assertEqual(self.engine.file("translation/glossary.md").read_text(encoding="utf-8"),
                         "# Glossary\nThrough chapter-1.\n")
        with self.assertRaisesRegex(ValueError, "has not started"):
            self.engine.restart_chapter("chapter-2", reason="Again")
        self.translate_chapter()  # The same sheet identities are valid again for the new attempt.
        state = self.engine.state()
        self.assertEqual(state["status"], "WAITING_FOR_ACCEPTANCE")
        first_acceptance = state["acceptance_id"]
        # A completed chapter can be restarted before final acceptance; it keeps its place in source order.
        state = self.engine.restart_chapter("chapter-1", reason="Apply later terminology")
        self.assertEqual((state["stage"], state["status"]), ("translate", "READY"))
        self.assertEqual([o["chapter_id"] for o in state["outputs"]], ["front-matter", "chapter-2"])
        self.assertEqual(state["iterations"][1]["restarts"][0]["output"]["chapter_id"], "chapter-1")
        self.assertFalse((self.workspace / "translation/translated_english/chapter-1.md").exists())
        self.english["chapter-1"] = "He returned.\n"
        self.translate_chapter()
        state = self.engine.state()
        self.assertEqual([o["chapter_id"] for o in state["outputs"]], ["front-matter", "chapter-1", "chapter-2"])
        self.assertNotEqual(state["acceptance_id"], first_acceptance)
        self.engine.accept(state["acceptance_id"], confirm_final=True)
        state = self.engine.advance(None)
        self.assertEqual((self.engine.root / "export/0002.md").read_text(encoding="utf-8"), "He returned.\n")
        for operation in (lambda: self.engine.restart_chapter("chapter-1", reason="x"),
                          lambda: self.engine.restart_stage("translate", reason="x"),
                          lambda: self.service.restart_workflow(self.run_id, reason="x")):
            with self.assertRaises(WorkflowError) as refused:
                operation()
            self.assertEqual(refused.exception.code, "run_finalized")
        actions = {a["action"]: a for a in self.service.get_run(self.run_id)["available_actions"]}
        self.assertFalse(actions["restart_workflow"]["enabled"])
        self.assertIn("run_finalized", actions["restart_chapter"]["reason"])
        library = self.service.library(self.work_id)
        self.assertEqual(library.read(library.head("literary-translation/v001/chapters/0002.md")), b"He returned.\n")
        run_info = json.loads(library.read(library.head("literary-translation/v001/run.json")))
        self.assertEqual((run_info["version"], run_info["run_id"], run_info["template_id"]),
                         ("v001", self.run_id, TRANSLATION))
        self.assertEqual(run_info["acceptance"]["decision_source"], "human")
        self.assertIn("chapter_sanity", run_info["decisions"])
        manifest = library.head("literary-translation/v001/manifest.json")
        self.assertEqual(manifest["contract"], "accepted-markdown-chapters/1")
        self.assertEqual(json.loads(library.read(manifest))["version"], "v001")

    def test_restart_stage_archives_owned_paths_and_keeps_receipts(self):
        self.prepare()
        self.engine.advance(ScriptedRuntime(lambda request: self.map_gate()))
        self.engine.reply(self.engine.state()["gate"]["id"], "PM001 approve")
        with self.assertRaisesRegex(ValueError, "current stage or an earlier one"):
            self.engine.restart_stage("export", reason="x")
        receipts = self.engine.state()["receipts"]
        state = self.engine.restart_stage("translate", reason="Start translation over")
        self.assertEqual((state["stage"], state["status"], state["approvals"], state["next_input"]),
                         ("translate", "READY", {}, None))
        self.assertEqual(state["receipts"], receipts)
        record = state["restarts"][-1]
        self.assertEqual(record["superseded_receipt_ids"],
                         [r["id"] for r in receipts if r["gate"]["stage"] == "translate"])
        self.assertTrue((self.engine.root / record["archive"] / "translation/map-review.json").is_file())
        self.assertFalse((self.workspace / "translation/map-review.json").exists())
        self.assertEqual(state["iterations"][0]["attempt"], 2)
        self.approve_map()  # Old receipts cannot satisfy the new attempt, but its own can.
        self.assertIn("map_exceptions", self.engine.state()["approvals"])
        state = self.engine.restart_stage("metadata", reason="Review metadata again")
        self.assertEqual((state["stage"], state["status"], state["gate"]["kind"], state["metadata_approval"]),
                         ("metadata", "WAITING_FOR_HUMAN", "metadata_review", None))
        self.engine.reply(state["gate"]["id"], "confirm metadata")
        state = self.engine.restart_stage("prepare", reason="Prepare again")
        self.assertEqual((state["stage"], state["prepared"], state["iterations"]), ("prepare", None, []))
        self.assertFalse((self.workspace / "prepared").exists())
        self.prepare()
        self.assertEqual(self.engine.state()["stage"], "translate")

    def test_restart_workflow_carries_continuity_and_reuses_published_metadata(self):
        self.two_chapter_engine()
        self.engine.advance(ScriptedRuntime(self.prepare_v2))
        gate = self.engine.state()["gate"]["id"]
        self.engine.edit_metadata("/genres", ["Literary fiction"], gate_id=gate, reason="Author correction")
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm metadata")
        self.approve_brief()
        self.translate_chapter()  # front matter
        self.translate_chapter()
        with self.assertRaises(WorkflowError) as busy:
            self.service.create_run(TRANSLATION, work_id=self.work_id)
        self.assertEqual(busy.exception.code, "work_busy")
        old_id = self.run_id
        new_id = self.service.restart_workflow(old_id, reason="Start again with what we learned")
        old = self.engine.state()
        self.assertEqual((old["status"], old["superseded_by"]), ("CANCELLED", new_id))
        self.assertEqual(self.service._run_row(new_id)["restart_of"], old_id)
        self.run_id = new_id
        self.reopen()
        state = self.engine.state()
        self.assertEqual((state["stage"], state["work_id"]), ("prepare", self.work_id))  # Preparation runs again.
        self.assertEqual(state["carried_from"], {"run_id": old_id, "chapter_id": "chapter-1"})
        self.assertEqual(self.engine.file("translation/glossary.md").read_text(encoding="utf-8"),
                         "# Glossary\nThrough chapter-1.\n")
        self.assertNotIn("prior_work_record", self.engine.stage_prompt(
            self.engine.state(), self.engine.stage_def(self.engine.state())))
        # The agent creates a fresh draft. The host, not the agent, retains reviewed metadata.
        def fresh_draft(request):
            response = self.preparation(request)
            path = Path(request.cwd) / response["work_record"]
            work = json.loads(path.read_bytes())
            work["metadata"]["genres"] = ["Different source suggestion"]
            self.write(response["work_record"], work)
            return response

        self.engine.advance(ScriptedRuntime(fresh_draft))
        view = self.service.get_metadata(new_id)
        self.assertEqual(view["metadata"]["genres"], ["Literary fiction"])  # Kept from the work's record.
        self.assertEqual(view["provenance"]["/genres"]["review_status"], "confirmed")
        self.assertTrue(any(d["field"] == "/genres" for d in view["source_differences"]))
        with self.assertRaises(WorkflowError) as refused:
            self.service.restart_workflow(old_id, reason="again")
        self.assertEqual(refused.exception.code, "run_cancelled")

    def test_metadata_is_entered_at_audit_and_cleared_values_survive_repreparation(self):
        self.service.stop(self.run_id)
        with self.assertRaisesRegex(ValueError, "Prepare the manuscript first"):
            self.service.edit_work_metadata(self.work_id, "/title", "Too early")
        self.run_id = self.service.create_run(TRANSLATION, work_id=self.work_id)
        self.reopen()
        self.engine.advance(ScriptedRuntime(self.preparation))
        for field, value in (("/title", None), ("/contributors", []), ("/subtitle", "Reviewed subtitle")):
            self.engine.edit_metadata(field, value, gate_id=self.engine.state()["gate"]["id"])
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm metadata")
        original_source = self.source.read_bytes()
        self.run_id = self.service.restart_workflow(self.run_id, reason="Re-read the same manuscript")
        self.reopen()
        self.engine.advance(ScriptedRuntime(self.preparation))
        view = self.service.get_metadata(self.run_id)
        self.assertIsNone(view["metadata"]["title"])
        self.assertEqual(view["metadata"]["contributors"], [])
        self.assertEqual(view["metadata"]["subtitle"], "Reviewed subtitle")
        self.assertEqual(view["provenance"]["/title"]["origin"], "user_edit")
        self.assertEqual(self.source.read_bytes(), original_source)
        self.assertEqual(self.engine.state()["gate"]["kind"], "metadata_review")

    def test_engine_update_allows_reading_stopping_and_restarting_not_execution(self):
        self.prepare()
        with self.engine.store.locked():
            revision, state = self.engine.store.load()
            state["engine"]["sha256"] = "0" * 64
            self.engine.store.save(revision, state, "test.engine_changed")
        for operation in (lambda: self.engine.advance(ScriptedRuntime(self.map_gate)),
                          lambda: self.engine.retry(refresh_gate=True),
                          lambda: self.engine.restart_stage("translate", reason="x"),
                          lambda: self.engine.edit_metadata("/title", "x")):
            with self.assertRaises(WorkflowError) as refused:
                operation()
            self.assertEqual(refused.exception.code, "engine_updated")
        run = self.service.get_run(self.run_id)
        self.assertFalse(run["engine_current"])
        enabled = [a["action"] for a in run["available_actions"] if a["enabled"]]
        self.assertEqual(enabled, ["restart_workflow", "stop"])
        new_id = self.service.restart_workflow(self.run_id, reason="Engine updated")
        new = self.service.get_run(new_id)
        self.assertTrue(new["engine_current"])
        self.assertEqual(new["work_id"], self.work_id)

    def test_stopping_an_outdated_run_releases_the_work_without_deleting_history(self):
        self.prepare()
        with self.engine.store.locked():
            revision, state = self.engine.store.load()
            state["engine"]["sha256"] = "0" * 64
            self.engine.store.save(revision, state, "test.engine_changed")
        with self.assertRaises(WorkflowError) as busy:
            self.service.create_run(TRANSLATION, work_id=self.work_id)
        self.assertEqual(busy.exception.code, "work_busy")
        before = self.engine.state()
        stopped = self.service.stop(self.run_id)
        self.assertEqual(stopped["status"], "CANCELLED")
        after = self.engine.state()
        for field in ("outputs", "receipts", "gate", "prepared"):
            self.assertEqual(after.get(field), before.get(field))
        new_id = self.service.create_run(TRANSLATION, work_id=self.work_id)
        self.assertNotEqual(new_id, self.run_id)
        self.assertEqual(self.service.get_run(self.run_id)["status"], "CANCELLED")

    def test_work_level_metadata_edits_are_published_and_versioned(self):
        self.engine.advance(ScriptedRuntime(self.prepare_v2))
        blank = self.service.get_work_metadata(self.work_id)  # Created empty with the work.
        self.assertEqual((blank["metadata"]["title"], blank["metadata"]["manuscript_language"]), (None, "zh"))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm metadata")
        with self.assertRaises(WorkflowError) as busy:
            self.service.edit_work_metadata(self.work_id, "/genres", ["Satire"])
        self.assertEqual(busy.exception.code, "work_busy")
        self.service.stop(self.run_id)
        with self.assertRaisesRegex(ValueError, "fixed for a work"):
            self.service.edit_work_metadata(self.work_id, "/manuscript_language", "fr")
        edited = self.service.edit_work_metadata(self.work_id, "/genres", ["Satire"], "Author note")
        self.assertEqual(self.service.get_work_metadata(self.work_id)["metadata"]["genres"], ["Satire"])
        history = self.service.work_metadata_history(self.work_id)
        self.assertEqual([h["stage"] for h in history], ["create", "metadata", "work_metadata_edit"])
        self.assertEqual(history[-1]["record_revision"], edited["record_revision"])
        first = self.service.work_metadata_version(self.work_id, history[0]["record_revision"])
        self.assertEqual(first["metadata"]["genres"], ["Historical fiction"])
        library = self.service.library(self.work_id)
        self.assertTrue(list((library.root / "metadata-history").glob("*.json")))

    def test_work_display_uses_published_metadata_instead_of_upload_filename(self):
        self.engine.advance(ScriptedRuntime(self.prepare_v2))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm metadata")
        work = self.service.get_work(self.work_id)
        self.assertEqual((work["title"], work["manuscript_language"]), ("Story", "zh"))
        self.assertEqual(next(w for w in self.service.list_works() if w["id"] == self.work_id)["title"], "Story")
        self.service.stop(self.run_id)
        self.service.edit_work_metadata(self.work_id, "/title", "Author's title", "Preferred title")
        self.assertEqual(self.service.get_work(self.work_id)["title"], "Author's title")
        self.service.reindex()
        self.assertEqual(self.service.get_work(self.work_id)["title"], "Author's title")
        self.service.edit_work_metadata(self.work_id, "/title", None, "Leave the actual title unknown")
        self.assertEqual(self.service.get_work(self.work_id)["title"], self.source.stem)

    def test_library_hand_edits_are_recorded_and_conflicting_publishes_refused(self):
        self.engine.advance(ScriptedRuntime(self.prepare_v2))
        self.engine.reply(self.engine.state()["gate"]["id"], "confirm metadata")
        self.engine.restart_stage("metadata", reason="Review again")
        library = self.service.library(self.work_id)
        work = json.loads((library.root / "work.json").read_text(encoding="utf-8"))
        work["metadata"]["title"] = "Hand-edited title"
        (library.root / "work.json").write_text(json.dumps(work, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(WorkflowError) as conflict:
            self.engine.reply(self.engine.state()["gate"]["id"], "confirm metadata")
        self.assertEqual(conflict.exception.code, "metadata_conflict")
        head = library.head("work.json")
        self.assertEqual((head["status"], head["review_status"]), ("user_edit", "unreviewed"))
        gate = self.engine.state()["gate"]
        self.assertIn("Hand-edited title", gate["message"])  # The newer record is presented, never silently used.
        self.engine.reply(gate["id"], "confirm metadata")
        self.assertEqual(json.loads(library.read(library.head("work.json")))["metadata"]["title"], "Hand-edited title")
        (library.root / "work.json").write_text("{}", encoding="utf-8")
        self.assertEqual(len(self.service.verify_work(self.work_id)), 1)
        with self.assertRaises(WorkflowError) as conflict:
            self.engine.edit_metadata("/genres", ["Satire"])
        self.assertEqual(conflict.exception.code, "metadata_conflict")

    def test_cli_is_a_thin_client_of_the_service_and_index_can_be_rebuilt(self):
        from ..src import cli
        root = str(self.service.root)

        def call(*args):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(cli.main(["--server-root", root, "--owner", "tester", *args]), 0)
            return output.getvalue()

        self.assertIn(TRANSLATION, call("templates"))
        created = call("create", "--template", TRANSLATION, "--source", str(self.source), "--manuscript-language", "zh")
        run_id = json.loads(created.split("\n\nNext:")[0])["id"]
        self.assertNotEqual(self.service._run_row(run_id)["work_id"], self.work_id)  # Same file, new work.
        status = json.loads(call("status", run_id))
        self.assertEqual((status["stage"], status["status"]), ("prepare", "READY"))
        self.assertIn("Run " + run_id + " stopped; restarted as", call("restart", run_id, "--reason", "test"))
        self.assertEqual(len(json.loads(call("works", "list"))), 2)
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(cli.main(["--server-root", root, "create", "--template", TRANSLATION,
                                       "--work", self.work_id]), 1)
        self.assertIn("work_busy", error.getvalue())
        runs = len(self.service.list_runs())
        self.service.close()
        (self.service.root / "index.sqlite3").unlink()
        self.service = WorkflowService(self.service.root, owner="tester")
        self.addCleanup(self.service.close)
        self.assertEqual(len(self.service.reindex()), runs)
        self.assertEqual(len(self.service.list_works()), 2)

    # ----- literary editing: passes chosen by the user -------------------------------------

    def edit_job(self, stage, chapter_id):
        number = self.engine.state()["passes"][-1]["number"]
        return f"editorial/passes/{number:03d}-{stage}/{chapter_id}/"

    def editorial_review(self, stage, chapter_id, revision="1", resolved=False):
        job = self.edit_job(stage, chapter_id)
        sheet = self.sheet(revision, resolved)
        sheet.update(sheet_id=f"{stage}-{chapter_id}", title="Line edit decisions")
        sheet["decisions"] = [
            {"id": "accept", "command": "accept", "label": "Accept", "requires_note": False, "effect": "resolve"},
            {"id": "revise", "command": "revise proposal", "label": "Revise", "requires_note": True, "effect": "reopen"},
        ]
        sheet["items"][0].update(id="LE-001", summary="Tighten the opening sentence", allowed_decisions=["accept", "revise"],
                                 details=[{"label": "Current", "value": "He came back."},
                                          {"label": "Proposed", "value": "He returned."}],
                                 response={"decision": "accept", "note": "", "date": now()} if resolved else None)
        return result("needs_human_input", gate="editorial_review", message="Verdict and LE-001 proposal.",
                      state_path=self.write(job + "state.md", "Decisions pending.\n"),
                      binding_path=self.write(job + f"proposals-r{revision}.md", "LE-001: He came back. -> He returned.\n"),
                      review_path=self.write(job + "decision-table.json", sheet))

    def apply_gate(self, stage, chapter_id, message="Apply LE-001? Reply 'apply accepted changes'."):
        job = self.edit_job(stage, chapter_id)
        return result("needs_human_input", gate="apply_authorization", message=message,
                      state_path=self.write(job + "state.md", "Awaiting apply instruction.\n"),
                      binding_path=self.write(job + "decision-table.md", "| LE-001 | accept |\n"))

    def empty_review(self, stage, chapter_id):
        job = self.edit_job(stage, chapter_id)
        return result("needs_human_input", gate="editorial_review", message="Verdict: ready. No changes proposed.",
                      state_path=self.write(job + "state.md", "No changes proposed\n"),
                      binding_path=self.write(job + "verdict.md", "# Verdict\nReady.\n"))

    def finish_job(self, stage, chapter_id, output):
        return result(state_path=self.write(self.edit_job(stage, chapter_id) + "application-report.md", "Done.\n"),
                      output_path=output)

    def approve_empty_job(self, stage):
        chapter_id = self.engine.current_iteration(self.engine.state())["chapter_id"]
        self.engine.advance(ScriptedRuntime(lambda r: self.empty_review(stage, chapter_id)))
        self.engine.reply(self.engine.state()["gate"]["id"], "approve review")
        output = None if chapter_id == "_whole" else self.engine.state()["manuscript"][chapter_id]
        return self.engine.advance(ScriptedRuntime(lambda r: self.finish_job(stage, chapter_id, output)))

    def apply_change(self, stage, chapter_id, text, style):
        """One accepted proposal: review (the complete submission is its closure), apply authorization, application."""
        self.engine.advance(ScriptedRuntime(lambda r: self.editorial_review(stage, chapter_id)))
        self.engine.reply(self.engine.state()["gate"]["id"], "LE-001 accept")
        self.engine.advance(ScriptedRuntime(lambda r: self.apply_gate(stage, chapter_id)))
        self.engine.reply(self.engine.state()["gate"]["id"], "apply accepted changes")
        path = self.engine.state()["manuscript"][chapter_id]

        def apply(request):
            self.write(path, text)
            self.write("editorial/style-sheet.md", style)
            return self.finish_job(stage, chapter_id, path)

        return self.engine.advance(ScriptedRuntime(apply))

    def choose(self, command):
        return self.engine.reply(self.engine.state()["gate"]["id"], command)

    def start_editing(self, parts=None):
        english = self.base / "to-kill.en.md"
        self.parts = parts or ["## 1\n\nHe came back.\n", "## 2\n\nShe left.\n"]
        english.write_text("".join(self.parts), encoding="utf-8")
        self.engine.close()
        self.source, self.language = english, "en-US"
        self.run_id = self.service.create_run("literary-editing-v1", upload=english, manuscript_language="en-US")
        self.work_id = self.service._run_row(self.run_id)["work_id"]
        self.reopen()
        self.prepare()
        return self.engine.state()

    def design_result(self, request, *, work_record=None):
        ctx = json.loads(request.prompt[request.prompt.index('{\n  "stage"'):])
        relative = work_record or ctx["work_record"]
        proposal = proposal_for(self.workspace / relative)
        if ctx["previous_proposal"]:
            proposal = ctx["previous_proposal"]
            proposal["revision"] += 1
        apply_target(proposal, ctx["vendor_profile"], ctx["format_target"])
        self.write(ctx["proposal_path"], proposal)
        return result(state_path=ctx["proposal_path"], work_record=relative)

    def approve_editing(self):
        state = self.choose("finish")
        return self.engine.accept(state["acceptance_id"], confirm_final=True)

    def approved_docx_design(self):
        self.start_editing(["# One\n\nHe came back.\n", "# Two\n\nShe left.\n"])
        self.approve_editing()
        state = self.engine.advance(ScriptedRuntime(self.design_result))
        gate = state["gate"]
        proposal = self.engine.design_view(state)["proposal"]
        return self.engine.review_design(gate["id"], gate["binding"]["sha256"], "generate",
            answers={q["id"]: "Keep the proposal." for q in proposal["questions"] if q["blocking"]})

    def test_docx_single_request_records_plan_and_builds_candidate_before_final_approval(self):
        self.approved_docx_design()
        self.assertIsNone(self.engine.state().get("design_approval"))
        attempts = self.engine.state()["attempts"]
        request_state = self.engine.state()
        self.reopen()
        state = self.engine.advance(None)
        self.assertEqual((state["status"], state["attempts"]), ("WAITING_FOR_ACCEPTANCE", attempts))
        job = state["production"]
        self.assertEqual(state["receipts"], request_state["receipts"])
        self.assertEqual(job["authorization"], state["design_generation"]["receipt_id"])
        self.assertIsNone(state["gate"])
        self.assertEqual(json.loads(self.engine.store.content(job["plan"]))["plan_sha256"], job["plan_sha256"])
        self.reopen()
        self.engine.verify_docx_candidate(self.engine.state())
        self.assertIsNone(state.get("design_approval"))
        artifact = state["production"]["result"]["docx"]
        data, sha = self.service.docx_candidate(self.run_id, job["id"])
        self.assertEqual((digest(data), sha), (artifact["sha256"], artifact["sha256"]))
        self.assertEqual(self.service.library(self.work_id).finalized(), [])
        with self.assertRaises(WorkflowError):
            self.engine.accept(state["acceptance_id"])
        state = self.engine.accept(state["acceptance_id"], confirm_final=True)
        self.assertEqual(state["acceptance"]["docx"]["sha256"], sha)
        self.assertEqual(state["design_approval"]["receipt_id"], state["acceptance"]["id"])
        self.assertEqual(state["design_approval"]["docx_sha256"], sha)
        self.assertEqual(state["design_approval"]["proposal"]["sha256"], state["production"]["proposal_sha256"])
        state = self.engine.advance(None)
        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual((Path(state["export_path"]) / "document.docx").read_bytes(), data)
        published = self.service.library(self.work_id).head("literary-editing/v001/document.docx")
        self.assertEqual(self.service.library(self.work_id).read(published), data)

    def test_docx_inspection_reopens_saved_design_and_invalidates_old_candidate_and_acceptance(self):
        self.approved_docx_design()
        state = self.engine.advance(None)
        old = copy.deepcopy(state)
        job = old["production"]
        sha = job["result"]["docx"]["sha256"]
        protected = {key: copy.deepcopy(state[key]) for key in
                     ("manuscript_approval", "design_sources", "design_metadata", "format_target", "passes")}
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.reopen_design("old-acceptance", sha)
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.reopen_design(old["acceptance_id"], "0" * 64)
        with patch.object(self.engine, "publish_accepted", side_effect=WorkflowError("conflict", "Synthetic conflict")):
            with self.assertRaises(WorkflowError):
                self.engine.accept(old["acceptance_id"], confirm_final=True)
        self.assertIsNone(self.engine.state().get("design_approval"))
        self.engine.retry()
        # Retry re-enters the acceptance stage, giving it a fresh review identity.
        state = self.engine.advance(None)
        with patch.object(cli, "CodexRuntime", side_effect=AssertionError("Reopening must not start an agent")), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["--server-root", str(self.service.root), "--owner", "tester",
                "reopen-design", self.run_id, "--acceptance-id", state["acceptance_id"], "--docx-sha256", sha]), 0)
        state = self.engine.state()
        self.assertEqual(state["stage"], "interior-design")
        self.assertEqual(state["gate"]["kind"], "interior_design_review")
        self.assertIsNone(state.get("design_approval"))
        self.assertIsNone(state.get("design_generation"))
        self.assertNotIn("production", state)
        self.assertEqual(state["production_history"][-1], job)
        self.assertEqual(state["design_draft"], old["design_draft"])
        for key, value in protected.items():
            self.assertEqual(state[key], value)
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.accept(old["acceptance_id"], confirm_final=True)
        with self.assertRaisesRegex(ValueError, "No current DOCX"):
            self.service.docx_candidate(self.run_id, job["id"])
        gate = state["gate"]
        with self.assertRaisesRegex(ValueError, "Unknown"):
            self.engine.review_design(gate["id"], gate["binding"]["sha256"], "approve", answers={})
        view = self.engine.design_view(state)
        spec = {key: copy.deepcopy(view["proposal"][key]) for key in ("edition_brief", "design_system")}
        spec["role_styles"] = {role["id"]: role["style_id"] for role in view["proposal"]["text_roles"]}
        spec["design_system"]["page"]["gutter_mm"] += 1
        state = self.engine.review_design(gate["id"], view["sha256"], "save", spec=spec)
        gate = state["gate"]
        proposal = self.engine.design_view(state)["proposal"]
        self.engine.review_design(gate["id"], gate["binding"]["sha256"], "generate",
            answers={q["id"]: "Keep the proposed treatment." for q in proposal["questions"] if q["blocking"]})
        state = self.engine.advance(None)
        self.assertNotEqual(state["production"]["id"], job["id"])
        self.assertEqual(state["production"]["authorization"], state["design_generation"]["receipt_id"])
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.review_design(gate["id"], gate["binding"]["sha256"], "generate", answers={})
        self.assertNotEqual(state["production"]["result"]["docx"]["sha256"], sha)
        self.assertIsNone(state.get("design_approval"))
        state = self.engine.accept(state["acceptance_id"], confirm_final=True)
        self.assertEqual(state["design_approval"]["docx_sha256"], state["production"]["result"]["docx"]["sha256"])
        self.assertEqual(self.engine.store.content(job["result"]["docx"]), self.engine.store.content(
            state["production_history"][-1]["result"]["docx"]))
        with self.assertRaises(WorkflowError):
            self.engine.reopen_design(old["acceptance_id"], sha)

    def test_docx_request_and_plan_bindings_cannot_be_substituted_on_retry(self):
        self.approved_docx_design()
        with patch("book_formatter.build", side_effect=OSError("Synthetic disk failure")):
            with self.assertRaises(OSError):
                self.engine.advance(None)
        baseline = copy.deepcopy(self.engine.state())
        for field in ("design_request_id", "authorization"):
            with self.subTest(field=field):
                revision, _ = self.engine.store.load()
                changed = copy.deepcopy(baseline)
                changed["production"][field] = "unrelated-request"
                self.engine.store.save(revision, changed, "fixture.changed_binding")
                self.engine.retry()
                with patch("book_formatter.build") as build:
                    with self.assertRaisesRegex(ValueError, "generation"):
                        self.engine.advance(None)
                    build.assert_not_called()
                self.assertIsNone(self.engine.state()["production"]["result"])

    def test_existing_two_step_candidate_keeps_its_original_authorization_evidence(self):
        self.approved_docx_design()
        state = self.engine.advance(None)
        job = state["production"]
        receipt = {"id": "historical-authorization", "decision_source": "human",
                   "gate": {"kind": "docx_generation_review", "instance": job["id"], "binding": job["plan"]},
                   "parsed": {"type": "docx-generation", "plan_sha256": job["plan_sha256"],
                              "proposal_sha256": job["proposal_sha256"]}}
        state["receipts"].append(receipt)
        job["authorization"] = receipt["id"]
        manifest = json.loads(self.engine.store.content(job["result"]["manifest"]))
        manifest["generation_receipt_id"] = receipt["id"]
        path = self.base / "historical-manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        job["result"]["manifest"] = self.engine.store.snapshot(path, "docx_build")
        self.engine.verify_docx_candidate(state)
        receipt["decision_source"] = "delegated-automation"
        with self.assertRaisesRegex(ValueError, "authorization"):
            self.engine.verify_docx_candidate(state)

    def test_docx_failure_is_retryable_and_restart_invalidates_candidate_download(self):
        self.approved_docx_design()
        with patch("book_formatter.build", side_effect=OSError("Synthetic disk failure")):
            with self.assertRaisesRegex(OSError, "Synthetic"):
                self.engine.advance(None)
        state = self.engine.state()
        self.assertEqual(state["status"], "BLOCKED")
        self.assertIsNone(state["production"]["result"])
        with self.assertRaisesRegex(ValueError, "No current DOCX"):
            self.service.docx_candidate(self.run_id, state["production"]["id"])
        self.engine.retry()
        self.reopen()
        state = self.engine.advance(None)
        build_id = state["production"]["id"]
        self.assertEqual(state["production"]["attempts"], 2)
        self.engine.restart_stage("interior-design", reason="Revise the proposed layout")
        with self.assertRaisesRegex(ValueError, "No current DOCX"):
            self.service.docx_candidate(self.run_id, build_id)

    def test_docx_changed_before_sealing_is_never_offered_as_a_verified_candidate(self):
        self.approved_docx_design()
        snapshot = self.engine.store.snapshot

        def change_before_snapshot(path, role):
            if role == "editable_docx":
                path.write_bytes(b"External change after native verification")
            return snapshot(path, role)

        with patch.object(self.engine.store, "snapshot", side_effect=change_before_snapshot):
            with self.assertRaisesRegex(ValueError, "between formatter verification and sealing"):
                self.engine.advance(None)
        state = self.engine.state()
        self.assertIsNone(state["production"]["result"])
        self.assertEqual(self.service.library(self.work_id).finalized(), [])

    def test_docx_changed_effective_plan_blocks_retry_without_replanning_or_building(self):
        self.approved_docx_design()
        with patch("book_formatter.build", side_effect=OSError("Synthetic disk failure")):
            with self.assertRaises(OSError):
                self.engine.advance(None)
        old_job = copy.deepcopy(self.engine.state()["production"])
        self.engine.retry()
        data = json.loads(self.engine.store.content(old_job["plan"]))["plan"]
        data["policy"]["test_policy_change"] = True

        class ChangedPlan:
            sha256 = digest(json.dumps(data, sort_keys=True).encode())

            def to_dict(self):
                return copy.deepcopy(data)

        with patch("book_formatter.prepare", return_value=ChangedPlan()), patch("book_formatter.build") as build:
            with self.assertRaisesRegex(ValueError, "inputs changed"):
                self.engine.advance(None)
            build.assert_not_called()
        state = self.engine.state()
        self.assertEqual(state["status"], "BLOCKED")
        self.assertIsNone(state["gate"])
        self.assertEqual(state["production"]["id"], old_job["id"])
        self.assertEqual(state["production"]["plan_sha256"], old_job["plan_sha256"])
        self.assertIsNone(state["production"]["result"])

    def test_docx_cli_builds_directly_without_an_authorization_command_or_agent_runtime(self):
        for configured in (False, True):
            with self.subTest(execution_profile=configured):
                self.approved_docx_design()
                prefix = ["--server-root", str(self.service.root), "--owner", "tester"]
                if configured:
                    data = profile_data()
                    data["models"][0]["workflows"] = ["literary-editing"]
                    path = self.base / "native-profile.json"
                    path.write_text(json.dumps(data), encoding="utf-8")
                    prefix += ["--execution-profile", str(path)]
                with patch.object(cli, "CodexRuntime", side_effect=AssertionError("No native runtime")), \
                        patch.object(ExecutionProfile, "runtime", side_effect=AssertionError("No profile runtime")), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(cli.main(prefix + ["step", self.run_id]), 0)
                self.assertEqual(self.engine.state()["status"], "WAITING_FOR_ACCEPTANCE")

    def test_docx_unsupported_content_blocks_without_silent_partial_delivery(self):
        self.start_editing(["# One\n\n- A list item is outside the POC.\n"])
        self.approve_editing()
        state = self.engine.advance(ScriptedRuntime(self.design_result))
        gate = state["gate"]
        proposal = self.engine.design_view(state)["proposal"]
        self.engine.review_design(gate["id"], gate["binding"]["sha256"], "generate",
            answers={q["id"]: "Keep the proposal." for q in proposal["questions"] if q["blocking"]})
        with self.assertRaisesRegex(ValueError, "unsupported_content"):
            self.engine.advance(None)
        state = self.engine.state()
        self.assertEqual(state["status"], "BLOCKED")
        self.assertNotIn("production", state)
        self.assertEqual(self.service.library(self.work_id).finalized(), [])

    def test_workflow_rejects_pdf_bundle_instead_of_partial_docx_success(self):
        self.start_editing()
        self.approve_editing()

        def bundle(request):
            outcome = self.design_result(request)
            path = self.workspace / outcome["state_path"]
            proposal = json.loads(path.read_bytes())
            pdf = copy.deepcopy(proposal["edition_brief"]["production_targets"][0])
            pdf.update(id="pdf", format="print-interior-pdf")
            proposal["edition_brief"]["production_targets"].append(pdf)
            self.write(outcome["state_path"], proposal)
            return outcome

        with self.assertRaisesRegex(ValueError, "exactly one editable-DOCX"):
            self.engine.advance(ScriptedRuntime(bundle))

    def test_design_roles_bind_whole_paragraphs_and_preserve_inline_markers(self):
        self.start_editing(["## 1\n\nHe *came* **back**.\n", "## 2\n\nShe *left*.\n"])
        self.approve_editing()

        def design(request):
            self.assertIn("--list-paragraphs", request.prompt)
            self.assertIn("Do not generate inline roles", request.prompt)
            self.assertIn("book-title", request.prompt)
            self.assertIn("page-x-of-y", request.prompt)
            context = json.loads(request.prompt[request.prompt.index('{\n  "stage"'):])
            state = self.engine.state()
            self.assertEqual([unit["role"] for unit in context["manuscript"]],
                             [unit["role"] for unit in state["chapters"]])
            self.assertTrue(all(source["role"] == "edited_chapter"
                                for source in state["design_sources"].values()))
            return self.design_result(request)

        state = self.engine.advance(ScriptedRuntime(design))
        proposal = self.engine.design_view(state)["proposal"]
        self.assertEqual(proposal["contract"], "interior-design-proposal/5")
        occurrence = proposal["text_roles"][0]["occurrences"][0]
        self.assertEqual(occurrence["paragraph_index"], 2)
        self.assertEqual(occurrence["paragraph_sha256"], digest(b"She *left*."))
        self.assertNotIn("start_byte", occurrence)
        for index, source in enumerate(self.parts, 1):
            item = state["design_sources"][f"chapter-{index}"]
            self.assertEqual(self.engine.file(item["path"]).read_text(encoding="utf-8"), source)

    def test_design_review_preserves_zero_and_nonzero_widow_orphan_inputs(self):
        self.start_editing()
        self.approve_editing()
        state = self.engine.advance(ScriptedRuntime(self.design_result))
        for widow, orphan in ((0, 7), (0, 0)):
            view = self.engine.design_view(state)
            spec = {key: copy.deepcopy(view["proposal"][key]) for key in ("edition_brief", "design_system")}
            spec["role_styles"] = {role["id"]: role["style_id"] for role in view["proposal"]["text_roles"]}
            spec["design_system"]["styles"][0]["paragraph"].update(widow_lines=widow, orphan_lines=orphan)
            state = self.engine.review_design(state["gate"]["id"], view["sha256"], "save", spec=spec)
            saved = self.engine.design_view(state)["proposal"]["design_system"]["styles"][0]["paragraph"]
            self.assertEqual((saved["widow_lines"], saved["orphan_lines"]), (widow, orphan))

    def test_design_cannot_submit_inline_role_ranges(self):
        self.start_editing()
        self.approve_editing()

        def inline_role(request):
            output = self.design_result(request)
            proposal = json.loads(self.engine.file(output["state_path"]).read_bytes())
            proposal["text_roles"][0]["occurrences"][0].update(start_byte=8, end_byte=10)
            self.write(output["state_path"], proposal)
            return output

        with self.assertRaisesRegex(ValueError, "Additional properties"):
            self.engine.advance(ScriptedRuntime(inline_role))
        self.assertNotIn("design_draft", self.engine.state())
        self.assertIsNone(self.engine.state().get("design_approval"))

    def test_purpose_is_supplied_before_authoring_and_fixed_during_review(self):
        self.start_editing()
        state = self.choose("finish")
        selection = {"purpose": "submission", "vendor_id": None, "binding": "paperback"}
        state = self.engine.accept(state["acceptance_id"], confirm_final=True, format_target=selection)
        approval = state["manuscript_approval"]

        def design(request):
            ctx = json.loads(request.prompt[request.prompt.index('{\n  "stage"'):])
            self.assertEqual(ctx["format_target"]["purpose"], "submission")
            self.assertIn("recipient", ctx["purpose_guidance"])
            self.assertIn("edition_brief.purpose", request.prompt)
            return self.design_result(request)

        state = self.engine.advance(ScriptedRuntime(design))
        proposal = self.engine.design_view(state)["proposal"]
        self.assertEqual(proposal["edition_brief"]["purpose"], "submission")
        gate = state["gate"]
        spec = {k: copy.deepcopy(proposal[k]) for k in ("edition_brief", "design_system")}
        spec["role_styles"] = {r["id"]: r["style_id"] for r in proposal["text_roles"]}
        spec["edition_brief"]["purpose"] = "print-ready"
        with self.assertRaisesRegex(ValueError, "selected purpose"):
            self.engine.review_design(gate["id"], gate["binding"]["sha256"], "save", spec=spec)
        with self.assertRaisesRegex(ValueError, "Unknown"):
            self.engine.review_design(gate["id"], gate["binding"]["sha256"], "select-target")
        state = self.engine.review_design(gate["id"], gate["binding"]["sha256"], "request-revision",
                                          feedback="Use more annotation space without changing the purpose.")
        state = self.engine.advance(ScriptedRuntime(self.design_result))
        self.assertEqual(self.engine.design_view(state)["proposal"]["edition_brief"]["purpose"], "submission")
        self.assertEqual(state["manuscript_approval"], approval)

    def test_ingramspark_variant_is_pinned_and_entry_fields_are_read_only(self):
        self.start_editing()
        state = self.choose("finish")
        for invalid in ({"purpose": "print-ready", "vendor_id": "ingramspark", "binding": "dust-jacket"},
                        {"purpose": "print-ready", "vendor_id": "other", "binding": "paperback"},
                        {"purpose": "print-ready", "vendor_id": "ingramspark", "binding": "paperback", "variant_id": "hardcover"},
                        {"purpose": [], "vendor_id": None, "binding": "paperback"}):
            with self.subTest(target=invalid), self.assertRaises(ValueError):
                self.engine.accept(state["acceptance_id"], confirm_final=True, format_target=invalid)
        self.assertNotIn("manuscript_approval", self.engine.state())
        state = self.engine.accept(state["acceptance_id"], confirm_final=True,
                                   format_target={"purpose": "print-ready", "vendor_id": "ingramspark", "binding": "paperback"})
        manuscript_approval = state["manuscript_approval"]
        self.assertEqual(self.engine.selected_vendor_profile(state)["variant_id"], "paperback")
        state = self.engine.advance(ScriptedRuntime(self.design_result))
        proposal = self.engine.design_view(state)["proposal"]
        self.assertEqual(proposal["vendor_profile"]["variant_id"], "paperback")
        spec = {k: copy.deepcopy(proposal[k]) for k in ("edition_brief", "design_system")}
        spec["role_styles"] = {r["id"]: r["style_id"] for r in proposal["text_roles"]}
        spec["design_system"]["page"]["gutter_mm"] = 5
        gate = state["gate"]
        state = self.engine.review_design(gate["id"], gate["binding"]["sha256"], "save", spec=spec)
        gate = state["gate"]
        for field, value in (("id", "different-target"), ("vendor_id", "other"), ("binding", "hardcover"),
                             ("vendor_profile_ref", None)):
            candidate = copy.deepcopy(spec)
            candidate["edition_brief"]["production_targets"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.engine.review_design(gate["id"], gate["binding"]["sha256"], "save", spec=candidate)
            self.assertEqual(self.engine.state()["gate"]["id"], gate["id"])
        state = self.engine.review_design(gate["id"], gate["binding"]["sha256"], "request-revision",
                                          feedback="Refine typography within the selected target.")
        self.assertEqual(state["manuscript_approval"], manuscript_approval)
        state = self.engine.advance(ScriptedRuntime(self.design_result))
        proposal = self.engine.design_view(state)["proposal"]
        self.assertEqual(proposal["vendor_profile"]["variant_id"], "paperback")
        self.assertEqual(proposal["edition_brief"]["production_targets"][0]["binding"], "paperback")
        self.assertEqual(proposal["design_system"]["page"]["gutter_mm"], 5)
        profile = state["design_vendor_profile"]
        profile_bytes = self.engine.store.content(profile)
        state = self.engine.restart_stage("interior-design", reason="Recheck design")
        self.assertEqual(state["design_vendor_profile"], profile)
        self.assertEqual(state["manuscript_approval"], manuscript_approval)
        self.assertEqual(self.engine.file(profile["path"]).read_bytes(), profile_bytes)
        self.reopen()
        state = self.engine.advance(ScriptedRuntime(self.design_result))
        self.assertEqual((state["status"], state["gate"]["kind"]), ("WAITING_FOR_HUMAN", "interior_design_review"))
        self.assertEqual(self.engine.design_view(state)["proposal"]["vendor_profile"]["sha256"],
                         json.loads(profile_bytes)["sha256"])
        self.assertEqual(state["manuscript_approval"], manuscript_approval)
        state = self.engine.restart_stage("approve-manuscript", reason="Choose a new target")
        self.assertNotIn("design_vendor_profile", state)
        self.assertFalse((self.workspace / profile["path"]).exists())

    def test_design_cannot_replace_user_selected_vendor_variant(self):
        self.start_editing()
        state = self.choose("finish")
        self.engine.accept(state["acceptance_id"], confirm_final=True,
                           format_target={"purpose": "print-ready", "vendor_id": "ingramspark", "binding": "paperback"})

        def wrong_variant(request):
            output = self.design_result(request)
            proposal = json.loads(self.engine.file(output["state_path"]).read_bytes())
            profile = self.engine.interior_validator.vendor_profiles().resolve("ingramspark", "hardcover")
            apply_target(proposal, profile, {"purpose": "print-ready", "vendor_id": "ingramspark", "binding": "hardcover"})
            self.write(output["state_path"], proposal)
            return output

        with self.assertRaisesRegex(ValueError, "user-selected"):
            self.engine.advance(ScriptedRuntime(wrong_variant))
        self.assertNotIn("design_draft", self.engine.state())
        self.assertIsNone(self.engine.state().get("design_approval"))

    def test_interior_design_zero_pass_edit_save_stale_gate_and_approval(self):
        state = self.start_editing(["# One\n\nHe came back.\n", "# Two\n\nShe left.\n"])
        prepared = {p: s["sha256"] for p, s in state["prepared"]["files"].items()}
        with self.assertRaisesRegex(ValueError, "Reply with exactly"):
            self.choose("proceed to formatting")
        state = self.choose("finish")
        self.assertEqual((state["stage"], state["status"]), ("approve-manuscript", "WAITING_FOR_ACCEPTANCE"))
        self.assertFalse(self.engine.acceptance_details(state)["finalizes"])
        self.assertEqual(self.engine.acceptance_details(state)["format_target"]["purpose"], "print-ready")
        with contextlib.redirect_stdout(io.StringIO()) as approval_copy:
            cli.display(self.engine, state, review=True)
        self.assertIn("Approval freezes the manuscript", approval_copy.getvalue())
        self.assertNotIn("manuscript_approval", state)
        with self.assertRaises(WorkflowError) as unconfirmed:
            self.engine.accept(state["acceptance_id"])
        self.assertEqual(unconfirmed.exception.code, "confirmation_required")
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.accept("wrong-id", confirm_final=True)
        state = self.engine.accept(state["acceptance_id"], confirm_final=True)
        self.assertEqual((state["stage"], state["status"], len(state["passes"])), ("interior-design", "READY", 0))
        self.assertFalse(self.engine.finalized(state))
        self.assertEqual(state["manuscript_approval"]["hashes"], [o["sha256"] for o in state["outputs"]])
        self.assertEqual(self.service.library(self.work_id).finalized(), [])

        def design(request):
            self.assertIn("interior-design", request.prompt)
            ctx = json.loads(request.prompt[request.prompt.index('{\n  "stage"'):])
            self.assertFalse(ctx["preparation_required"])
            self.assertTrue(all(self.engine.file(c["path"]).is_file() for c in ctx["manuscript"]))
            return self.design_result(request)

        state = self.engine.advance(ScriptedRuntime(design))
        gate = state["gate"]
        self.assertEqual((state["status"], gate["kind"]), ("WAITING_FOR_HUMAN", "interior_design_review"))
        with self.assertRaisesRegex(ValueError, "form"):
            self.engine.reply(gate["id"], "approve design")
        view = self.engine.design_view(state)
        proposal = view["proposal"]
        work_before = self.engine._work_path(state).read_bytes()
        with self.assertRaisesRegex(ValueError, "Restart manuscript approval"):
            self.engine.edit_metadata("/title", "Changed title", reason="Explicit correction")
        self.assertEqual(self.engine._work_path(state).read_bytes(), work_before)
        spec = {k: proposal[k] for k in ("edition_brief", "design_system")}
        spec["role_styles"] = {r["id"]: r["style_id"] for r in proposal["text_roles"]}
        spec["design_system"]["page"]["gutter_mm"] = 5
        spec["design_system"]["styles"][0]["font"]["size_pt"] = 12
        state = self.engine.review_design(gate["id"], view["sha256"], "save", spec=spec)
        updated = self.engine.design_view(state)["proposal"]
        self.assertEqual(updated["revision"], proposal["revision"] + 1)
        self.assertEqual(updated["design_system"]["page"]["gutter_mm"], 5)
        self.assertEqual(updated["design_system"]["styles"][0]["font"]["size_pt"], 12)
        self.assertEqual(updated["basis"], proposal["basis"])
        self.assertNotEqual(state["gate"]["id"], gate["id"])
        self.assertEqual(json.loads(self.engine.store.content(gate["binding"]))["design_system"]["page"]["gutter_mm"], 3)
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.review_design(gate["id"], view["sha256"], "generate", answers={})
        gate = state["gate"]
        with self.assertRaisesRegex(ValueError, "every blocking question"):
            self.engine.review_design(gate["id"], gate["binding"]["sha256"], "generate", answers={})
        answers = {q["id"]: "Keep the proposed new-page openings." for q in updated["questions"] if q["blocking"]}
        state = self.engine.review_design(gate["id"], gate["binding"]["sha256"], "generate", answers=answers)
        self.assertEqual((state["stage"], state["status"]), ("produce-docx", "READY"))
        self.assertFalse(self.engine.finalized(state))
        self.assertEqual(state["design_generation"]["proposal"]["sha256"], gate["binding"]["sha256"])
        self.assertIsNone(state.get("design_approval"))
        self.assertEqual(len(state["outputs"]), len(state["chapters"]))  # Approved Markdown, not generated documents.
        self.assertNotIn("acceptance", state)
        attempts = state["attempts"]
        state = self.engine.advance(None)  # Production cannot accidentally invoke an agent.
        self.assertEqual((state["status"], state["attempts"]), ("WAITING_FOR_ACCEPTANCE", attempts))
        self.assertIsNone(state["gate"])
        for path, sha in prepared.items():
            self.assertEqual(digest(self.engine.file(path).read_bytes()), sha)
        self.assertEqual(self.engine.state()["receipts"][-1]["decision_source"], "human")
        self.engine.cancel()
        with self.assertRaisesRegex(ValueError, "CANCELLED"):
            self.engine.advance(None)
        self.assertEqual(self.engine.state()["status"], "CANCELLED")

    def test_design_without_author_questions_needs_no_technical_acknowledgements(self):
        self.start_editing()
        self.approve_editing()

        def design(request):
            output = self.design_result(request)
            proposal = json.loads(self.engine.file(output["state_path"]).read_bytes())
            proposal["questions"] = []
            self.write(output["state_path"], proposal)
            return output

        state = self.engine.advance(ScriptedRuntime(design))
        gate = state["gate"]
        state = self.engine.review_design(gate["id"], gate["binding"]["sha256"], "generate", answers={})
        self.assertEqual((state["stage"], state["status"]), ("produce-docx", "READY"))
        self.assertIsNone(state["error"])
        self.assertEqual(state["receipts"][-1]["parsed"]["answers"], {})
        self.assertFalse(self.engine.finalized(state))

    def test_cli_design_review_saves_revises_and_approves_exact_proposal(self):
        self.start_editing(["# One\n\nHe came back.\n", "# Two\n\nShe left.\n"])
        self.approve_editing()
        state = self.engine.advance(ScriptedRuntime(self.design_result))
        prefix = ["--server-root", str(self.service.root), "--owner", "tester"]
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(prefix + ["review", self.run_id]), 0)
        self.assertIn("review-design", output.getvalue())
        self.assertIn(state["gate"]["binding"]["sha256"], output.getvalue())
        proposal = self.engine.design_view(state)["proposal"]
        self.assertIn(proposal["proposal_id"], output.getvalue())
        spec = {k: copy.deepcopy(proposal[k]) for k in ("edition_brief", "design_system")}
        spec["role_styles"] = {r["id"]: r["style_id"] for r in proposal["text_roles"]}
        spec["design_system"]["page"]["gutter_mm"] = 5
        spec_path = self.base / "design-spec.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        original_gate = state["gate"]

        def review_args(action, gate):
            return prefix + ["review-design", self.run_id, "--action", action, "--gate", gate["id"],
                             "--proposal-sha256", gate["binding"]["sha256"]]

        with patch.object(cli, "CodexRuntime", side_effect=AssertionError("Review must not run an agent")), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(review_args("save", original_gate) + ["--spec-file", str(spec_path)]), 0)
            saved = self.engine.state()
            self.assertNotEqual(saved["gate"]["id"], original_gate["id"])
            self.assertEqual(self.engine.design_view(saved)["proposal"]["design_system"]["page"]["gutter_mm"], 5)
            self.assertEqual(cli.main(review_args("generate", original_gate)), 1)
            self.assertEqual(self.engine.state(), saved)
            feedback = self.base / "design-feedback.txt"
            feedback.write_text("Keep my gutter; refine the typography.", encoding="utf-8")
            self.assertEqual(cli.main(review_args("request-revision", saved["gate"]) +
                                      ["--feedback-file", str(feedback)]), 0)
        state = self.engine.state()
        self.assertEqual((state["status"], state["next_input"]["text"]), ("READY", feedback.read_text(encoding="utf-8")))
        state = self.engine.advance(ScriptedRuntime(self.design_result))
        gate = state["gate"]
        proposal = self.engine.design_view(state)["proposal"]
        self.assertEqual(proposal["design_system"]["page"]["gutter_mm"], 5)
        answers = self.base / "design-answers.json"
        answers.write_text(json.dumps({q["id"]: "Keep the proposed opening." for q in proposal["questions"]
                                       if q["blocking"]}), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(cli.main(review_args("generate", gate)), 1)  # Blocking answers cannot be bypassed.
            self.assertEqual(self.engine.state(), state)
            self.assertEqual(cli.main(review_args("generate", gate) + ["--answers-file", str(answers)]), 0)
            state = self.engine.state()
            self.assertEqual((state["stage"], state["status"]), ("produce-docx", "READY"))
            self.assertEqual(state["design_generation"]["proposal"]["sha256"], gate["binding"]["sha256"])
            self.assertIsNone(state.get("design_approval"))
            self.assertEqual(state["receipts"][-1]["decision_source"], "human")
            with patch.object(cli, "CodexRuntime", side_effect=AssertionError("Native planning needs no agent")):
                self.assertEqual(cli.main(prefix + ["step", self.run_id]), 0, errors.getvalue())
        self.assertEqual(self.engine.state()["status"], "WAITING_FOR_ACCEPTANCE")

    def test_cli_design_review_validates_action_files_and_allows_no_questions(self):
        self.start_editing()
        self.approve_editing()

        def design(request):
            result = self.design_result(request)
            proposal = json.loads(self.engine.file(result["state_path"]).read_bytes())
            proposal["questions"] = []
            self.write(result["state_path"], proposal)
            return result

        state = self.engine.advance(ScriptedRuntime(design))
        gate = state["gate"]
        prefix = ["--server-root", str(self.service.root), "review-design", self.run_id,
                  "--gate", gate["id"], "--proposal-sha256", gate["binding"]["sha256"]]
        invalid = self.base / "invalid-design.json"
        invalid.write_text("not JSON", encoding="utf-8")
        for args in (["--action", "save"], ["--action", "request-revision"],
                     ["--action", "generate", "--spec-file", str(invalid)],
                     ["--action", "save", "--answers-file", str(invalid)],
                     ["--action", "generate", "--answers-file", str(invalid)]):
            with self.subTest(args=args), contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(prefix + args), 1)
                self.assertEqual(self.engine.state(), state)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(prefix + ["--action", "generate"]), 0)
        self.assertEqual(self.engine.state()["receipts"][-1]["parsed"]["answers"], {})
        self.assertEqual(self.engine.state()["stage"], "produce-docx")

    def test_interior_design_refuses_invalid_settings_and_supports_revision(self):
        self.start_editing()
        self.approve_editing()
        state = self.engine.advance(ScriptedRuntime(self.design_result))
        gate = state["gate"]
        proposal = self.engine.design_view(state)["proposal"]
        spec = {k: proposal[k] for k in ("edition_brief", "design_system")}
        spec["role_styles"] = {r["id"]: r["style_id"] for r in proposal["text_roles"]}
        spec["design_system"]["page"]["margins_mm"]["inside"] = 200
        with self.assertRaises(ValueError):
            self.engine.review_design(gate["id"], gate["binding"]["sha256"], "save", spec=spec)
        self.assertEqual(self.engine.state()["gate"]["id"], gate["id"])
        with self.assertRaisesRegex(ValueError, "only"):
            self.engine.review_design(gate["id"], gate["binding"]["sha256"], "save", spec={"basis": {}})
        state = self.engine.review_design(gate["id"], gate["binding"]["sha256"], "request-revision",
                                          feedback="Use a quieter heading and preserve my settings.")
        self.assertEqual(state["status"], "READY")
        state = self.engine.advance(ScriptedRuntime(self.design_result))
        self.assertEqual(self.engine.design_view(state)["proposal"]["revision"], 2)
        self.assertNotEqual(state["gate"]["id"], gate["id"])
        metadata_path = self.engine._work_path(state)
        original_metadata = metadata_path.read_bytes()
        tampered = json.loads(original_metadata)
        tampered["metadata"]["title"] = "Changed outside the human review"
        metadata_path.write_bytes(json.dumps(tampered).encode())
        with self.assertRaisesRegex(ValueError, "frozen interior-design metadata"):
            self.engine.review_design(state["gate"]["id"], state["gate"]["binding"]["sha256"], "generate", answers={})
        metadata_path.write_bytes(original_metadata)
        self.engine.file(state["manuscript"]["chapter-1"]).write_bytes(b"Tampered manuscript\n")
        with self.assertRaisesRegex(ValueError, "frozen"):
            self.engine.review_design(state["gate"]["id"], state["gate"]["binding"]["sha256"], "generate", answers={})

    def test_formatting_approval_freezes_basis_before_agent_and_survives_design_restart(self):
        self.start_editing()
        with self.assertRaisesRegex(ValueError, "Approve the manuscript"):
            self.engine.prepare_design_turn(self.engine.state())
        state = self.approve_editing()
        approval = state["manuscript_approval"]
        path = self.engine.file(state["manuscript"]["chapter-1"])
        before = path.read_bytes()
        path.write_bytes(b"Changed after approval\n")
        with self.assertRaisesRegex(ValueError, "frozen"):
            self.engine.advance(None)
        path.write_bytes(before)
        state = self.engine.restart_stage("interior-design", reason="Propose the layout again")
        self.assertEqual(state["manuscript_approval"], approval)
        self.assertTrue(state["design_sources"])
        state = self.engine.restart_stage("approve-manuscript", reason="Reopen manuscript approval")
        self.assertNotIn("manuscript_approval", state)
        self.assertNotIn("design_sources", state)
        self.assertNotEqual(state["acceptance_id"], approval["id"])
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.accept(approval["id"], confirm_final=True)

    def test_interior_design_after_pass_requires_matching_output_preparation(self):
        self.start_editing()
        self.choose("run line")
        for _ in range(4):
            state = self.approve_empty_job("line")
        with self.assertRaisesRegex(ValueError, "Reply with exactly"):
            self.choose("finish")
        self.choose("accept pass")
        self.approve_editing()
        # A deliberately wrong proposal cannot silently bind a different source.
        def bad(request):
            response = self.design_result(request)
            proposal = json.loads(self.engine.file(response["state_path"]).read_bytes())
            proposal["basis"]["preparation"]["record_revision"] += 1
            self.write(response["state_path"], proposal)
            return response
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.engine.advance(ScriptedRuntime(bad))

    def test_interior_design_prepares_exact_accepted_edited_text_without_overwriting_original(self):
        self.start_editing()
        self.choose("run line")
        self.approve_empty_job("line")
        self.apply_change("line", "chapter-1", "## 1\n\nHe returned.\n", "# Approved style\n")
        self.approve_empty_job("line")
        self.approve_empty_job("line")
        self.choose("accept pass")
        self.approve_editing()

        def stale(request):
            ctx = json.loads(request.prompt[request.prompt.index('{\n  "stage"'):])
            self.assertTrue(ctx["preparation_required"])
            return self.design_result(request)  # Still bound to original preparation: must not pass.

        with self.assertRaisesRegex(ValueError, "exact selected manuscript"):
            self.engine.advance(ScriptedRuntime(stale))
        self.engine.retry()
        original_work = self.engine._work_path(self.engine.state()).read_bytes()

        def reprepare(request):
            ctx = json.loads(request.prompt[request.prompt.index('{\n  "stage"'):])
            work = json.loads(original_work)
            previous = self.engine._work_path(self.engine.state()).parent / "revisions/r0001/manifest.json"
            manifest = json.loads(previous.read_bytes())
            work["preparation"]["current_revision"] = "r0002"
            folder = ctx["output_preparation_root"] + "/accepted"
            work["discovery"].update(location_kind="directory", location=str(self.workspace / "manuscript/chapters"))
            manifest.update(revision="r0002", sources=[])
            for chapter, source in zip(manifest["chapters"], ctx["manuscript"]):
                data = self.engine.file(source["path"]).read_text(encoding="utf-8")
                self.assertEqual(source["role"], chapter["role"])
                for key in ("chapter_id", "order", "role", "title"):
                    chapter[key] = source[key]
                chapter["sha256"] = digest(data.encode())
                chapter["source_spans"] = [{"source_id": chapter["chapter_id"], "locator": "Whole accepted unit"}]
                self.write(folder + "/revisions/r0002/" + chapter["file"], data)
                manifest["sources"].append({"source_id": chapter["chapter_id"],
                                            "locator": str(self.engine.file(source["path"])), "format": "markdown",
                                            "identity": {"kind": "sha256", "value": chapter["sha256"]}})
            self.write(folder + "/revisions/r0002/manifest.json", manifest)
            relative = self.write(folder + "/work.json", work)
            return self.design_result(request, work_record=relative)

        state = self.engine.advance(ScriptedRuntime(reprepare))
        self.assertEqual(state["gate"]["kind"], "interior_design_review")
        proposal = self.engine.design_view(state)["proposal"]
        self.assertEqual(proposal["basis"]["preparation"]["revision"], "r0002")
        self.assertEqual(self.engine._work_path(state).read_bytes(), original_work)
        self.assertNotEqual(state["design_work_record"], state["prepared"]["work_record"])
        self.assertEqual(proposal["basis"]["preparation"]["units"][1]["sha256"], digest(b"## 1\n\nHe returned.\n"))

    def test_literary_editing_passes_are_chosen_accepted_and_repeatable(self):
        state = self.start_editing()
        self.assertEqual(self.engine.stage_ids(state), ["prepare", "metadata", "analysis", "passes", "approve-manuscript", "interior-design", "produce-docx", "accept", "export"])
        # After metadata review the user chooses a pass, or proceeds to manuscript approval.
        self.assertEqual((state["stage"], state["status"], state["gate"]["kind"]), ("passes", "WAITING_FOR_HUMAN", "pass_choice"))
        self.assertEqual(self.engine.gate_commands(state, state["gate"]),
                         ["run developmental", "run line", "run copy", "finish"])
        self.assertEqual(state["gate"]["options"][-1]["title"], "Review manuscript")
        with self.assertRaisesRegex(ValueError, "Reply with exactly one of"):
            self.choose("run everything")

        state = self.choose("run line")
        self.assertEqual((state["stage"], state["status"]), ("line", "READY"))
        self.assertEqual([(p["number"], p["stage"], p["epoch"]) for p in state["passes"]], [(1, "line", 1)])
        chapter_1, chapter_2 = state["manuscript"]["chapter-1"], state["manuscript"]["chapter-2"]
        self.assertEqual(self.engine.file(chapter_1).read_text(encoding="utf-8"), self.parts[0])  # Verbatim intake.
        self.assertEqual([i["chapter_id"] for i in state["iterations"]], ["front-matter", "chapter-1", "chapter-2", "_whole"])
        self.approve_empty_job("line")  # The front matter has nothing to edit.

        # Chapter 1: proposal review, explicit apply authorization, then application. A reopening decision does
        # not close the review; a complete resolving submission is its closure, with no separate confirmation.
        self.engine.advance(ScriptedRuntime(lambda r: self.editorial_review("line", "chapter-1")))
        self.engine.reply(self.engine.state()["gate"]["id"], "LE-001 revise proposal: keep the plain verb")
        self.assertNotIn("editorial_review", self.engine.state()["approvals"])
        with self.assertRaisesRegex(ValueError, "Decision closure is required"):
            self.engine.advance(ScriptedRuntime(lambda r: self.apply_gate("line", "chapter-1", "Apply?")))
        self.engine.retry()
        self.engine.advance(ScriptedRuntime(lambda r: self.editorial_review("line", "chapter-1", "2")))
        self.engine.reply(self.engine.state()["gate"]["id"], "LE-001 accept")
        state = self.engine.state()
        self.assertIn("editorial_review", state["approvals"])
        self.assertTrue(state["receipts"][-1]["parsed"]["implied_closure"])
        self.engine.advance(ScriptedRuntime(lambda r: self.apply_gate("line", "chapter-1")))
        self.engine.reply(self.engine.state()["gate"]["id"], "go ahead")  # Not the exact command: feedback only.
        self.assertNotIn("apply_authorization", self.engine.state()["approvals"])
        self.engine.advance(ScriptedRuntime(lambda r: self.apply_gate("line", "chapter-1", "Reply exactly 'apply accepted changes'.")))
        self.engine.reply(self.engine.state()["gate"]["id"], "apply accepted changes")

        def apply(request):
            self.write(chapter_1, "## 1\n\nHe returned.\n")
            self.write("editorial/style-sheet.md", "# Style sheet\n- returned (approved)\n")
            return self.finish_job("line", "chapter-1", chapter_1)

        state = self.engine.advance(ScriptedRuntime(apply))
        self.assertEqual(state["iterations"][1]["changed"], [chapter_1])
        self.assertEqual(state["outputs"], [])  # Text can change in any pass until final acceptance.
        self.assertTrue((self.workspace / "editorial/passes/001-line/chapter-1/application-report.md").is_file())

        # A pending chapter cannot change outside its job; an unauthorized change cannot complete.
        self.write(chapter_2, "## 2\n\nTampered.\n")
        with self.assertRaisesRegex(ValueError, "changed outside its approved editorial job"):
            self.engine.advance(ScriptedRuntime(lambda r: self.empty_review("line", "chapter-2")))
        self.write(chapter_2, self.parts[1])
        self.engine.advance(ScriptedRuntime(lambda r: self.empty_review("line", "chapter-2")))
        self.engine.reply(self.engine.state()["gate"]["id"], "approve review")

        def unauthorized(request):
            self.write(chapter_2, "## 2\n\nShe departed.\n")
            return self.finish_job("line", "chapter-2", chapter_2)

        with self.assertRaisesRegex(ValueError, "without an explicit apply authorization"):
            self.engine.advance(ScriptedRuntime(unauthorized))
        self.write(chapter_2, self.parts[1])
        self.engine.retry()
        self.engine.advance(ScriptedRuntime(lambda r: self.finish_job("line", "chapter-2", chapter_2)))
        with self.assertRaisesRegex(ValueError, "planned for M4"):
            self.engine.restart_chapter("chapter-1", reason="x")

        # The whole-book pass ends the pass; its output is accepted in a separate decision.
        state = self.approve_empty_job("line")
        self.assertEqual((state["stage"], state["gate"]["kind"]), ("passes", "pass_review"))
        self.assertIn("Changed chapters: chapter-1.", state["gate"]["message"])
        self.assertEqual(self.engine.gate_commands(state, state["gate"]), ["accept pass"])
        self.write(chapter_1, "## 1\n\nEdited by hand.\n")
        with self.assertRaisesRegex(ValueError, "changed outside an editorial pass"):
            self.choose("accept pass")
        self.write(chapter_1, "## 1\n\nHe returned.\n")
        with self.assertRaisesRegex(ValueError, "restart the workflow"):
            self.engine.restart_stage("metadata", reason="x")
        with self.assertRaisesRegex(ValueError, "Restart the pass in progress"):
            self.engine.restart_stage("passes", reason="x")
        state = self.choose("accept pass")
        self.assertEqual(state["gate"]["kind"], "pass_choice")
        self.assertEqual(len(state["passes"][0]["iterations"]), 4)
        self.assertEqual(state["iterations"], [])
        with self.assertRaisesRegex(ValueError, "accepted passes are final"):
            self.engine.restart_stage("line", reason="x")

        # A copy pass starts from the accepted line edit; restarting it returns text and style sheet to that start.
        self.choose("run copy")
        self.approve_empty_job("copy")
        state = self.apply_change("copy", "chapter-1", "## 1\n\nHe returned home.\n", "# Style sheet\n- home\n")
        self.assertEqual(self.engine.file(chapter_1).read_text(encoding="utf-8"), "## 1\n\nHe returned home.\n")
        state = self.engine.restart_stage("copy", reason="Redo the copy edit")
        self.assertEqual((state["stage"], state["status"]), ("copy", "READY"))
        self.assertEqual(self.engine.file(chapter_1).read_text(encoding="utf-8"), "## 1\n\nHe returned.\n")
        self.assertEqual((self.workspace / "editorial/style-sheet.md").read_text(encoding="utf-8"),
                         "# Style sheet\n- returned (approved)\n")
        self.assertEqual((state["passes"][1]["restarts"], state["stage_epochs"]["copy"]), (1, 2))
        for _ in range(4):
            state = self.approve_empty_job("copy")
        self.assertIn("No text was changed.", state["gate"]["message"])
        self.choose("accept pass")

        # The same pass can run again, with its own epoch and job folders.
        state = self.choose("run line")
        self.assertEqual((state["passes"][2]["number"], state["passes"][2]["epoch"]), (3, 2))
        self.assertEqual(self.engine.instance(state)["key"], "line/2/front-matter/1")
        for _ in range(4):
            state = self.approve_empty_job("line")
        self.assertTrue((self.workspace / "editorial/passes/003-line/_whole/application-report.md").is_file())
        self.assertTrue((self.workspace / "editorial/passes/001-line/_whole/application-report.md").is_file())
        self.choose("accept pass")

        # Manuscript approval is separate from final publication and may be reopened.
        state = self.choose("finish")
        self.assertEqual(state["status"], "WAITING_FOR_ACCEPTANCE")
        self.assertEqual([o["chapter_id"] for o in state["outputs"]], ["front-matter", "chapter-1", "chapter-2"])
        state = self.engine.restart_stage("passes", reason="One more look")
        self.assertEqual(state["gate"]["kind"], "pass_choice")
        state = self.choose("finish")
        state = self.engine.accept(state["acceptance_id"], confirm_final=True)
        self.assertEqual((state["stage"], state["status"]), ("interior-design", "READY"))
        self.assertEqual(self.engine.store.content(state["outputs"][1]), b"## 1\n\nHe returned.\n")
        self.assertEqual([(p["number"], p["stage"]) for p in state["passes"]], [(1, "line"), (2, "copy"), (3, "line")])
        self.assertFalse(self.engine.finalized(state))
        self.assertFalse(state.get("export_path"))
        library = self.service.library(self.work_id)
        self.assertEqual(library.finalized(), [])
        self.assertIsNone(library.head("literary-editing/v001/run.json"))

    def test_literary_editing_can_be_accepted_without_any_pass(self):
        state = self.start_editing()
        state = self.choose("finish")
        self.assertEqual(state["status"], "WAITING_FOR_ACCEPTANCE")
        prepared = [self.engine.store.content(state["prepared"]["files"][c["path"]]) for c in state["chapters"]]
        self.assertEqual([self.engine.store.content(o) for o in state["outputs"]], prepared)
        state = self.engine.accept(state["acceptance_id"], confirm_final=True)
        self.assertEqual((state["stage"], state["status"]), ("interior-design", "READY"))
        self.assertFalse(self.engine.finalized(state))
        self.assertEqual([self.engine.store.content(o) for o in state["outputs"]], prepared)
        template = registry.get("literary-editing-v1")
        next(s for s in template["stages"] if s["id"] == "passes")["options"].append({"stage": "prepare", "title": "Prepare again"})
        with self.assertRaisesRegex(ValueError, "must be an agent stage other than preparation"):
            registry.validate(template)


class DocumentAdapterTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("docx"), "Install workflow/requirements-docx.txt for builder tests.")
    def test_builder_preserves_text_emphasis_headings_and_page_fields(self):
        from docx import Document
        from ..src.document_audit import docx_paragraphs
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "manuscript.docx"
            source = "# A Story\n\n## 1\n\nHe **came** *back*.\n\n## 2\n\nShe stayed.\n"
            settings = dict(document_adapters.DEFAULT_SETTINGS, include_toc=False)
            document_adapters.PythonDocxBuilder().build(source, settings, target, {})
            paragraphs, folios = docx_paragraphs(target)
            self.assertEqual([p["text"] for p in paragraphs], ["A Story", "1", "He came back.", "2", "She stayed."])
            self.assertTrue(paragraphs[0]["title"])
            self.assertTrue(paragraphs[1]["heading"])
            self.assertTrue(folios)
            runs = Document(target).paragraphs[2].runs
            self.assertTrue(next(r for r in runs if r.text == "came").bold)
            self.assertTrue(next(r for r in runs if r.text == "back").italic)
            from docx.oxml.ns import qn
            document = Document(target)
            for name in ("Title", "Heading 1"):
                style = document.styles[name]
                self.assertIsNone(style.element.find(qn("w:pPr") + "/" + qn("w:pBdr")))
                fonts = style.element.find(qn("w:rPr") + "/" + qn("w:rFonts"))
                self.assertFalse(any("theme" in key.lower() for key in fonts.attrib))
                self.assertEqual(fonts.get(qn("w:ascii")), settings["body_font"])
            self.assertEqual(document.paragraphs[2].paragraph_format.first_line_indent, 0)
            settings["indent_opening_paragraphs"] = True
            document_adapters.PythonDocxBuilder().build(source, settings, target, {})
            self.assertIsNone(Document(target).paragraphs[2].paragraph_format.first_line_indent)

    def test_bad_settings_and_unsupported_content_are_not_silently_converted(self):
        with self.assertRaisesRegex(ValueError, "text width"):
            document_adapters.validate_settings(dict(document_adapters.DEFAULT_SETTINGS, margin_inches=2.5))
        with self.assertRaisesRegex(ValueError, "Unsupported manuscript block"):
            document_adapters.content_blocks("# Title\n\n![illustration](image.png)\n")

    def test_cloud_renderer_uses_isolated_libreoffice_profile(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "book.docx"
            source.write_bytes(b"test input")

            def run(command, **kwargs):
                if "--convert-to" in command:
                    self.assertIn("--headless", command)
                    self.assertTrue(any(arg.startswith("-env:UserInstallation=file:") for arg in command))
                    self.assertIn("pdf:writer_pdf_Export", command)
                    (root / "book.pdf").write_bytes(b"%PDF fixture")
                return SimpleNamespace(returncode=0, stdout="LibreOffice test", stderr="")

            with patch.object(document_adapters.shutil, "which", return_value="/usr/bin/soffice"), \
                    patch.object(document_adapters.subprocess, "run", side_effect=run):
                result = document_adapters.LibreOfficeRenderer().render(source, root)
            self.assertEqual(result.renderer, "libreoffice")
            self.assertEqual(result.pdf.name, "book.pdf")


class PerformanceTests(unittest.TestCase):
    def test_approval_submission_and_followup_work_are_separate(self):
        from datetime import datetime, timezone, timedelta
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        data = [
            (0, "execution.started", {"stage": "translate"}),
            (10, "execution.result", {"outcome": "needs_human_input", "gate": "map_exceptions"}),
            (10.2, "e2e.delegated_approval", {"gate_id": "g1"}),
            (10.5, "review.received", {"receipt_id": "r1", "gate_id": "g1"}),
            (11, "execution.started", {"stage": "translate"}),
            (31, "execution.result", {"outcome": "needs_human_input", "gate": "map_exceptions"}),
            (31.2, "e2e.delegated_approval", {"gate_id": "g2"}),
            (31.4, "review.received", {"receipt_id": "r2", "gate_id": "g2"}),
            (32, "execution.started", {"stage": "translate"}),
            (92, "execution.result", {"outcome": "needs_human_input", "gate": "continuation"}),
        ]
        events = [{"created_at": (base + timedelta(seconds=second)).isoformat(),
                   "kind": kind, "payload": payload} for second, kind, payload in data]
        state = {
            "id": "test", "status": "WAITING_FOR_HUMAN", "stage": "translate",
            "outputs": [], "chapters": [{}],
            "receipts": [
                {"id": "r1", "decision_source": "delegated-automation",
                 "gate": {"kind": "map_exceptions"},
                 "parsed": {"type": "dispositions", "dispositions": [{}, {}]}},
                {"id": "r2", "decision_source": "delegated-automation",
                 "gate": {"kind": "map_exceptions"}, "parsed": {"type": "final-closure"}},
            ],
        }
        report = monitor_performance.analyze(events, state, base + timedelta(seconds=93))
        self.assertEqual(report["work_groups"]["map_decision_recording"]["wall_seconds"], 20)
        self.assertEqual(report["work_groups"]["drafting_and_source_review"]["wall_seconds"], 60)
        self.assertEqual(report["delegated_approval_timing"]["submission_seconds"], .5)
        self.assertEqual(report["delegated_approval_timing"]["result_to_receipt_seconds"], .9)
        self.assertEqual(report["delegated_approval_timing"]["batches"][0]["item_count"], 2)
        self.assertEqual(monitor_performance.work_category(
            "translate", "translation_issue", "feedback", "continuation"),
            "issue_application_and_finalization_mixed")
        self.assertEqual(monitor_performance.work_category(
            "translate", "continuation", "feedback", "chapter_sanity"), "chapter_sanity_review")

    def test_timing_unions_tools_and_deduplicates_cumulative_usage(self):
        from datetime import datetime, timezone, timedelta
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        events = []

        def event(second, kind, payload):
            events.append({"created_at": (base + timedelta(seconds=second)).isoformat(),
                           "kind": kind, "payload": payload})

        def usage(second, turn_id, inputs, cached, outputs, last_input):
            event(second, "thread/tokenUsage/updated", {
                "threadId": "thread", "turnId": turn_id,
                "tokenUsage": {"total": {"inputTokens": inputs, "cachedInputTokens": cached,
                                        "outputTokens": outputs, "reasoningOutputTokens": 3},
                               "last": {"inputTokens": last_input}},
            })

        event(0, "execution.started", {"stage": "translate"})
        event(.1, "execution.thread", {"thread_id": "thread"})
        event(.2, "thread/started", {"thread": {"id": "thread", "model": "test-model"}})
        event(1, "turn/started", {"turn": {"id": "turn-1"}})
        event(2, "item/started", {"turnId": "turn-1", "item": {"id": "command", "type": "commandExecution"}})
        event(3, "item/started", {"turnId": "turn-1", "item": {"id": "nested", "type": "fileChange"}})
        usage(3.5, "turn-1", 100, 80, 10, 100)
        event(4, "item/completed", {"turnId": "turn-1", "item": {"id": "nested", "type": "fileChange", "changes": []}})
        usage(4.1, "turn-1", 100, 80, 10, 100)
        event(6, "item/completed", {"turnId": "turn-1", "item": {
            "id": "command", "type": "commandExecution", "exitCode": 0, "aggregatedOutput": "fixture",
        }})
        usage(8, "turn-1", 300, 230, 30, 200)
        event(9, "turn/completed", {"turn": {"id": "turn-1"}})
        event(10, "execution.result", {"outcome": "needs_human_input", "gate": "continuation"})
        event(12, "execution.started", {"stage": "translate"})
        event(12.1, "execution.thread", {"thread_id": "thread"})
        usage(12.2, "turn-1", 300, 230, 30, 200)  # Resume notification repeats earlier usage.
        event(13, "turn/started", {"turn": {"id": "turn-2"}})
        usage(14, "turn-2", 450, 330, 45, 150)
        state = {"id": "test", "status": "RUNNING", "stage": "translate", "outputs": [], "chapters": [{}]}
        report = monitor_performance.analyze(events, state, base + timedelta(seconds=15))
        first, active = report["attempts"]
        self.assertEqual((first["startup_seconds"], first["tool_seconds"],
                          first["runtime_non_tool_seconds"], first["post_turn_seconds"]), (1, 4, 4, 1))
        self.assertEqual(first["usage_updates"], 2)
        self.assertEqual(first["tokens"]["inputTokens"], 300)
        self.assertEqual(first["model"], "test-model")
        self.assertEqual(active["tokens"]["inputTokens"], 150)
        self.assertFalse(active["finished"])
        self.assertEqual(report["completed_attempt_totals"]["tokens"]["outputTokens"], 30)
        self.assertEqual(report["completed_attempt_totals"]["wall_seconds"], 10)


class CodexTransportTests(unittest.TestCase):
    SERVER = r'''
import json, sys
def send(value):
    print(json.dumps(value), flush=True)
for line in sys.stdin:
    m = json.loads(line)
    method = m.get("method")
    if method == "initialize":
        send({"id": m["id"], "result": {"userAgent": "fixture"}})
    elif method in ("thread/start", "thread/resume"):
        assert m["params"]["sandbox"] == "workspace-write"
        assert m["params"]["approvalPolicy"] == "never"
        send({"id": m["id"], "result": {"thread": {"id": "thread-1"}}})
    elif method == "turn/start":
        assert m["params"]["outputSchema"]["type"] == "object"
        assert not m["params"]["sandboxPolicy"]["networkAccess"]
        send({"id": 88, "method": "item/commandExecution/requestApproval",
              "params": {"command": "fixture denied command"}})
        answer = json.loads(sys.stdin.readline())
        assert answer["result"]["decision"] == "decline"
        for method in ("item/started", "item/completed"):
            send({"method": method, "params": {"threadId": "thread-1", "turnId": "turn-1",
                  "item": {"id": "tool", "type": "commandExecution", "exitCode": 0,
                           "aggregatedOutput": "private tool output"}}})
        for _ in range(2):
            send({"method": "thread/tokenUsage/updated", "params": {"threadId": "thread-1", "turnId": "turn-1",
                  "tokenUsage": {"total": {"inputTokens": 600, "outputTokens": 60, "cachedInputTokens": 350},
                                 "last": {"inputTokens": 100, "outputTokens": 10, "cachedInputTokens": 50}}}})
        # Notifications intentionally precede the RPC response.
        send({"method": "item/completed", "params": {"threadId": "thread-1", "turnId": "turn-1",
              "item": {"type": "agentMessage", "text": json.dumps({"outcome": "blocked"})}}})
        send({"method": "turn/completed", "params": {"threadId": "thread-1",
              "turn": {"id": "turn-1", "status": "completed"}}})
        send({"id": m["id"], "result": {"turn": {"id": "turn-1"}}})
'''

    def test_stdio_protocol_start_resume_interleaving_and_denial(self):
        with tempfile.TemporaryDirectory() as temp:
            for thread_id in (None, "thread-1"):
                with self.subTest(thread_id=thread_id):
                    events, threads = [], []
                    runtime = CodexRuntime([sys.executable, "-u", "-c", self.SERVER], timeout=10)
                    response = runtime.run(Request(Path(temp), "Fixture", None, thread_id, RESULT_SCHEMA),
                                           lambda *event: events.append(event), threads.append)
                    self.assertEqual(response, {"outcome": "blocked"})
                    self.assertEqual(threads, ["thread-1"])
                    self.assertTrue(any(event[0] == "runtime.request" for event in events))
                    self.assertEqual([kind for kind, _ in events if kind.startswith("runtime.tool_")],
                                     ["runtime.tool_started", "runtime.tool_completed"])
                    self.assertEqual(sum(p["input"] for k, p in events if k == "runtime.usage"), 100)
                    self.assertNotIn("private tool output", json.dumps(events))
                    self.assertTrue(all(kind.startswith("runtime.") for kind, _ in events))

    def test_timeout_terminates_process(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = CodexRuntime([sys.executable, "-u", "-c", "import time; time.sleep(30)"], timeout=0.1)
            with self.assertRaises(TimeoutError):
                runtime.run(Request(Path(temp), "", None, None, RESULT_SCHEMA), lambda *args: None, lambda t: None)


if __name__ == "__main__":
    unittest.main()
