"""Export one source-only translator input per distinct source/task, never per candidate."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

if __package__:
    from .run_judge import ROOT, EvaluationError, guarded, identifier, object_json, read_bytes, reference, sha
    from .translation_cases import discover_cases
else:
    from run_judge import ROOT, EvaluationError, guarded, identifier, object_json, read_bytes, reference, sha
    from translation_cases import discover_cases


def prepare_tasks(root, case_ids, *, instructions=None):
    root = Path(root).resolve()
    tasks = {}
    for cid in dict.fromkeys(case_ids):
        directory = root / "cases/literary-translation" / identifier(cid)
        case = object_json(read_bytes(directory / "case.json", root / "cases/literary-translation"))
        if case.get("case_id") != cid or case.get("task") != "literary-translation-quality":
            raise EvaluationError("Invalid translation task.")
        if case.get("schema_version") not in {1, 2}:
            raise EvaluationError("Unsupported translation case version.")
        source_meta_path = reference(directory, case.get("source_metadata_file"), root / "fixtures/manuscripts")
        if source_meta_path.name != "passage.json":
            raise EvaluationError("Expected shared passage metadata.")
        source = object_json(read_bytes(source_meta_path, root / "fixtures/manuscripts"))
        if any(case.get(key) != source.get(key) for key in ("group_id", "passage_id", "source_language")):
            raise EvaluationError("Source identity does not match the case.")
        if (type(case.get("source_revision")) is not int or case["source_revision"] < 1
                or type(source.get("revision")) is not int or case["source_revision"] != source["revision"]):
            raise EvaluationError("Invalid source revision.")
        source_path = reference(directory, case.get("source_file"), root / "fixtures/manuscripts")
        if source_path.suffix != ".txt":
            raise EvaluationError("Shared source must be a text file.")
        if source_path != reference(source_meta_path.parent, source.get("source_file"), source_meta_path.parent):
            raise EvaluationError("Source references disagree.")
        raw = read_bytes(source_path, root / "fixtures/manuscripts")
        source_text = raw.decode("utf-8")
        if not source_text.strip():
            raise EvaluationError("Translator input requires nonempty source text.")
        instruction = instructions if instructions is not None else case.get("translation_instructions")
        if instruction is not None and (not isinstance(instruction, str) or not instruction.strip()):
            raise EvaluationError("Translation instructions must be nonblank text or null.")
        target = case.get("target_language")
        if not isinstance(target, str) or not target.strip():
            raise EvaluationError("A target language is required.")
        packet = {"source_text": source_text, "source_language": case["source_language"],
                  "target_language": target, "translation_instructions": instruction}
        identity = {"group_id": case["group_id"], "passage_id": case["passage_id"],
                    "source_revision": case["source_revision"], "source_sha256": sha(raw),
                    "target_language": target, "translation_instructions": instruction}
        key = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        if key not in tasks:
            tasks[key] = {"task_id": key, "case_id": cid, "case_ids": [], "identity": identity, "input": packet}
        tasks[key]["case_ids"].append(cid)
    return list(tasks.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--case", action="append")
    selection.add_argument("--all", action="store_true")
    parser.add_argument("--instructions-file", type=Path, help="Explicit translator instructions, never case evaluation notes.")
    args = parser.parse_args()
    root = args.data_dir.resolve()
    ids = args.case or [p.parent.name for p in discover_cases(root / "cases/literary-translation")]
    instructions = args.instructions_file.read_text(encoding="utf-8") if args.instructions_file else None
    tasks = prepare_tasks(root, ids, instructions=instructions)
    results = guarded(root / "results", root)
    results.mkdir(exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix="translation-inputs-", dir=results))
    index = []
    for task in tasks:
        filename = f"{task['task_id']}.json"
        (destination / filename).write_text(json.dumps(task["input"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        index.append({key: value for key, value in task.items() if key != "input"} | {"input_file": filename})
    (destination / "tasks.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(tasks)} unique translator tasks from {len(ids)} cases: {destination}")
    print("Only per-task input files go to the translator. Generation and scoring are separate steps.")


if __name__ == "__main__":
    main()
