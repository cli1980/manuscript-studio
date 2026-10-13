#!/usr/bin/env python3
"""Validate terminal on-demand layout and newly reproduced agent ZIPs."""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath


ZIP_NAME = re.compile(r"agent-package-([a-z0-9]+(?:-[a-z0-9]+)*)\.zip\Z")
REQUIRED_FILES = {
    "package-manifest.md",
    "query-letter.md",
    "claim-audit.md",
    "submission-instructions.md",
}


class ValidationError(ValueError):
    pass


def validate_root(root: Path) -> list[str]:
    if not root.is_dir():
        raise ValidationError(f"On-demand root is not a directory: {root}")
    errors: list[str] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if child.is_dir():
            errors.append(f"staging or loose directory is forbidden: {child.name}")
        elif not ZIP_NAME.fullmatch(child.name):
            errors.append(f"loose on-demand file is forbidden: {child.name}")
    if errors:
        raise ValidationError("; ".join(errors))
    return [child.name for child in sorted(root.iterdir())]


def _normalized_entries(archive: zipfile.ZipFile) -> list[str]:
    entries: list[str] = []
    seen: set[str] = set()
    for info in archive.infolist():
        name = info.filename.replace("\\", "/")
        if info.is_dir() or name.endswith("/"):
            continue
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValidationError(f"unsafe archive path: {name}")
        normalized = str(path)
        if normalized in seen:
            raise ValidationError(f"duplicate archive path: {normalized}")
        seen.add(normalized)
        entries.append(normalized)
    return entries


def validate_new_zip(zip_path: Path) -> dict[str, object]:
    match = ZIP_NAME.fullmatch(zip_path.name)
    if not match:
        raise ValidationError(
            "new ZIP must be named agent-package-<agent-slug>.zip"
        )
    slug = match.group(1)
    if not zip_path.is_file():
        raise ValidationError(f"new ZIP does not exist: {zip_path}")

    with zipfile.ZipFile(zip_path, "r") as archive:
        entries = _normalized_entries(archive)
        prefix = f"agent-package/{slug}/"
        unexpected = [
            entry
            for entry in entries
            if not entry.startswith(prefix)
            or "/" in entry[len(prefix):]
        ]
        if unexpected:
            raise ValidationError(
                "archive entries must be direct files beneath "
                f"{prefix}: {', '.join(unexpected)}"
            )
        leaves = {entry[len(prefix):] for entry in entries}
        missing = sorted(REQUIRED_FILES - leaves)
        if missing:
            raise ValidationError(
                "incomplete package; missing: " + ", ".join(missing)
            )

        manifest_path = prefix + "package-manifest.md"
        manifest = archive.read(manifest_path).decode("utf-8-sig")
        if "Build mode: fresh-reproduction" not in manifest:
            raise ValidationError(
                "manifest lacks Build mode: fresh-reproduction"
            )
        if "Prior on-demand source: none" not in manifest:
            raise ValidationError(
                "manifest lacks Prior on-demand source: none"
            )

        unlisted = sorted(name for name in leaves if name not in manifest)
        if unlisted:
            raise ValidationError(
                "manifest does not list every archive file: "
                + ", ".join(unlisted)
            )

        synopsis_requested = bool(
            re.search(r"(?im)^-\s*Synopsis requested:\s*yes\s*$", manifest)
        )
        if synopsis_requested and "synopsis.md" not in leaves:
            raise ValidationError(
                "manifest requests a synopsis but synopsis.md is absent"
            )

        prepared_samples = re.findall(
            r"(?im)^-\s*Package filename:\s*([^\s]+)\s*$", manifest
        )
        absent_samples = sorted(
            name for name in prepared_samples if name not in leaves
        )
        if absent_samples:
            raise ValidationError(
                "manifest names missing sample files: "
                + ", ".join(absent_samples)
            )

        for entry in entries:
            if PurePosixPath(entry).suffix.lower() in {".md", ".txt", ".json"}:
                archive.read(entry).decode("utf-8-sig")

    return {
        "zip": str(zip_path),
        "agent_slug": slug,
        "files": len(entries),
        "required_files": sorted(REQUIRED_FILES),
        "validation": "passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--root", type=Path)
    group.add_argument("--new-zip", type=Path)
    args = parser.parse_args()
    try:
        if args.root is not None:
            files = validate_root(args.root)
            print(
                f"on-demand root passed: {len(files)} terminal ZIP(s); "
                "existing ZIP contents were not opened"
            )
        else:
            report = validate_new_zip(args.new_zip)
            print(
                f"new on-demand ZIP passed: {report['agent_slug']} "
                f"({report['files']} files)"
            )
        return 0
    except (OSError, UnicodeError, zipfile.BadZipFile, ValidationError) as exc:
        sys.stderr.write("on-demand validation failed: " + str(exc) + "\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
