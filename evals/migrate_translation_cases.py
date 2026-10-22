"""Migrate legacy translation cases and judgment bindings; text files are untouched."""

import argparse
import json
import os
import tempfile
from pathlib import Path

if __package__:
    from .translation_cases import migrate_case, discover_cases
    from .run_judge import ROOT, guarded, read_bytes, object_json
else:
    from translation_cases import migrate_case, discover_cases
    from run_judge import ROOT, guarded, read_bytes, object_json


def migrate(root, *, write=False):
    root = Path(root).resolve()
    changes = []
    for path in discover_cases(root / "cases/literary-translation"):
        raw = read_bytes(path, root)
        case = object_json(raw)
        if case.get("schema_version", 1) == 2:
            continue
        judgments_path = guarded(path.parent / "judgments.jsonl", root)
        raw_judgments = read_bytes(judgments_path, root) if judgments_path.exists() else b""
        judgments = [object_json(line) for line in raw_judgments.splitlines() if line.strip()]
        updated, records = migrate_case(case, judgments)
        changes.append((path, raw, (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode("utf-8")))
        if records:
            changes.append((judgments_path, raw_judgments,
                            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records).encode("utf-8")))
    backup = None
    if write and changes:
        results = guarded(root / "results", root)
        results.mkdir(exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix="case-migration-", dir=results))
        # Validate every original before writing and keep rollback bytes.
        for path, original, _ in changes:
            if path.read_bytes() != original:
                raise ValueError("Case changed during migration; retry from the current files.")
            saved = backup / path.relative_to(root)
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(original)
        published = []
        try:
            for path, original, content in changes:
                if path.read_bytes() != original:
                    raise ValueError("Case changed during migration; retry from the current files.")
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                    temporary = Path(handle.name)
                    handle.write(content)
                try:
                    os.replace(temporary, path)
                finally:
                    temporary.unlink(missing_ok=True)
                published.append((path, original))
        except BaseException:
            for path, original in reversed(published):
                path.write_bytes(original)
            raise
    return {"files": len(changes), "written": write, "backup": str(backup) if backup else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true", help="Apply migration; otherwise preview the count.")
    args = parser.parse_args()
    print(json.dumps(migrate(args.data_dir, write=args.write), indent=2))


if __name__ == "__main__":
    main()
