import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from argparse import Namespace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_judge as judge
from translation_cases import migrate_case, candidates, discover_cases
from prepare_translation import prepare_tasks
from migrate_translation_cases import migrate
import generate_translation_candidates as generator
from anonymize_translation_candidates import anonymize

CASE_ID = "zh-en-modern-001"
REVIEWER = "private-human-label"
PREDICTION = {
    "overall_score": 3,
    "dimension_scores": {"fidelity": 3, "english_naturalness": 4, "literary_voice": 5},
    "rationale": "Deterministic transport fixture, not an LLM assessment.",
}


class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / "evals"
        for relative in (
            f"cases/literary-translation/{CASE_ID}",
            "fixtures/manuscripts/modern-lu-xun-guxiang/passage-001", "rubrics",
            "judges/literary-translation-judge",
        ):
            shutil.copytree(judge.ROOT / relative, self.root / relative)
        self.case_root = self.root / f"cases/literary-translation/{CASE_ID}"
        # Keep legacy coverage explicit even after repository fixtures migrate.
        path = self.case_root / "case.json"
        case = json.loads(path.read_text(encoding="utf-8"))
        if case.get("schema_version") == 2:
            baseline = next(c for c in case.pop("candidates") if c["provenance"]["translation_origin"] == "user-provided")
            original = (self.case_root / baseline["translation_file"]).read_bytes()
            (self.case_root / "translation.en.txt").write_bytes(original)
            case.update(schema_version=1, translation_file="translation.en.txt",
                        provenance=baseline["provenance"])
            case.pop("translation_instructions", None)
            path.write_text(json.dumps(case), encoding="utf-8")
        self.history = self.case_root / "judgments.jsonl"
        self.older = {
            "judgment_id": "older", "case_id": CASE_ID, "case_revision": 1,
            "passage_id": "modern-lu-xun-guxiang-passage-001", "source_revision": 1,
            "rubric_version": "literary-translation-quality-v1",
            "rater_id": REVIEWER, "status": "complete", "overall_score": 2,
            "dimension_scores": {"fidelity": 1, "english_naturalness": 2, "literary_voice": 3},
            "rationale": "SECRET_HUMAN_REASON", "issues": [{"explanation": "SECRET_HUMAN_ISSUE"}],
        }
        self.latest = {
            **self.older, "judgment_id": "latest", "supersedes_judgment_id": "older",
            "overall_score": 4,
            "dimension_scores": {"fidelity": 2, "english_naturalness": 4, "literary_voice": 4},
        }
        self.write_history([self.older, self.latest])

    def write_history(self, records):
        self.history.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")

    def prepared(self, **kwargs):
        return judge.prepare_case(self.root, CASE_ID, model="fixture-not-an-llm", smoke_test=True, **kwargs)

    def args(self, **kwargs):
        values = {
            "data_dir": self.root, "case": [CASE_ID], "all": False,
            "model": "fixture-not-an-llm", "reviewer": REVIEWER,
            "base_url": "https://api.openai.com/v1", "api_key_env": "EVAL_TEST_KEY",
            "prepare_only": True, "smoke_test": True, "temperature": None, "timeout": 5,
        }
        values.update(kwargs)
        return Namespace(**values)

    def test_prepare_does_not_read_human_judgments_or_production_skills(self):
        accesses = []
        read = judge.read_bytes

        def observed(path, area):
            accesses.append(Path(path))
            self.assertNotEqual(Path(path).name, "judgments.jsonl")
            self.assertNotIn("plugins", Path(path).parts)
            return read(path, area)

        with patch.object(judge, "read_bytes", side_effect=observed):
            prepared = self.prepared()
        self.assertEqual({p.name for p in accesses}, {
            "case.json", "passage.json", "source.zh.txt", "translation.en.txt",
            "literary-translation-quality-v1.json", "SKILL.md",
        })
        request = prepared["request"]
        self.assertNotIn("tools", request)
        self.assertEqual([m["role"] for m in request["messages"]], ["system", "user"])
        self.assertEqual(request["messages"][0]["content"],
                         (self.root / "judges/literary-translation-judge/SKILL.md").read_bytes().decode("utf-8"))
        inputs = json.loads(request["messages"][1]["content"])
        self.assertEqual(set(inputs), {"source_text", "translation_text"})
        self.assertEqual(inputs["source_text"].encode("utf-8"),
                         (self.root / "fixtures/manuscripts/modern-lu-xun-guxiang/passage-001/source.zh.txt").read_bytes())
        self.assertEqual(inputs["translation_text"].encode("utf-8"), (self.case_root / "translation.en.txt").read_bytes())
        for marker in (REVIEWER, "SECRET_HUMAN_REASON", "SECRET_HUMAN_ISSUE", "supersedes_judgment_id"):
            self.assertNotIn(marker, json.dumps(request))

    def test_prepare_excludes_all_case_context_and_extra_metadata(self):
        for path in (
            self.case_root / "case.json",
            self.root / "fixtures/manuscripts/modern-lu-xun-guxiang/passage-001/passage.json",
            self.root / "rubrics/literary-translation-quality-v1.json",
        ):
            metadata = json.loads(path.read_text(encoding="utf-8"))
            metadata["human_score"] = "SECRET_SCORE"
            metadata.setdefault("context", {})["human_comment"] = "SECRET_COMMENT"
            metadata["context"].update({
                "brief": "EXCLUDED_BRIEF", "genre": "EXCLUDED_GENRE", "background": "EXCLUDED_BACKGROUND",
            })
            path.write_text(json.dumps(metadata), encoding="utf-8")
        prompt = json.dumps(self.prepared()["request"])
        self.assertNotIn("SECRET_SCORE", prompt)
        self.assertNotIn("SECRET_COMMENT", prompt)
        for marker in ("EXCLUDED_BRIEF", "EXCLUDED_GENRE", "EXCLUDED_BACKGROUND"):
            self.assertNotIn(marker, prompt)

    def test_case_references_choose_the_texts_without_guessing_filenames(self):
        translation = self.case_root / "candidate-version-2.txt"
        translation.write_text("A separately referenced candidate.", encoding="utf-8")
        source_root = self.root / "fixtures/manuscripts/modern-lu-xun-guxiang/passage-001"
        source = source_root / "alternate-source.zh.txt"
        source.write_text("另一个原文段落。", encoding="utf-8")
        source_metadata = json.loads((source_root / "passage.json").read_text(encoding="utf-8"))
        source_metadata["source_file"] = source.name
        (source_root / "passage.json").write_text(json.dumps(source_metadata), encoding="utf-8")
        path = self.case_root / "case.json"
        case = json.loads(path.read_text(encoding="utf-8"))
        case["translation_file"] = translation.name
        case["source_file"] = Path(os.path.relpath(source, self.case_root)).as_posix()
        path.write_text(json.dumps(case), encoding="utf-8")
        prepared = self.prepared()
        inputs = json.loads(prepared["request"]["messages"][1]["content"])
        self.assertEqual(inputs["translation_text"], "A separately referenced candidate.")
        self.assertEqual(inputs["source_text"], "另一个原文段落。")

    def test_embedded_rubric_cannot_drift_from_human_criteria(self):
        path = self.root / "rubrics/literary-translation-quality-v1.json"
        rubric = json.loads(path.read_text(encoding="utf-8"))
        rubric["scale"]["anchors"]["4"] = "Changed scoring criterion."
        path.write_text(json.dumps(rubric), encoding="utf-8")
        with self.assertRaisesRegex(judge.EvaluationError, "embedded rubric"):
            self.prepared()

    def test_prepare_only_works_without_human_file_or_credentials(self):
        self.history.unlink()
        with patch.object(judge, "call_model", side_effect=AssertionError("No model calls allowed")):
            with patch.object(judge, "human_reference", side_effect=AssertionError("No human reads allowed")):
                destination, manifest = judge.run(self.args(model=None))
        self.assertEqual(manifest["status"], "prepared")
        self.assertFalse(manifest["benchmark_eligible"])
        self.assertTrue((destination / CASE_ID / "request.json").is_file())
        self.assertFalse((destination / CASE_ID / "prediction.json").exists())
        self.assertFalse((destination / "summary.json").exists())

    def make_ready(self):
        for path in (
            self.case_root / "case.json",
            self.root / "fixtures/manuscripts/modern-lu-xun-guxiang/passage-001/passage.json",
        ):
            metadata = json.loads(path.read_text(encoding="utf-8"))
            metadata["provenance"]["usage_rights"] = "permitted"
            if path.name == "case.json":
                metadata["status"] = "ready"
            path.write_text(json.dumps(metadata), encoding="utf-8")

    def test_training_export_uses_human_scores_only_as_assistant_targets(self):
        self.make_ready()
        self.latest["rationale"] = None
        self.write_history([self.older, self.latest])
        before = self.history.read_bytes()
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(judge, "call_model", side_effect=AssertionError("Training export must not call a model")):
                destination, manifest = judge.run(self.args(
                    mode="export-training", prepare_only=False, smoke_test=False, model=None,
                ))
        self.assertEqual(manifest["status"], "completed")
        self.assertTrue(manifest["training_eligible"])
        self.assertFalse(manifest["benchmark_eligible"])
        rows = [json.loads(line) for line in (destination / "training.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1)
        messages = rows[0]["messages"]
        self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant"])
        self.assertEqual(set(json.loads(messages[1]["content"])), {"source_text", "translation_text"})
        target = json.loads(messages[2]["content"])
        self.assertEqual(target, {
            "overall_score": 4, "dimension_scores": self.latest["dimension_scores"], "rationale": None,
        })
        self.assertNotIn(REVIEWER, json.dumps(messages))
        self.assertNotIn("SECRET_HUMAN", json.dumps(messages[:2]))
        index = json.loads((destination / "training-index.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(index["human_judgment_id"], "latest")
        self.assertEqual(index["group_id"], "modern-lu-xun-guxiang")
        self.assertEqual(self.history.read_bytes(), before)
        self.assertFalse((destination / CASE_ID / "prediction.json").exists())

    def test_training_export_retains_actual_human_explanation_when_present(self):
        target = judge.training_target(self.latest)
        self.assertEqual(target["rationale"], "SECRET_HUMAN_REASON")
        self.assertEqual(target["overall_score"], self.latest["overall_score"])

    def test_training_export_rejects_missing_dimension_labels(self):
        self.latest["dimension_scores"]["fidelity"] = None
        self.write_history([self.older, self.latest])
        destination, manifest = judge.run(self.args(mode="export-training", prepare_only=False))
        self.assertEqual(manifest["status"], "failed")
        self.assertIn("missing human labels", manifest["cases"][0]["error"])
        self.assertEqual((destination / "training.jsonl").read_text(), "")

    def test_training_export_rejects_current_draft_without_falling_back(self):
        draft = {**self.latest, "judgment_id": "draft", "supersedes_judgment_id": "latest", "status": "pending"}
        self.write_history([self.older, self.latest, draft])
        destination, manifest = judge.run(self.args(mode="export-training", prepare_only=False))
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual((destination / "training.jsonl").read_text(), "")

    def test_judge_only_scores_actual_output_without_reading_labels_or_stored_candidate(self):
        candidate = self.root.parent / "actual translated output.md"
        candidate.write_text("A new translated passage produced by the translation workflow.", encoding="utf-8")
        (self.case_root / "translation.en.txt").unlink()
        self.history.unlink()
        reads = []
        read = judge.read_bytes
        response = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(PREDICTION)}}]}

        def observed(path, area):
            reads.append(Path(path).name)
            self.assertNotEqual(Path(path).name, "judgments.jsonl")
            self.assertNotEqual(Path(path).name, "translation.en.txt")
            return read(path, area)

        with patch.dict(os.environ, {"EVAL_TEST_KEY": "fake"}):
            with patch.object(judge, "call_model", return_value=response) as call:
                with patch.object(judge, "read_bytes", side_effect=observed):
                    destination, manifest = judge.run(self.args(
                        mode="judge", prepare_only=False, reviewer=None, smoke_test=False,
                        translation_file=candidate,
                    ))
        model_input = json.loads(call.call_args.args[0]["messages"][1]["content"])
        self.assertEqual(model_input["translation_text"], candidate.read_text(encoding="utf-8"))
        self.assertEqual(set(model_input), {"source_text", "translation_text"})
        self.assertEqual(manifest["mode"], "judgment")
        self.assertEqual(manifest["status"], "completed")
        self.assertFalse(manifest["benchmark_eligible"])
        self.assertEqual(manifest["cases"][0]["candidate_source"], "external_translation")
        self.assertFalse((destination / CASE_ID / "comparison.json").exists())
        summary = json.loads((destination / "summary.json").read_text())
        self.assertEqual(summary["cases_judged"], 1)
        self.assertNotIn("metrics", summary)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            judge.print_report(destination, manifest)
        self.assertIn("LLM score", output.getvalue())
        self.assertNotIn("Human reference reviewer", output.getvalue())
        self.assertNotIn("MAE", output.getvalue())

    def multi_candidate(self):
        path = self.case_root / "case.json"
        case, history = migrate_case(json.loads(path.read_text(encoding="utf-8")), [self.older, self.latest])
        case["candidates"].append({
            "candidate_id": "adverse", "revision": 1, "translation_file": "adverse.en.txt",
            "status": "ready", "derived_from": "baseline",
            "provenance": {"usage_rights": "permitted", "intended_defect": "SECRET_VARIANT_LABEL"},
        })
        (self.case_root / "adverse.en.txt").write_text("A distinct synthetic candidate for isolation tests.", encoding="utf-8")
        path.write_text(json.dumps(case), encoding="utf-8")
        history.append({
            **self.latest, "judgment_id": "adverse-review", "candidate_id": "adverse",
            "candidate_revision": 1, "overall_score": 1, "supersedes_judgment_id": None,
        })
        self.write_history(history)
        return case

    def test_each_candidate_is_judged_independently_and_bound_to_its_human_scores(self):
        self.multi_candidate()
        response = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(PREDICTION)}}]}
        with patch.dict(os.environ, {"EVAL_TEST_KEY": "fake"}):
            with patch.object(judge, "call_model", return_value=response) as model:
                destination, manifest = judge.run(self.args(prepare_only=False))
        self.assertEqual(model.call_count, 2)
        inputs = [json.loads(call.args[0]["messages"][1]["content"]) for call in model.call_args_list]
        self.assertEqual(inputs[0]["source_text"], inputs[1]["source_text"])
        self.assertNotEqual(inputs[0]["translation_text"], inputs[1]["translation_text"])
        self.assertNotIn("SECRET_VARIANT_LABEL", json.dumps([call.args[0] for call in model.call_args_list]))
        self.assertNotIn("SECRET_HUMAN", json.dumps([call.args[0] for call in model.call_args_list]))
        for cid, human in (("baseline", "latest"), ("adverse", "adverse-review")):
            comparison = json.loads((destination / CASE_ID / cid / "comparison.json").read_text())
            self.assertEqual(comparison["human_judgment_id"], human)
            self.assertEqual(comparison["candidate_id"], cid)
        self.assertEqual(manifest["status"], "completed")
        summary = json.loads((destination / "summary.json").read_text())
        self.assertEqual(summary["unique_case_count"], 1)
        self.assertEqual(summary["cases_requested"], 1)
        self.assertEqual(summary["cases_compared"], 1)
        self.assertEqual(summary["candidates_compared"], 2)
        self.assertEqual(summary["candidates_requested"], 2)
        self.assertEqual(summary["case_macro_metrics"]["overall_score"]["count"], 1)

    def test_candidate_filter_and_cross_candidate_amendments(self):
        self.multi_candidate()
        destination, manifest = judge.run(self.args(candidate="adverse"))
        self.assertEqual(len(manifest["cases"]), 1)
        self.assertEqual(manifest["cases"][0]["candidate_id"], "adverse")
        self.assertTrue((destination / CASE_ID / "adverse/request.json").exists())
        records = [json.loads(line) for line in self.history.read_text().splitlines()]
        records[-1]["supersedes_judgment_id"] = "latest"
        self.write_history(records)
        with self.assertRaisesRegex(judge.EvaluationError, "cross candidate"):
            judge.human_reference(self.prepared(candidate_id="adverse"), REVIEWER)

    def test_case_macro_metrics_do_not_overweight_cases_with_more_candidates(self):
        case = self.multi_candidate()
        other_id = "another-task"
        directory = self.case_root.parent / other_id
        directory.mkdir()
        case["case_id"] = other_id
        case["translation_instructions"] = "A different translation task."
        case["candidates"] = case["candidates"][:1]
        (directory / "case.json").write_text(json.dumps(case))
        (directory / "translation.en.txt").write_text("Another synthetic candidate.")
        review = {
            **self.latest, "case_id": other_id, "judgment_id": "other-review",
            "candidate_id": "baseline", "candidate_revision": 1,
            "overall_score": 3, "supersedes_judgment_id": None,
        }
        (directory / "judgments.jsonl").write_text(json.dumps(review) + "\n")
        response = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(PREDICTION)}}]}
        with patch.dict(os.environ, {"EVAL_TEST_KEY": "fake"}):
            with patch.object(judge, "call_model", return_value=response):
                destination, _ = judge.run(self.args(prepare_only=False, case=[CASE_ID, other_id]))
        summary = json.loads((destination / "summary.json").read_text())
        self.assertEqual(summary["cases_requested"], 2)
        self.assertEqual(summary["candidates_requested"], 3)
        self.assertEqual(summary["metrics"]["overall_score"]["mean_absolute_error"], 1)
        self.assertEqual(summary["case_macro_metrics"]["overall_score"]["mean_absolute_error"], .75)

    def test_translator_inputs_are_source_only_and_shared_variants_do_not_duplicate_tasks(self):
        self.multi_candidate()
        self.history.unlink()
        (self.case_root / "translation.en.txt").unlink()
        (self.case_root / "adverse.en.txt").unlink()
        tasks = prepare_tasks(self.root, [CASE_ID])
        self.assertEqual(len(tasks), 1)
        self.assertEqual(set(tasks[0]["input"]), {"source_text", "source_language", "target_language", "translation_instructions"})
        self.assertNotIn("SECRET_", json.dumps(tasks))
        duplicate_id = "same-source-another-case"
        duplicate = self.case_root.parent / duplicate_id
        duplicate.mkdir()
        case = json.loads((self.case_root / "case.json").read_text())
        case["case_id"] = duplicate_id
        (duplicate / "case.json").write_text(json.dumps(case))
        self.assertEqual(len(prepare_tasks(self.root, [CASE_ID, duplicate_id])), 1)
        case["translation_instructions"] = "Use British English."
        (duplicate / "case.json").write_text(json.dumps(case))
        self.assertEqual(len(prepare_tasks(self.root, [CASE_ID, duplicate_id])), 2)

    def test_local_only_case_is_excluded_from_batches_but_can_be_selected_explicitly(self):
        cid = "local-long-case"
        directory = self.case_root.parent / cid
        shutil.copytree(self.case_root, directory)
        path = directory / "case.json"
        case = json.loads(path.read_text(encoding="utf-8"))
        case["case_id"] = cid
        path.write_text(json.dumps(case), encoding="utf-8")
        (directory / ".local-only").write_text("Manual testing only.")
        self.assertEqual([p.parent.name for p in discover_cases(self.case_root.parent)], [CASE_ID])
        _, manifest = judge.run(self.args(case=None, all=True))
        self.assertEqual([item["case_id"] for item in manifest["cases"]], [CASE_ID])
        self.assertEqual(judge.prepare_case(self.root, cid, smoke_test=True)["case"]["case_id"], cid)
        self.assertEqual(prepare_tasks(self.root, [cid])[0]["case_id"], cid)

    def test_empty_candidate_collection_still_supports_external_translation(self):
        case = self.multi_candidate()
        case["candidates"] = []
        (self.case_root / "case.json").write_text(json.dumps(case))
        external = self.root.parent / "new.en.txt"
        external.write_text("A newly generated candidate.")
        prepared = self.prepared(purpose="judge", translation_file=external)
        self.assertIsNone(prepared["candidate"])
        self.assertEqual(json.loads(prepared["request"]["messages"][1]["content"])["translation_text"],
                         external.read_text())

    def test_candidate_contract_rejects_duplicates_and_derivation_cycles(self):
        case = self.multi_candidate()
        case["candidates"][0]["derived_from"] = "adverse"
        with self.assertRaisesRegex(ValueError, "cycles"):
            candidates(case)
        case["candidates"][0].pop("derived_from")
        case["candidates"][1]["candidate_id"] = "baseline"
        with self.assertRaisesRegex(ValueError, "unique"):
            candidates(case)

    def test_case_migration_preserves_text_scores_history_and_is_idempotent(self):
        source_path = self.root / "fixtures/manuscripts/modern-lu-xun-guxiang/passage-001/source.zh.txt"
        source = source_path.read_bytes()
        english = (self.case_root / "translation.en.txt").read_bytes()
        old = self.history.read_bytes()
        self.assertEqual(migrate(self.root)["files"], 2)
        self.assertEqual(self.history.read_bytes(), old)
        report = migrate(self.root, write=True)
        self.assertTrue(Path(report["backup"]).is_dir())
        history = [json.loads(line) for line in self.history.read_text().splitlines()]
        for before, after in zip((self.older, self.latest), history):
            self.assertEqual({key: after[key] for key in before}, before)
            self.assertEqual(after["candidate_id"], "baseline")
            self.assertEqual(after["candidate_revision"], before["case_revision"])
        self.assertEqual(source_path.read_bytes(), source)
        self.assertEqual((self.case_root / "translation.en.txt").read_bytes(), english)
        self.assertEqual(migrate(self.root, write=True)["files"], 0)

    def test_anonymization_preserves_text_ratings_and_private_mapping(self):
        case = self.multi_candidate()
        before_text = {c["candidate_id"]: (self.case_root / c["translation_file"]).read_bytes() for c in case["candidates"]}
        before_ratings = [json.loads(line) for line in self.history.read_text().splitlines()]
        result = anonymize(self.root, write=True)
        self.assertEqual(result["candidates"], 2)
        mappings = json.loads(Path(result["private_mapping"]).read_text(encoding="utf-8"))
        by_old = {item["old_id"]: item for item in mappings}
        current = json.loads((self.case_root / "case.json").read_text(encoding="utf-8"))
        for item in mappings:
            self.assertRegex(item["new_id"], r"^c-[a-f0-9]{16}$")
            self.assertEqual((self.case_root / item["new_file"]).read_bytes(), before_text[item["old_id"]])
        variant = next(c for c in current["candidates"] if c["candidate_id"] == by_old["adverse"]["new_id"])
        self.assertEqual(variant["derived_from"], by_old["baseline"]["new_id"])
        after_ratings = [json.loads(line) for line in self.history.read_text(encoding="utf-8").splitlines()]
        for old, new in zip(before_ratings, after_ratings):
            self.assertEqual(new["candidate_id"], by_old[old["candidate_id"]]["new_id"])
            self.assertEqual({k:v for k,v in new.items() if k!="candidate_id"}, {k:v for k,v in old.items() if k!="candidate_id"})
        self.assertEqual(anonymize(self.root, write=True)["candidates"], 0)
        # Private identity and provenance still never enter judge requests.
        prepared = self.prepared(candidate_id=variant["candidate_id"])
        self.assertNotIn("SECRET_VARIANT_LABEL", json.dumps(prepared["request"]))

    def test_minimal_generation_preserves_other_candidates_and_reviews_and_resumes(self):
        self.multi_candidate()
        history = self.history.read_bytes()
        baseline = (self.case_root / "translation.en.txt").read_bytes()
        task = prepare_tasks(self.root, [CASE_ID], instructions=generator.PROMPT)[0]
        request = generator.request_for(task, "azure/openai/gpt-4.1-mini")
        self.assertEqual(request["messages"], [
            {"role": "system", "content": "translate the Chinese to English"},
            {"role": "user", "content": task["input"]["source_text"]},
        ])
        response = {
            "model": "gpt-4.1-mini", "created": 1,
            "usage": {"completion_tokens_details": {"reasoning_tokens": 0}},
            "choices": [{"finish_reason": "stop", "message": {"content": "Synthetic transport fixture, not an actual translation."}}],
        }
        destination = self.root / "results/generation-test"
        destination.mkdir(parents=True)
        args = Namespace(model="azure/openai/gpt-4.1-mini", candidate_id=None)
        with patch.object(generator, "call_model", return_value=response) as model:
            first = generator.generate(task, args, self.root, destination, "https://example.test/v1/chat/completions", "fake")
            # Older run artifacts lack an ID assignment; recover the published
            # opaque identity from request/source provenance rather than duplicate it.
            (destination / CASE_ID / "candidate-id.json").unlink()
            args.resume = destination
            second = generator.generate(task, args, self.root, destination, "https://example.test/v1/chat/completions", "fake")
        self.assertEqual(model.call_count, 1)
        self.assertEqual(first["published"][CASE_ID], "published")
        self.assertEqual(second["published"][CASE_ID], "unchanged")
        self.assertEqual(self.history.read_bytes(), history)
        self.assertEqual((self.case_root / "translation.en.txt").read_bytes(), baseline)
        case = json.loads((self.case_root / "case.json").read_text(encoding="utf-8"))
        self.assertEqual(len(case["candidates"]), 3)
        self.assertRegex(first["candidate_id"], r"^c-[a-f0-9]{16}$")
        self.assertEqual(first["candidate_id"], second["candidate_id"])
        generated = next(c for c in case["candidates"] if c["candidate_id"] == first["candidate_id"])
        self.assertEqual(generated["provenance"]["instruction"], generator.PROMPT)

    def test_minimal_generator_rejects_reasoning_models_and_truncated_responses(self):
        task = prepare_tasks(self.root, [CASE_ID])[0]
        with self.assertRaisesRegex(judge.EvaluationError, "non-reasoning"):
            generator.request_for(task, "reasoning-model")
        with self.assertRaisesRegex(judge.EvaluationError, "Incomplete"):
            generator.output_text({"choices": [{"finish_reason": "length", "message": {"content": "Partial"}}]})
        with self.assertRaisesRegex(judge.EvaluationError, "reasoning tokens"):
            generator.output_text({
                "choices": [{"finish_reason": "stop", "message": {"content": "Text"}}],
                "usage": {"completion_tokens_details": {"reasoning_tokens": 10}},
            })

    def test_judge_only_can_prepare_case_candidate_without_human_file(self):
        self.history.unlink()
        with patch.object(judge, "call_model", side_effect=AssertionError("Prepare must not call a model")):
            destination, manifest = judge.run(self.args(
                mode="judge", reviewer=None, smoke_test=False, model=None,
            ))
        self.assertEqual(manifest["status"], "prepared")
        self.assertEqual(manifest["purpose"], "judge")
        self.assertTrue((destination / CASE_ID / "request.json").exists())

    def test_judge_mode_rejects_skill_files_as_translation_outputs(self):
        with self.assertRaisesRegex(judge.EvaluationError, "not skill instructions"):
            judge.prepare_case(self.root, CASE_ID, purpose="judge",
                               translation_file=self.root / "judges/literary-translation-judge/SKILL.md")

    def test_mode_boundaries_reject_ambiguous_arguments(self):
        for arguments in (
            self.args(mode="judge"),
            self.args(mode="evaluate", translation_file=self.case_root / "translation.en.txt"),
            self.args(mode="judge", reviewer=None, case=None, all=True, translation_file=self.case_root / "translation.en.txt"),
            self.args(mode="export-training", prepare_only=True),
            self.args(mode="export-training", prepare_only=False, reviewer=None),
        ):
            with self.subTest(mode=arguments.mode), self.assertRaises(judge.EvaluationError):
                judge.run(arguments)

    def test_judge_only_rejects_external_translation_changed_during_scoring(self):
        candidate = self.root.parent / "candidate.txt"
        candidate.write_text("Initial candidate.", encoding="utf-8")

        def call(*args):
            candidate.write_text("Changed candidate.", encoding="utf-8")
            return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(PREDICTION)}}]}

        with patch.dict(os.environ, {"EVAL_TEST_KEY": "fake"}):
            with patch.object(judge, "call_model", side_effect=call):
                destination, manifest = judge.run(self.args(
                    mode="judge", reviewer=None, translation_file=candidate, prepare_only=False,
                ))
        self.assertEqual(manifest["status"], "failed")
        self.assertIn("Inputs changed", manifest["cases"][0]["error"])
        self.assertFalse((destination / CASE_ID / "comparison.json").exists())

    def test_current_case_requires_explicit_smoke_mode(self):
        with self.assertRaisesRegex(judge.EvaluationError, "smoke-test"):
            judge.prepare_case(self.root, CASE_ID)

    def test_invalid_case_binding_and_path_escape_are_rejected(self):
        path = self.case_root / "case.json"
        original = path.read_bytes()
        for field, value in (
            ("source_file", "../../../server/app.py"),
            ("translation_file", "../../../rubrics/literary-translation-quality-v1.json"),
            ("source_metadata_file", "C:/private/secret.json"),
            ("source_revision", 2),
        ):
            with self.subTest(field=field):
                metadata = json.loads(original)
                metadata[field] = value
                path.write_text(json.dumps(metadata), encoding="utf-8")
                with self.assertRaises(judge.EvaluationError):
                    self.prepared()
                path.write_bytes(original)

    def test_latest_matching_leaf_is_used_not_last_line_from_another_reviewer(self):
        other = {**self.latest, "judgment_id": "other", "rater_id": "another-reviewer", "supersedes_judgment_id": None}
        self.write_history([self.older, self.latest, other])
        selected, digest = judge.human_reference(self.prepared(), REVIEWER)
        self.assertEqual(selected["judgment_id"], "latest")
        self.assertEqual(len(digest), 64)

    def test_placeholder_can_be_prepared_but_is_not_a_human_reference(self):
        placeholder = {
            **self.older, "rater_id": None, "rubric_version": None,
            "status": "pending", "overall_score": None,
            "dimension_scores": {name: None for name in judge.DIMENSIONS},
            "rationale": None, "issues": [],
        }
        self.write_history([placeholder])
        prepared = self.prepared()
        self.assertEqual(prepared["case"]["case_id"], CASE_ID)
        with self.assertRaisesRegex(judge.EvaluationError, "No current human judgment"):
            judge.human_reference(prepared, REVIEWER)

    def test_latest_draft_does_not_fall_back_to_a_completed_review(self):
        draft = {**self.latest, "judgment_id": "draft", "status": "pending", "supersedes_judgment_id": "latest"}
        self.write_history([self.older, self.latest, draft])
        with self.assertRaisesRegex(judge.EvaluationError, "draft"):
            judge.human_reference(self.prepared(), REVIEWER)

    def test_invalid_history_and_mismatched_versions_fail(self):
        for records in (
            [self.latest],
            [self.older, self.older],
            [{**self.older, "case_revision": 9}],
            [{**self.older, "rubric_version": "obsolete"}],
        ):
            with self.subTest(records=len(records)):
                self.write_history(records)
                with self.assertRaises(judge.EvaluationError):
                    judge.human_reference(self.prepared(), REVIEWER)

    def test_prediction_validation_rejects_wrong_scores_and_extra_fields(self):
        for score in (True, 0, 6, 4.5, "4", None):
            prediction = copy.deepcopy(PREDICTION)
            prediction["overall_score"] = score
            with self.subTest(score=score), self.assertRaises(judge.EvaluationError):
                judge.validate_prediction(prediction)
        for prediction in (
            {**PREDICTION, "confidence": 1},
            {**PREDICTION, "dimension_scores": {"fidelity": 4}},
            {**PREDICTION, "rationale": ""},
        ):
            with self.assertRaises(judge.EvaluationError):
                judge.validate_prediction(prediction)

    def test_json_and_incomplete_api_response_are_rejected(self):
        for content in ('{"score":1,"score":2}', '{"score":NaN}', "```json\n{}\n```"):
            with self.assertRaises(judge.EvaluationError):
                judge.parse_json(content)
        for response in (
            {}, {"choices": []},
            {"choices": [{"finish_reason": "stop", "message": None}]},
            {"choices": [{"finish_reason": "length", "message": {"content": json.dumps(PREDICTION)}}]},
        ):
            with self.assertRaises(judge.EvaluationError):
                judge.extract_prediction(response)

    def test_metrics_skip_missing_human_dimensions(self):
        human = {**self.latest, "dimension_scores": {"fidelity": 2, "english_naturalness": None}}
        comparison = judge.compare(PREDICTION, human)
        self.assertEqual(comparison["overall_score"]["signed_error"], -1)
        self.assertEqual(comparison["fidelity"]["signed_error"], 1)
        self.assertIsNone(comparison["english_naturalness"]["absolute_error"])
        summary = judge.aggregate([comparison])
        self.assertEqual(summary["overall_score"]["mean_absolute_error"], 1)
        self.assertEqual(summary["overall_score"]["exact_agreement_rate"], 0)
        self.assertEqual(summary["literary_voice"]["count"], 0)
        self.assertIsNone(summary["literary_voice"]["mean_absolute_error"])

    def test_api_configuration_and_missing_credentials_fail_safely(self):
        for url in ("http://remote.example/v1", "https://user:secret@example.test/v1", "https://example.test/v1?key=secret"):
            with self.assertRaises(judge.EvaluationError):
                judge.endpoint(url)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(judge.EvaluationError, "not set"):
                judge.run(self.args(prepare_only=False))

    def test_end_to_end_http_fixture_against_current_case_texts(self):
        captured = []
        events = []
        test = self
        human_reader = judge.human_reference
        read = judge.read_bytes

        def observed_read(path, area):
            if Path(path).name == "judgments.jsonl":
                events.append("human_scores_read")
            return read(path, area)

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                events.append("model_called")
                captured.append(json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")))
                body = json.dumps({
                    "id": "fixture-response", "model": "fixture-not-an-llm",
                    "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": json.dumps(PREDICTION)}}],
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        def reference_after_prediction(prepared, reviewer):
            predictions = list((test.root / "results").glob(f"*/{CASE_ID}/prediction.json"))
            test.assertEqual(len(predictions), 1)
            events.append("prediction_saved")
            return human_reader(prepared, reviewer)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        original = self.history.read_bytes()
        try:
            with patch.dict(os.environ, {"EVAL_TEST_KEY": "PRIVATE_TEST_KEY"}):
                with patch.object(judge, "human_reference", side_effect=reference_after_prediction):
                    with patch.object(judge, "read_bytes", side_effect=observed_read):
                        destination, manifest = judge.run(self.args(
                            prepare_only=False, base_url=f"http://127.0.0.1:{server.server_port}/v1",
                        ))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        self.assertEqual(manifest["status"], "completed")
        self.assertFalse(manifest["benchmark_eligible"])
        self.assertEqual(len(captured), 1)
        self.assertEqual(events, ["model_called", "prediction_saved", "human_scores_read"])
        self.assertEqual(set(json.loads(captured[0]["messages"][1]["content"])), {"source_text", "translation_text"})
        self.assertNotIn(REVIEWER, json.dumps(captured[0]))
        self.assertNotIn("SECRET_HUMAN", json.dumps(captured[0]))
        comparison = json.loads((destination / CASE_ID / "comparison.json").read_text(encoding="utf-8"))
        self.assertEqual(comparison["human_judgment_id"], "latest")
        self.assertEqual(comparison["scores"]["overall_score"]["absolute_error"], 1)
        summary = json.loads((destination / "summary.json").read_text())
        self.assertEqual(summary["cases_compared"], 1)
        self.assertEqual(summary["metrics"]["english_naturalness"]["exact_agreement_rate"], 1)
        for artifact in destination.rglob("*.json"):
            self.assertNotIn("PRIVATE_TEST_KEY", artifact.read_text(encoding="utf-8"))
        self.assertEqual(self.history.read_bytes(), original)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            judge.print_report(destination, manifest)
        report = output.getvalue()
        self.assertIn("Model: fixture-not-an-llm", report)
        self.assertIn("Human judgment: latest", report)
        self.assertIn("LLM-human", report)
        self.assertIn("Abs error", report)
        self.assertRegex(report, r"Overall\s+4\s+3\s+-1\s+1")
        self.assertRegex(report, r"Fidelity\s+2\s+3\s+\+1\s+1")
        self.assertIn("Compared: 1/1; failed: 0", report)
        self.assertIn("100.0%", report)
        self.assertIn(PREDICTION["rationale"], report)

    def test_failed_model_output_is_recorded_not_compared(self):
        response = {"choices": [{"finish_reason": "stop", "message": {"content": '{"overall_score":99}'}}]}
        with patch.dict(os.environ, {"EVAL_TEST_KEY": "fake"}):
            with patch.object(judge, "call_model", return_value=response):
                destination, manifest = judge.run(self.args(prepare_only=False))
        self.assertEqual(manifest["status"], "failed")
        self.assertFalse((destination / CASE_ID / "comparison.json").exists())
        summary = json.loads((destination / "summary.json").read_text())
        self.assertEqual(summary["cases_failed"], 1)
        self.assertEqual(summary["cases_compared"], 0)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            judge.print_report(destination, manifest)
        self.assertIn("Evaluation failed:", output.getvalue())
        self.assertIn("judge quality cannot be assessed", output.getvalue())
        self.assertNotIn("0.00", output.getvalue())

    def test_console_reports_missing_human_dimensions_as_unavailable(self):
        self.latest["dimension_scores"] = {"fidelity": 2}
        self.write_history([self.older, self.latest])
        response = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(PREDICTION)}}]}
        with patch.dict(os.environ, {"EVAL_TEST_KEY": "fake"}):
            with patch.object(judge, "call_model", return_value=response):
                destination, manifest = judge.run(self.args(prepare_only=False))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            judge.print_report(destination, manifest)
        self.assertRegex(output.getvalue(), r"English naturalness\s+n/a\s+4\s+n/a\s+n/a")
        self.assertRegex(output.getvalue(), r"English naturalness\s+0\s+n/a\s+n/a\s+n/a")

    def test_console_prints_chinese_rationale_with_legacy_windows_encoding(self):
        prediction = {**PREDICTION, "rationale": "原文与译文的语气存在差异。"}
        response = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(prediction)}}]}
        with patch.dict(os.environ, {"EVAL_TEST_KEY": "fake"}):
            with patch.object(judge, "call_model", return_value=response):
                destination, manifest = judge.run(self.args(prepare_only=False))
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="cp1252")
        try:
            with contextlib.redirect_stdout(stream):
                judge.print_report(destination, manifest)
            stream.flush()
            self.assertIn(prediction["rationale"], buffer.getvalue().decode("utf-8"))
        finally:
            stream.detach()

    def test_changed_inputs_block_comparison(self):
        def call(*args):
            path = self.case_root / "translation.en.txt"
            path.write_bytes(path.read_bytes() + b"\nChanged during generation")
            return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(PREDICTION)}}]}

        with patch.dict(os.environ, {"EVAL_TEST_KEY": "fake"}):
            with patch.object(judge, "call_model", side_effect=call):
                destination, manifest = judge.run(self.args(prepare_only=False))
        self.assertEqual(manifest["status"], "failed")
        self.assertTrue((destination / CASE_ID / "prediction.json").is_file())
        self.assertFalse((destination / CASE_ID / "comparison.json").exists())

    def test_cli_prepare_all_and_smoke_scope(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = judge.main(["--all", "--data-dir", str(self.root), "--smoke-test", "--prepare-only"])
        self.assertEqual(status, 0)
        self.assertIn("prepared: 1 case(s)", output.getvalue())
        self.assertIn("Exploratory smoke test", output.getvalue())
        self.assertIn("No model was called. No prediction or evaluation result is available.", output.getvalue())
        self.assertNotIn("LLM-human", output.getvalue())


if __name__ == "__main__":
    unittest.main()
