"""Validate the shared preparation contract and the files it binds."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"
ACTIVE = {"in_progress", "awaiting_approval", "completed"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def plain_path(path):
    path = Path(os.path.abspath(path))
    for entry in (path, *path.parents):
        try:
            info = entry.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode) and not (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ), "Prepared files and source checks must not follow links or reparse points.")
    return path


def local_file(root, relative):
    require(isinstance(relative, str) and "\\" not in relative and ":" not in relative,
            "Package paths must use relative forward-slash notation.")
    part = Path(relative)
    require(not part.is_absolute() and ".." not in part.parts, "Package paths may not escape their root.")
    path = plain_path(root / part)
    require(path.is_relative_to(root) and path.is_file(), f"Missing package file: {relative}")
    require(path.stat().st_nlink == 1, "Prepared files must not be hard-linked working copies.")
    return path


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON field: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def validators():
    schemas = [load_json(SCHEMAS / name) for name in ("work.schema.json", "revision.schema.json")]
    registry = Registry()
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return [Draft202012Validator(schema, registry=registry, format_checker=FormatChecker()) for schema in schemas]


def schema_check(validator, value, label):
    error = next(iter(validator.iter_errors(value)), None)
    if error:
        location = ".".join(map(str, error.absolute_path)) or "<root>"
        raise ValueError(f"{label}.{location}: {error.message}")


def validate(work_path, *, check_sources=False):
    work_path = plain_path(work_path)
    root = work_path.parent
    work_validator, revision_validator = validators()
    work = load_json(work_path)
    schema_check(work_validator, work, "work")
    preparation = work["preparation"]
    current_revision = preparation["current_revision"]
    loaded = {}

    def revision(revision_id):
        if revision_id in loaded:
            return loaded[revision_id]
        manifest_path = local_file(root, f"revisions/{revision_id}/manifest.json")
        manifest = load_json(manifest_path)
        schema_check(revision_validator, manifest, "manifest")
        require(manifest["work_id"] == work["work_id"] and manifest["revision"] == revision_id,
                "Work and revision identities do not match.")
        sources = {source["source_id"] for source in manifest["sources"]}
        require(len(sources) == len(manifest["sources"]), "Source IDs must be unique.")
        chapters = manifest["chapters"]
        ids = [chapter["chapter_id"] for chapter in chapters]
        require(len(ids) == len(set(ids)), "Chapter IDs must be unique.")
        require(manifest["scope"]["chapter_ids"] == ids, "Scope must enumerate the prepared chapters in source order.")
        require([chapter["order"] for chapter in chapters] == list(range(1, len(chapters) + 1)),
                "Chapter orders must be consecutive and source-ordered.")
        directory = manifest_path.parent
        expected_files = set()
        for chapter in chapters:
            require(chapter["file"] == f"chapters/{chapter['order']:04d}.md",
                    "Chapter filenames must match their zero-padded order.")
            path = local_file(directory, chapter["file"])
            expected_files.add(path.name)
            raw = path.read_bytes()
            require(not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw and raw.endswith(b"\n"),
                    "Chapter Markdown must be UTF-8 without BOM, use LF, and end with LF.")
            require(raw.decode("utf-8").strip(), "Chapter Markdown must not be empty.")
            require(digest(path) == chapter["sha256"], "A prepared chapter hash does not match.")
            require(all(span["source_id"] in sources for span in chapter["source_spans"]),
                    "Chapter source spans refer to an unknown source.")
        chapter_dir = plain_path(directory / "chapters")
        require({p.name for p in chapter_dir.iterdir()} == expected_files,
                "The chapter directory contains missing or unlisted files.")
        assets = manifest["assets"]
        require(len({a["file"] for a in assets}) == len(assets), "Asset paths must be unique.")
        for asset in assets:
            path = local_file(directory, asset["file"])
            require(path.suffix.lower() not in {".md", ".txt"}, "Prepared text belongs in chapter Markdown, not assets.")
            require(asset["source_id"] in sources and digest(path) == asset["sha256"],
                    "Asset source identity or hash does not match.")
        if manifest["status"] == "verified":
            verification = manifest["verification"]
            require(verification["coverage_complete"] and verification["performed_by"] and verification["verified_at"],
                    "Verified extraction requires a dated source-comparison and coverage record.")
            require(all(chapter["status"] == "verified" for chapter in chapters),
                    "Every chapter must be verified before publishing a verified manifest.")
            require(not any(issue["severity"] == "blocking" for issue in verification["issues"]),
                    "A verified manifest cannot have blocking extraction issues.")
        loaded[revision_id] = manifest
        return manifest

    manifest = revision(current_revision) if current_revision else None
    if preparation["status"] == "not_started":
        require(current_revision is None, "Not-started preparation cannot claim a current revision.")
    if preparation["status"] == "ready":
        require(manifest is not None and manifest["status"] == "verified",
                "Ready preparation requires a verified revision manifest.")
        require(work["discovery"]["selection_status"] == "confirmed" and not preparation["blockers"],
                "Ready preparation requires confirmed source selection and no blockers.")
        require(work["metadata"]["source_language"] is not None, "Ready preparation requires the source language.")
    if preparation["status"] == "blocked":
        require(preparation["blockers"], "Blocked preparation must explain its blockers.")
    for name, state in work["workflows"].items():
        if state["status"] == "not_started":
            require(all(state[key] is None for key in ("basis_revision", "scope", "operation", "state_locator", "updated_at")),
                    f"{name}: not-started state must not claim a workflow basis or progress.")
            continue
        require(state["operation"] and state["updated_at"], f"{name}: record the operation and update time.")
        basis = state["basis_revision"]
        if state["status"] in ACTIVE:
            require(basis == current_revision and basis is not None and preparation["status"] == "ready",
                    f"{name}: active or completed work requires the current ready preparation revision.")
            require(state["scope"] and state["state_locator"], f"{name}: scope and authoritative state locator are required.")
        if basis is not None:
            basis_manifest = revision(basis)
            require(state["scope"] is not None, f"{name}: a source-bound workflow requires a scope.")
            available = {chapter["chapter_id"] for chapter in basis_manifest["chapters"]}
            scope = state["scope"]
            require(set(scope["chapter_ids"]) <= available, f"{name}: scope contains unknown chapters.")
            if scope["kind"] == "whole_work":
                require(basis_manifest["scope"]["kind"] == "whole_work" and set(scope["chapter_ids"]) == available,
                        f"{name}: whole-work status cannot be based on a partial preparation.")
        else:
            require(state["status"] == "blocked" and state["scope"] is None,
                    f"{name}: only a blocked operation may have no source revision.")
    discovery = work["discovery"]
    if check_sources:
        require(manifest is not None, "There is no prepared source revision to check.")
        require(discovery["location_kind"] in {"file", "directory"},
                "Remote sources require version verification through their provider.")
    if manifest is not None and discovery["location_kind"] in {"file", "directory"}:
        base = plain_path(discovery["location"])
        require(Path(discovery["location"]).is_absolute(), "Local discovery locations must be absolute.")
        require(not base.is_relative_to(root) and not root.is_relative_to(base),
                "The preparation package and original source location must be separate.")
        for source in manifest["sources"]:
            require(Path(source["locator"]).is_absolute(), "Local source locators must be absolute.")
            path = plain_path(source["locator"])
            if discovery["location_kind"] == "file":
                require(path == base, "Source is outside the designated file.")
            else:
                require(path.is_relative_to(base), "Source is outside the designated directory.")
                require(discovery["recursive"] or path.parent == base, "Source requires unapproved recursive discovery.")
            if check_sources:
                require(source["identity"]["kind"] == "sha256", "Local source verification requires a SHA-256 identity.")
                require(path.is_file() and digest(path) == source["identity"]["value"],
                        "Original source changed; mark preparation and dependent workflows stale.")
    return {"work_id": work["work_id"], "preparation_status": preparation["status"],
            "current_revision": current_revision, "chapters": len(manifest["chapters"]) if manifest else 0,
            "local_sources_checked": check_sources}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_json", type=Path)
    parser.add_argument("--check-sources", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.work_json, check_sources=args.check_sources), indent=2))
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"prepare-manuscript validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
