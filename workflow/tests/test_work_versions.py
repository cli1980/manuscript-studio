"""Work-owned preparation and production-template input/version regressions."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.src.engine import Engine, WorkflowError
from workflow.src.service import WorkflowService
from workflow.src.work_versions import load_version, publish_changed_output, versions
from workflow.tests.analysis_fixture import analyze
from workflow.tests import test_workflow as fixtures
from workflow.tests.test_workflow import ScriptedRuntime


class WorkVersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "original.md"
        self.source.write_bytes("# Story\n\nHe came back.\n".encode())
        self.service = WorkflowService(self.base / "server", owner="tester")
        self.addCleanup(self.service.close)
        self.work_id = self.service.create_work(self.source, "zh")
        self.fixture = fixtures.WorkflowTests()
        self.fixture.base = self.base
        self.fixture.source = self.source
        self.fixture.language = "zh"
        self.fixture.service = self.service
        self.fixture.work_id = self.work_id
        self.fixture.engine = None
        self.addCleanup(lambda: self.fixture.engine and self.fixture.engine.close())

    def open_fixture(self, job_id):
        if self.fixture.engine:
            self.fixture.engine.close()
        self.fixture.engine = Engine.open(
            Path(self.service._run_row(job_id)["path"]), library=self.service.library(self.work_id))
        self.fixture.workspace = self.fixture.engine.workspace
        self.fixture.run_id = job_id
        return self.fixture.engine

    def prepare(self, *, publish=True):
        job_id = self.service.create_preparation(self.work_id)
        engine = self.open_fixture(job_id)
        state = engine.advance(ScriptedRuntime(self.fixture.preparation))
        self.assertEqual(state["gate"]["kind"], "metadata_review")
        engine.reply(state["gate"]["id"], "confirm metadata")
        state = engine.advance(ScriptedRuntime(analyze))
        self.assertEqual(state["stage"], "save-preparation")
        if not publish:
            return state
        state = engine.advance(None)
        self.assertEqual(state["status"], "COMPLETED")
        self.service._record_state(job_id, state)
        return load_version(self.service.library(self.work_id), state["prepared_version_id"])

    def test_storage_retry_reuses_completed_reading_without_another_agent_turn(self):
        state = self.prepare(publish=False)
        engine = self.fixture.engine
        identity, attempts = state["analysis"]["analysis_id"], state["attempts"]
        publish = engine.library.publish_many

        def interrupted(entries, **kwargs):
            publish(entries[:2], **kwargs)
            raise OSError("Synthetic interrupted file batch")

        with patch.object(engine.library, "publish_many", side_effect=interrupted):
            with self.assertRaisesRegex(OSError, "interrupted"):
                engine.advance(None)
        self.assertEqual(engine.state()["status"], "FAILED")
        self.assertEqual(versions(engine.library), [])
        engine.retry()
        state = engine.advance(None)
        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual(state["analysis"]["analysis_id"], identity)
        self.assertEqual(state["attempts"], attempts)

    def test_work_input_survives_producer_workspace_becoming_unavailable(self):
        version = self.prepare()
        root = self.fixture.engine.root
        self.fixture.engine.close()
        self.fixture.engine = None
        root.rename(root.with_name(root.name + "-archived"))
        run = self.service.create_run("literary-editing-v1", work_id=self.work_id,
                                      work_version_id=version["version_id"])
        with self.service.open_run(run) as engine:
            engine.verify(engine.state())
            self.assertEqual(engine.state()["analysis"]["analysis_id"], version["analysis"]["analysis_id"])
            for record in engine.metadata_history(engine.state()):
                self.assertTrue(engine.metadata_version(engine.state(), record["record_revision"])["metadata"])

    def test_metadata_revision_reuses_text_reading_and_freezes_new_approval(self):
        version = self.prepare()
        job = self.service.create_preparation(self.work_id, source_version_id=version["version_id"])
        engine = self.open_fixture(job)
        state = engine.state()
        self.assertEqual(state["gate"]["kind"], "metadata_review")
        state = engine.edit_metadata("/title", "A corrected title", gate_id=state["gate"]["id"])
        state = engine.reply(state["gate"]["id"], "confirm metadata")
        self.assertEqual(state["stage"], "save-preparation")
        state = engine.advance(None)
        updated = load_version(engine.library, state["prepared_version_id"])
        self.assertEqual(state["attempts"], 0)
        self.assertEqual(updated["analysis"], version["analysis"])
        self.assertNotEqual(updated["metadata_approval"]["sha256"], version["metadata_approval"]["sha256"])
        self.assertFalse(engine.analysis_handoff(state)["current_metadata_matches_analysis"])
        self.assertEqual(updated["parent_version_id"], version["version_id"])
        for chapter in version["chapters"]:
            self.assertEqual(updated["files"][chapter["path"]]["sha256"], chapter["sha256"])
        self.assertEqual(len(versions(engine.library)), 2)

    def test_explicit_analysis_refresh_reuses_extraction_but_creates_new_reading(self):
        version = self.prepare()
        job = self.service.create_preparation(self.work_id, source_version_id=version["version_id"],
                                              refresh_analysis=True)
        engine = self.open_fixture(job)
        state = engine.state()
        self.assertEqual(state["gate"]["kind"], "metadata_review")
        engine.reply(state["gate"]["id"], "confirm metadata")
        engine.advance(ScriptedRuntime(analyze))
        state = engine.advance(None)
        updated = load_version(engine.library, state["prepared_version_id"])
        self.assertEqual(state["attempts"], 1)
        self.assertNotEqual(updated["analysis"]["analysis_id"], version["analysis"]["analysis_id"])
        self.assertEqual(updated["analysis"]["basis"], version["analysis"]["basis"])

    def test_canonical_source_is_independent_of_windows_path_separator_choice(self):
        job = self.service.create_preparation(self.work_id)
        engine = self.open_fixture(job)

        def forward_paths(request):
            result = self.fixture.preparation(request)
            path = engine.file(result["work_record"])
            work = json.loads(path.read_bytes())
            work["discovery"]["location"] = Path(work["discovery"]["location"]).as_posix()
            path.write_text(json.dumps(work), encoding="utf-8", newline="\n")
            manifest_path = path.parent / "revisions/r0001/manifest.json"
            manifest = json.loads(manifest_path.read_bytes())
            manifest["sources"][0]["locator"] = Path(manifest["sources"][0]["locator"]).as_posix()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
            return result

        state = engine.advance(ScriptedRuntime(forward_paths))
        work = json.loads(engine.file(state["prepared"]["work_record"]).read_bytes())
        self.assertEqual(Path(work["discovery"]["location"]),
                         engine.library.path(state["preparation_source"]["artifact"]))

    def test_run_requires_explicit_ready_version(self):
        with self.assertRaisesRegex(WorkflowError, "ready Work version"):
            self.service.create_run("literary-editing-v1", work_id=self.work_id)
        self.assertEqual(self.service.list_runs(), [])
        self.assertEqual(versions(self.service.library(self.work_id)), [])

    def test_work_job_publishes_provisional_immutable_package_not_a_workflow(self):
        version = self.prepare()
        work = self.service.get_work(self.work_id)
        self.assertEqual(self.service.list_runs(), [])
        self.assertEqual(len(work["preparation_jobs"]), 1)
        self.assertEqual(work["workflows"], {})
        self.assertEqual(version["analysis"]["approval_status"], "provisional")
        self.assertEqual(len(version["analysis"]["artifacts"]), 5)
        self.assertTrue(version["metadata_approval"]["receipt_id"])
        library = self.service.library(self.work_id)
        manifest = library.publication(version["publication_id"])
        with self.assertRaisesRegex(WorkflowError, "accepted version"):
            library.publish_many([{"artifact": manifest["artifact"], "data": b"{}", "expected_head": manifest["id"]}],
                                 run_id=None, workflow=None)

    def test_both_workflows_checkout_exact_analysis_without_preparation(self):
        version = self.prepare()
        for template, first in (("literary-translation-v1", "brief"), ("literary-editing-v1", "passes")):
            run_id = self.service.create_run(template, work_id=self.work_id, work_version_id=version["version_id"])
            with self.service.open_run(run_id) as engine:
                state = engine.state()
                self.assertEqual(state["stage"], first)
                self.assertFalse(any(stage.get("preparation") or stage["id"] == "analysis"
                                     for stage in state["definition"]["stages"]))
                self.assertEqual(state["analysis"]["manifest"], version["analysis"]["manifest"])
                self.assertEqual(state["input_version"]["analysis_id"], version["analysis"]["analysis_id"])
                engine.verify(state)
                if first == "brief":
                    prompt = engine.stage_prompt(state, engine.stage_def(state))
                    self.assertIn(version["analysis"]["analysis_id"], prompt)
                engine.cancel()

    def test_restart_without_a_version_refuses_before_cancelling_historical_run(self):
        version = self.prepare()
        run = self.service.create_run("literary-editing-v1", work_id=self.work_id,
                                      work_version_id=version["version_id"])
        engine = self.open_fixture(run)
        revision, state = engine.store.load()
        state.pop("input_version")
        engine.store.save(revision, state, "test.historical_input")
        before = engine.store.load()
        with self.assertRaisesRegex(WorkflowError, "older run has no selected Work version"):
            self.service.restart_workflow(run, reason="Explicit restart probe.")
        self.assertEqual(engine.store.load(), before)

    def test_restart_keeps_selected_version_instead_of_latest_metadata_version(self):
        selected = self.prepare()
        job = self.service.create_preparation(self.work_id, source_version_id=selected["version_id"])
        engine = self.open_fixture(job)
        state = engine.state()
        state = engine.edit_metadata("/title", "Newer display title", gate_id=state["gate"]["id"])
        engine.reply(state["gate"]["id"], "confirm metadata")
        newer = engine.advance(None)["prepared_version_id"]
        self.assertNotEqual(newer, selected["version_id"])
        run = self.service.create_run("literary-editing-v1", work_id=self.work_id,
                                      work_version_id=selected["version_id"])
        restarted = self.service.restart_workflow(run, reason="Restart without changing the chosen source.")
        engine = self.open_fixture(restarted)
        state = engine.state()
        self.assertEqual(state["input_version"]["version_id"], selected["version_id"])
        self.assertEqual(state["analysis"], selected["analysis"])
        self.assertEqual(state["metadata_approval"], selected["metadata_approval"])
        self.assertEqual(state["attempts"], 0)
        self.assertEqual(self.service.get_run(run)["status"], "CANCELLED")

    def test_zero_pass_docx_attaches_deliverables_without_duplicating_manuscript(self):
        version = self.prepare()
        run = self.service.create_run("literary-editing-v1", work_id=self.work_id,
                                      work_version_id=version["version_id"])
        engine = self.open_fixture(run)
        engine.advance(None)
        self.fixture.approve_editing()
        state = engine.advance(ScriptedRuntime(self.fixture.design_result))
        gate = state["gate"]
        proposal = engine.design_view(state)["proposal"]
        engine.review_design(gate["id"], gate["binding"]["sha256"], "generate",
                             answers={q["id"]: "Keep this proposal." for q in proposal["questions"] if q["blocking"]})
        state = engine.advance(None)
        self.assertEqual(state["status"], "WAITING_FOR_ACCEPTANCE")
        engine.accept(state["acceptance_id"], confirm_final=True)
        state = engine.advance(None)
        self.assertEqual(state["status"], "COMPLETED")
        self.assertIsNone(state.get("output_work_version_id"))
        self.assertEqual(len(versions(engine.library)), 1)
        self.assertTrue(any(record["artifact"].endswith("/document.docx")
                            for record in engine.library.publications()))

    def test_source_tampering_and_cross_work_reuse_are_rejected(self):
        version = self.prepare()
        other = self.service.create_work(self.source, "en-US")
        with self.assertRaisesRegex(ValueError, "Unknown"):
            self.service.create_run("literary-editing-v1", work_id=other, work_version_id=version["version_id"])
        library = self.service.library(self.work_id)
        library.path(version["source"]["artifact"]).write_bytes(b"Changed source")
        with self.assertRaisesRegex(ValueError, "source changed"):
            self.service.create_run("literary-editing-v1", work_id=self.work_id,
                                    work_version_id=version["version_id"])

    def test_incomplete_analysis_never_becomes_a_ready_input(self):
        job = self.service.create_preparation(self.work_id)
        engine = self.open_fixture(job)
        state = engine.advance(ScriptedRuntime(self.fixture.preparation))
        engine.reply(state["gate"]["id"], "confirm metadata")

        def incomplete(request):
            response = analyze(request)
            path = engine.file(response["state_path"])
            manifest = json.loads(path.read_bytes())
            manifest["coverage"].pop()
            path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
            return response

        with self.assertRaisesRegex(ValueError, "cover every"):
            engine.advance(ScriptedRuntime(incomplete, analysis_action=None))
        self.assertEqual(versions(self.service.library(self.work_id)), [])

    def test_accepted_translation_creates_pending_version_and_preserves_original(self):
        version = self.prepare()
        run = self.service.create_run("literary-translation-v1", work_id=self.work_id,
                                      work_version_id=version["version_id"])
        engine = self.open_fixture(run)
        self.fixture.approve_brief()
        self.fixture.translate_chapter()
        self.fixture.translate_chapter()
        state = engine.state()
        self.assertEqual(state["status"], "WAITING_FOR_ACCEPTANCE")
        self.assertIsNone(publish_changed_output(engine, state))
        state = engine.accept(state["acceptance_id"], confirm_final=True)
        pending = load_version(engine.library, state["output_work_version_id"], ready=False)
        self.assertEqual(pending["status"], "analysis_pending")
        self.assertIsNone(pending["analysis"])
        self.assertEqual(pending["parent_version_id"], version["version_id"])
        self.assertEqual(pending["language"], "en-US")
        self.assertEqual(engine.library.read(version["source"]), self.source.read_bytes())
        with self.assertRaisesRegex(WorkflowError, "Prepare and validate"):
            load_version(engine.library, pending["version_id"])
        state = engine.advance(None)
        self.assertEqual(state["status"], "COMPLETED")
        engine.close()
        self.fixture.engine = None
        self.service._record_state(run, state)
        next_job = self.service.create_preparation(self.work_id, source_version_id=pending["version_id"])
        next_engine = self.open_fixture(next_job)
        self.fixture.language = "en-US"
        state = next_engine.advance(ScriptedRuntime(self.fixture.preparation))
        self.assertEqual(next_engine.metadata_view(state)["metadata"]["manuscript_language"], "en-US")
        state = next_engine.edit_metadata("/title", "English edition title", gate_id=state["gate"]["id"])
        next_engine.reply(state["gate"]["id"], "confirm metadata")
        next_engine.advance(ScriptedRuntime(analyze))
        state = next_engine.advance(None)
        derived = load_version(next_engine.library, state["prepared_version_id"])
        self.assertEqual(derived["parent_version_id"], pending["version_id"])
        self.assertNotEqual(derived["analysis"]["analysis_id"], version["analysis"]["analysis_id"])
        self.assertEqual(self.service.get_work_metadata(self.work_id)["metadata"]["manuscript_language"], "zh")
        review = self.service.create_preparation(self.work_id, source_version_id=derived["version_id"])
        review_engine = self.open_fixture(review)
        # Probe metadata adoption for a subsequent English editing result on the original Chinese Work.
        state = review_engine.state()
        state["preparation_kind"] = "edited"
        review_engine._adopt_reviewed_metadata(state)
        self.assertEqual(review_engine.metadata_view(state)["metadata"]["title"], "English edition title")


if __name__ == "__main__":
    unittest.main()
