"""Assign opaque candidate IDs/filenames while preserving texts and human ratings."""

import argparse
import json
import os
import tempfile
from pathlib import Path

if __package__:
    from .run_judge import ROOT, guarded, read_bytes, object_json, reference, sha
    from .translation_cases import candidates, discover_cases, migrate_case, new_candidate_id, OPAQUE_CANDIDATE
else:
    from run_judge import ROOT, guarded, read_bytes, object_json, reference, sha
    from translation_cases import candidates, discover_cases, migrate_case, new_candidate_id, OPAQUE_CANDIDATE


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def atomic(path, raw):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(raw)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def anonymize(root, *, write=False):
    root = Path(root).resolve()
    replacements, originals, outputs, obsolete, mapping = {}, {}, {}, set(), []
    for path in discover_cases(root / "cases/literary-translation"):
        raw = read_bytes(path, root)
        case = object_json(raw)
        values = candidates(case)
        if case.get("schema_version") == 2 and all(
            OPAQUE_CANDIDATE.fullmatch(c["candidate_id"])
            and c["translation_file"] == f"candidates/{c['candidate_id']}.en.txt" for c in values
        ):
            continue
        history_path = guarded(path.parent / "judgments.jsonl", root)
        history_raw = read_bytes(history_path, root) if history_path.exists() else b""
        history = [object_json(line) for line in history_raw.splitlines() if line.strip()]
        case, history = migrate_case(case, history)
        ids, used = {}, {c["candidate_id"] for c in case["candidates"]}
        for item in case["candidates"]:
            old_id = item["candidate_id"]
            new_id = old_id if OPAQUE_CANDIDATE.fullmatch(old_id) else new_candidate_id()
            while new_id != old_id and new_id in used:
                new_id = new_candidate_id()
            used.add(new_id)
            ids[old_id] = new_id
            old_file = reference(path.parent, item["translation_file"], path.parent)
            content = read_bytes(old_file, root)
            new_file = guarded(path.parent / "candidates" / f"{new_id}.en.txt", root)
            if new_file != old_file:
                if new_file.exists() and read_bytes(new_file, root) != content:
                    raise ValueError("Opaque candidate destination already contains different text.")
                outputs[new_file] = content
                obsolete.add(old_file)
                originals[old_file] = content
            mapping.append({"case_id": case["case_id"], "old_id": old_id, "new_id": new_id,
                            "old_file": item["translation_file"], "new_file": new_file.relative_to(path.parent).as_posix(),
                            "translation_sha256": sha(content)})
            item["candidate_id"] = new_id
            item["translation_file"] = new_file.relative_to(path.parent).as_posix()
        for item in case["candidates"]:
            if item.get("derived_from"):
                item["derived_from"] = ids[item["derived_from"]]
        case["candidates"].sort(key=lambda item: item["candidate_id"])
        for item in history:
            item["candidate_id"] = ids[item["candidate_id"]]
        candidates(case)
        originals[path] = raw
        replacements[path] = encoded(case)
        if history_path.exists():
            originals[history_path] = history_raw
            replacements[history_path] = b"".join(
                (json.dumps(item, ensure_ascii=False) + "\n").encode("utf-8") for item in history
            )
    backup = None
    if write and replacements:
        results = guarded(root / "results", root)
        results.mkdir(exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix="candidate-anonymization-", dir=results))
        for path, raw in originals.items():
            if read_bytes(path, root) != raw:
                raise ValueError("Data changed during anonymization; retry.")
            saved = backup / path.relative_to(root)
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(raw)
        (backup / "mapping.json").write_bytes(encoded(mapping))
        created, changed, removed = [], [], []
        try:
            for path, raw in outputs.items():
                path.parent.mkdir(exist_ok=True)
                if not path.exists():
                    with path.open("xb") as handle:
                        handle.write(raw)
                    created.append(path)
            for path, raw in replacements.items():
                if read_bytes(path, root) != originals[path]:
                    raise ValueError("Data changed concurrently; retry.")
                atomic(path, raw)
                changed.append(path)
            for path in obsolete - set(outputs):
                if read_bytes(path, root) != originals[path]:
                    raise ValueError("Candidate text changed concurrently; retry.")
                path.unlink()
                removed.append(path)
        except BaseException:
            for path in removed:
                path.write_bytes(originals[path])
            for path in reversed(changed):
                atomic(path, originals[path])
            for path in created:
                path.unlink(missing_ok=True)
            raise
    return {"candidates": len(mapping), "cases": len({row["case_id"] for row in mapping}),
            "written": write, "private_mapping": str(backup / "mapping.json") if backup else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    print(json.dumps(anonymize(args.data_dir, write=args.write), indent=2))


if __name__ == "__main__":
    main()
