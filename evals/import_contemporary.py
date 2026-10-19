"""Import the locally collected contemporary Chinese/English pairs without rewriting text."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from run_judge import EvaluationError, guarded, identifier, object_json, read_bytes, sha

ROOT = Path(__file__).resolve().parent
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/3.0/"
WORDS = re.compile(r"[A-Za-z]+(?:['’\-][A-Za-z]+)*|\d+(?:[.,]\d+)*")


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def load_records(corpus):
    raw = read_bytes(corpus / "contemporary_pairs.jsonl", corpus)
    records = [object_json(line) for line in raw.splitlines() if line.strip()]
    if not records:
        raise EvaluationError("The corpus has no passage pairs.")
    ids, pairs, intervals, snapshots, works = set(), set(), {}, {}, {}
    for record in records:
        rid, work = identifier(record["id"]), identifier(record["source_work_id"])
        if not re.fullmatch(r"contemporary-\d{3}", rid) or rid in ids:
            raise EvaluationError("Corpus record IDs must be unique contemporary-NNN identifiers.")
        ids.add(rid)
        for language in ("chinese", "english"):
            if not isinstance(record.get(language), str) or not record[language].strip():
                raise EvaluationError(f"{rid}: both language texts must be nonblank.")
        if not re.search(r"[\u3400-\u9fff]", record["chinese"]):
            raise EvaluationError(f"{rid}: the Chinese passage contains no Chinese characters.")
        words = len(WORDS.findall(record["english"]))
        if not 500 <= words <= 700 or words != record["english_word_count"]:
            raise EvaluationError(f"{rid}: English word count does not match the corpus specification.")
        pair = (sha(record["chinese"].encode("utf-8")), sha(record["english"].encode("utf-8")))
        if pair in pairs:
            raise EvaluationError(f"{rid}: duplicate bilingual pair.")
        pairs.add(pair)
        rights = record["rights"]
        if (
            rights.get("license") != "CC BY-SA 3.0" or rights.get("license_url") != LICENSE_URL
            or rights.get("status") != "explicitly_licensed_not_public_domain"
            or not rights.get("attribution") or not rights.get("evidence")
        ):
            raise EvaluationError(f"{rid}: complete corpus license and attribution records are required.")
        if not record["review"].get("boundary_rationale"):
            raise EvaluationError(f"{rid}: passage boundary review is missing.")
        identity = (record["title_zh"], record["title_en"], record["author"], record["genre"])
        if work in works and works[work] != identity:
            raise EvaluationError(f"{rid}: inconsistent work metadata.")
        works[work] = identity
        fetched = object_json(read_bytes(corpus / "fetched" / f"{work}.json", corpus / "fetched"))
        for language, host in (("chinese", "scp-cn.wiki"), ("english", "scp-int.wikidot.com")):
            if fetched[language].get("licensed") is not True:
                raise EvaluationError(f"{rid}: saved source has no recorded license evidence.")
            interval = record["sources"]["extracted_block_ranges_exclusive"][language]
            if (
                not isinstance(interval, list) or len(interval) != 2
                or any(type(n) is not int for n in interval)
                or not 0 <= interval[0] < interval[1] <= len(fetched[language]["blocks"])
            ):
                raise EvaluationError(f"{rid}: invalid extraction range.")
            previous = intervals.setdefault((work, language), [])
            if any(max(lo, interval[0]) < min(hi, interval[1]) for lo, hi in previous):
                raise EvaluationError(f"{rid}: overlapping corpus passage ranges.")
            previous.append(interval)
            key = (work, language)
            if key not in snapshots:
                snapshots[key] = sha(read_bytes(
                    corpus / "source_cache" / f"{host}_{work}.html", corpus / "source_cache",
                ))
            if snapshots[key] != record["source_snapshot_sha256"][language]:
                raise EvaluationError(f"{rid}: source snapshot hash mismatch.")
    return sorted(records, key=lambda record: record["id"]), sha(raw)


def build_plan(records, corpus_hash):
    plan, mapping = {}, []
    for record in records:
        group = identifier("contemporary-" + record["source_work_id"])
        rid = record["id"]
        case_id = identifier("zh-en-" + rid)
        number = rid.rsplit("-", 1)[1]
        passage_id = identifier(f"{group}-passage-{number}")
        passage_directory = Path("fixtures/manuscripts") / group / f"passage-{number}"
        case_directory = Path("cases/literary-translation") / case_id
        sources, rights, review = record["sources"], record["rights"], record["review"]
        common = {
            "usage_rights": "permitted",
            "license": rights["license"], "license_url": rights["license_url"],
            "attribution": rights["attribution"],
            "license_evidence": rights["evidence"],
            "corpus_collection": "contemporary_corpus", "corpus_record_id": rid,
            "source_work_id": record["source_work_id"],
            "retrieved_date": sources["retrieved_date"],
            "modifications": "Imported verbatim from contemporary_pairs.jsonl; no additional wording or normalization changes.",
        }
        passage = {
            "schema_version": 1, "group_id": group, "passage_id": passage_id, "revision": 1,
            "source_language": "zh", "source_file": "source.zh.txt",
            "work": {"title": record["title_zh"], "title_en": record["title_en"], "author": record["author"]},
            "context": {"genre": record["genre"], "background": review.get("context")},
            "provenance": {
                **common, "source_origin": "published Chinese original",
                "source_url": sources["chinese"], "author_credit_url": sources.get("author_credit"),
                "source_credits": rights["source_credits"]["chinese"],
                "source_snapshot_sha256": record["source_snapshot_sha256"]["chinese"],
                "extracted_block_range_exclusive": sources["extracted_block_ranges_exclusive"]["chinese"],
                "corpus_review": review,
            },
        }
        case = {
            "schema_version": 1, "case_id": case_id, "revision": 1, "status": "ready",
            "task": "literary-translation-quality", "source_language": "zh", "target_language": "en",
            "source_file": Path(os.path.relpath(passage_directory / "source.zh.txt", case_directory)).as_posix(),
            "source_metadata_file": Path(os.path.relpath(passage_directory / "passage.json", case_directory)).as_posix(),
            "source_revision": 1, "translation_file": "translation.en.txt",
            "group_id": group, "passage_id": passage_id,
            "rubric_id": "literary-translation-quality-v1", "context": {"brief": None},
            "provenance": {
                **common, "translation_origin": "published English translation",
                "translator": record["translator"], "title_en": record["title_en"],
                "source_url": sources["english"], "english_history_url": sources.get("english_history"),
                "source_credits": rights["source_credits"]["english"],
                "source_snapshot_sha256": record["source_snapshot_sha256"]["english"],
                "extracted_block_range_exclusive": sources["extracted_block_ranges_exclusive"]["english"],
                "english_word_count": record["english_word_count"],
                "selection_type": record["selection_type"], "corpus_review": review,
            },
        }
        source_bytes, translation_bytes = record["chinese"].encode("utf-8"), record["english"].encode("utf-8")
        plan[passage_directory] = {"passage.json": encoded(passage), "source.zh.txt": source_bytes}
        plan[case_directory] = {
            "case.json": encoded(case), "translation.en.txt": translation_bytes, "judgments.jsonl": b"",
        }
        mapping.append({
            "corpus_record_id": rid, "case_id": case_id, "source_work_id": record["source_work_id"],
            "group_id": group, "passage_id": passage_id,
            "case_file": (case_directory / "case.json").as_posix(),
            "passage_file": (passage_directory / "passage.json").as_posix(),
            "source_text_sha256": sha(source_bytes), "translation_text_sha256": sha(translation_bytes),
        })
    manifest = {
        "schema_version": 1, "collection": "contemporary_corpus",
        "source_file": "contemporary_corpus/contemporary_pairs.jsonl",
        "source_file_sha256": corpus_hash, "pairs": len(records),
        "works": len({record["source_work_id"] for record in records}),
        "license": "CC BY-SA 3.0", "license_url": LICENSE_URL,
        "alignment_review": "AI-reviewed passage alignment; not independently human-certified.",
        "modifications": "Text copied verbatim from the corpus JSONL. Metadata mapped to the evaluation format.",
        "human_scores": "Not imported. New judgment files are empty.",
        "split_policy": "Keep all passages and translation variants sharing group_id in one dataset split.",
        "records": mapping,
    }
    plan[Path("imports/contemporary-corpus")] = {"manifest.json": encoded(manifest)}
    return plan, manifest


def import_corpus(corpus, data_root, *, dry_run=False):
    corpus, data_root = guarded(corpus, corpus), guarded(data_root, data_root)
    if not data_root.is_dir():
        raise EvaluationError("The evaluation data directory must already exist.")
    records, corpus_hash = load_records(corpus)
    plan, manifest = build_plan(records, corpus_hash)
    missing, unchanged = [], 0
    for relative, files in plan.items():
        directory = guarded(data_root / relative, data_root)
        if directory.exists():
            if not directory.is_dir():
                raise EvaluationError(f"Import destination is not a directory: {relative}")
            for filename, expected in files.items():
                path = guarded(directory / filename, data_root)
                if not path.is_file():
                    raise EvaluationError(f"Existing import is incomplete: {relative / filename}")
                if filename != "judgments.jsonl" and read_bytes(path, data_root) != expected:
                    raise EvaluationError(f"Refusing to overwrite changed data: {relative / filename}")
            unchanged += 1
        else:
            missing.append((relative, files))
    if not dry_run and missing:
        with tempfile.TemporaryDirectory(prefix=".contemporary-import-", dir=data_root) as temporary:
            staging = Path(temporary)
            for relative, files in missing:
                directory = staging / relative
                directory.mkdir(parents=True, exist_ok=True)
                for filename, content in files.items():
                    (directory / filename).write_bytes(content)
            for relative, _ in sorted(missing, key=lambda item: (not str(item[0]).startswith("fixtures"), str(item[0]))):
                destination = guarded(data_root / relative, data_root)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    raise EvaluationError(f"Destination appeared during import: {relative}")
                (staging / relative).rename(destination)
    return {**manifest, "new_directories": len(missing), "unchanged_directories": unchanged, "dry_run": dry_run}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Import validated contemporary corpus pairs into literary-translation eval cases.")
    parser.add_argument("--corpus", type=Path, default=ROOT.parent / "contemporary_corpus")
    parser.add_argument("--data-dir", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = import_corpus(args.corpus, args.data_dir, dry_run=args.dry_run)
        print(f"{'Preview' if args.dry_run else 'Imported'}: {report['pairs']} pairs from {report['works']} works")
        print(f"New directories: {report['new_directories']}; unchanged: {report['unchanged_directories']}")
        print("Chinese and English wording preserved; new judgment files are empty and existing reviews are preserved.")
        print("License and attribution retained: CC BY-SA 3.0")
        return 0
    except (EvaluationError, OSError, KeyError, TypeError, UnicodeError) as exc:
        print(f"import-contemporary: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
