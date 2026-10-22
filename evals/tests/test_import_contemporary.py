import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import import_contemporary as importer


class CorpusImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name).resolve()
        self.corpus, self.output = base / "corpus", base / "evals"
        (self.corpus / "fetched").mkdir(parents=True)
        (self.corpus / "source_cache").mkdir()
        self.output.mkdir()
        snapshot = b'<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC BY-SA 3.0</a>'
        for host in ("scp-cn.wiki", "scp-int.wikidot.com"):
            (self.corpus / "source_cache" / f"{host}_test-story.html").write_bytes(snapshot)
        (self.corpus / "fetched/test-story.json").write_text(json.dumps({
            language: {"licensed": True, "blocks": ["one", "two", "three", "four"]}
            for language in ("chinese", "english")
        }), encoding="utf-8")
        self.records = []
        for number in (1, 2):
            self.records.append({
                "id": f"contemporary-{number:03d}", "source_work_id": "test-story",
                "title_zh": "测试故事", "title_en": "Test story", "author": "Original author",
                "translator": "Credited translator", "genre": "Speculative fiction",
                "selection_type": "complete_scene_or_story", "english_word_count": 501,
                "chinese": f"第{number}段中文。\n\n保留段落。",
                "english": f"Passage{number} " + "word " * 499,
                "sources": {
                    "chinese": "https://scp-cn.wiki/test-story",
                    "english": "https://scp-int.wikidot.com/test-story",
                    "author_credit": "https://scp-int.wikidot.com/cn-hub",
                    "english_history": "https://scp-int.wikidot.com/test-story/history",
                    "retrieved_date": "2026-10-19",
                    "extracted_block_ranges_exclusive": {
                        language: [(number - 1) * 2, number * 2]
                        for language in ("chinese", "english")
                    },
                },
                "rights": {
                    "status": "explicitly_licensed_not_public_domain",
                    "license": "CC BY-SA 3.0", "license_url": importer.LICENSE_URL,
                    "attribution": "Test story, Original author; English translation, Credited translator. CC BY-SA 3.0.",
                    "evidence": "License links in retained snapshots.",
                    "source_credits": {"chinese": ["Original author"], "english": ["Credited translator"]},
                },
                "review": {
                    "reviewer": "AI", "boundary_rationale": "A complete passage.",
                    "alignment": "Passage-level, not human-certified.",
                    "normalization": "Paragraphs retained.", "context": "Shared story context.",
                },
                "source_snapshot_sha256": {
                    language: hashlib.sha256(snapshot).hexdigest() for language in ("chinese", "english")
                },
            })
        self.save_records()

    def save_records(self):
        (self.corpus / "contemporary_pairs.jsonl").write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in self.records), encoding="utf-8"
        )

    def test_import_preserves_text_attribution_and_work_grouping(self):
        report = importer.import_corpus(self.corpus, self.output)
        self.assertEqual((report["pairs"], report["works"]), (2, 1))
        for record in self.records:
            directory = self.output / "cases/literary-translation" / ("zh-en-" + record["id"])
            case = json.loads((directory / "case.json").read_text(encoding="utf-8"))
            source = (directory / case["source_file"]).resolve()
            passage = json.loads((directory / case["source_metadata_file"]).read_text(encoding="utf-8"))
            self.assertEqual(source.read_bytes(), record["chinese"].encode("utf-8"))
            self.assertEqual((directory / case["candidates"][0]["translation_file"]).read_bytes(), record["english"].encode("utf-8"))
            self.assertEqual((directory / "judgments.jsonl").read_bytes(), b"")
            self.assertEqual(case["group_id"], "contemporary-test-story")
            self.assertEqual(passage["group_id"], case["group_id"])
            self.assertEqual(passage["passage_id"], case["passage_id"])
            self.assertEqual(case["schema_version"], 2)
            candidate = case["candidates"][0]
            self.assertRegex(candidate["candidate_id"], r"^c-[a-f0-9]{16}$")
            self.assertEqual(candidate["provenance"]["attribution"], record["rights"]["attribution"])
            self.assertEqual(candidate["provenance"]["source_credits"], ["Credited translator"])
            self.assertEqual(passage["provenance"]["source_credits"], ["Original author"])
            self.assertEqual(candidate["provenance"]["usage_rights"], "permitted")
            self.assertEqual(candidate["provenance"]["corpus_review"], record["review"])
        self.assertTrue((self.output / "imports/contemporary-corpus/manifest.json").is_file())

    def test_repeat_import_preserves_new_human_judgments(self):
        importer.import_corpus(self.corpus, self.output)
        path = self.output / "cases/literary-translation/zh-en-contemporary-001/judgments.jsonl"
        review = b'{"judgment_id":"human-review","case_id":"zh-en-contemporary-001","rater_id":"human","overall_score":4}\n'
        path.write_bytes(review)
        report = importer.import_corpus(self.corpus, self.output)
        self.assertEqual(report["new_directories"], 0)
        self.assertEqual(path.read_bytes(), review)

    def test_repeat_import_preserves_added_candidates(self):
        importer.import_corpus(self.corpus, self.output)
        directory = self.output / "cases/literary-translation/zh-en-contemporary-001"
        path = directory / "case.json"
        case = json.loads(path.read_text(encoding="utf-8"))
        case["candidates"].append({
            "candidate_id": "variant", "revision": 1, "translation_file": "variant.en.txt",
            "status": "placeholder", "provenance": {},
        })
        path.write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
        (directory / "variant.en.txt").write_text("Additional candidate.")
        before = path.read_bytes()
        importer.import_corpus(self.corpus, self.output)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual((directory / "variant.en.txt").read_text(), "Additional candidate.")

    def test_dry_run_does_not_create_files(self):
        report = importer.import_corpus(self.corpus, self.output, dry_run=True)
        self.assertEqual(report["pairs"], 2)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_conflicts_are_detected_before_any_import_writes(self):
        directory = self.output / "cases/literary-translation/zh-en-contemporary-001"
        directory.mkdir(parents=True)
        (directory / "case.json").write_text('{"keep":"local work"}', encoding="utf-8")
        with self.assertRaises(importer.EvaluationError):
            importer.import_corpus(self.corpus, self.output)
        self.assertFalse((self.output / "fixtures").exists())
        self.assertEqual((directory / "case.json").read_text(), '{"keep":"local work"}')

    def test_snapshot_mismatch_is_rejected(self):
        (self.corpus / "source_cache/scp-cn.wiki_test-story.html").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(importer.EvaluationError, "hash mismatch"):
            importer.import_corpus(self.corpus, self.output)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_overlapping_ranges_and_missing_license_are_rejected(self):
        original = copy.deepcopy(self.records)
        self.records[1]["sources"]["extracted_block_ranges_exclusive"]["chinese"] = [1, 3]
        self.save_records()
        with self.assertRaisesRegex(importer.EvaluationError, "overlapping"):
            importer.import_corpus(self.corpus, self.output)
        self.records = original
        self.records[0]["rights"]["attribution"] = ""
        self.save_records()
        with self.assertRaisesRegex(importer.EvaluationError, "license and attribution"):
            importer.import_corpus(self.corpus, self.output)


if __name__ == "__main__":
    unittest.main()
