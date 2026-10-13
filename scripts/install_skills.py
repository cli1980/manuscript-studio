from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import sys
import tempfile
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "plugins/manuscript-studio/skills"
STATE_FILE = ".manuscript-studio-install.json"
LOCK_FILE = ".manuscript-studio-install.lock"
BACKUP_DIR = ".manuscript-studio-backups"
DEPENDENCIES = {
    name: ("review-approval-sheet",)
    for name in (
        "literary-editing", "literary-translation", "literary-agent-querying",
        "format-manuscript",
    )
}


def assert_plain_path(path: Path) -> None:
    for entry in (path, *path.parents):
        try:
            info = entry.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise ValueError(f"Refusing link or reparse point: {entry}")


def ignored(name: str) -> bool:
    return name in {"__pycache__", ".pytest_cache", ".git"} or name.endswith((".pyc", ".pyo"))


def inventory(root: Path) -> dict[str, str]:
    assert_plain_path(root)
    if not root.is_dir():
        raise ValueError(f"Not a skill directory: {root}")
    files = {}

    def visit(directory: Path) -> None:
        for path in sorted(directory.iterdir()):
            if ignored(path.name):
                continue
            assert_plain_path(path)
            if path == root / STATE_FILE:
                if not path.is_file():
                    raise ValueError(f"Invalid installation state: {path}")
                continue
            relative = path.relative_to(root).as_posix()
            if path.is_dir():
                files[relative + "/"] = ""
                visit(path)
            elif path.is_file():
                files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                raise ValueError(f"Not a regular file or directory: {path}")

    visit(root)
    return files


def available_skills(source_root: Path) -> dict[str, Path]:
    assert_plain_path(source_root)
    if not source_root.is_dir():
        raise ValueError(f"Canonical skills directory is missing: {source_root}")
    skills = {
        path.name: path for path in sorted(source_root.iterdir())
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", path.name)
        and (path / "SKILL.md").is_file()
    }
    if not skills:
        raise ValueError(f"No skills found in {source_root}")
    return skills


def select_skills(available: dict[str, Path], names: list[str]) -> list[str]:
    selected = set()

    def include(name: str) -> None:
        if name not in available:
            raise ValueError(f"Unknown or missing skill: {name}. Use --list to see available skills.")
        if name not in selected:
            selected.add(name)
            for dependency in DEPENDENCIES.get(name, ()):
                include(dependency)

    for name in names or available:
        include(name)
    return sorted(selected)


def installed_inventory(target: Path) -> dict[str, str] | None:
    assert_plain_path(target)
    if not target.exists():
        return None
    state_path = target / STATE_FILE
    assert_plain_path(state_path)
    if not target.is_dir() or not state_path.is_file():
        raise ValueError(f"Refusing unmanaged installation: {target}. Back it up and move it aside first.")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError(f"Invalid installation state: {state_path}") from exc
    if (
        not isinstance(state, dict)
        or state.get("schema_version") != 1
        or state.get("project") != "manuscript-studio"
        or state.get("skill") != target.name
        or not isinstance(state.get("files"), dict)
        or "SKILL.md" not in state["files"]
    ):
        raise ValueError(f"Invalid installation state: {state_path}")
    current = inventory(target)
    if current != state["files"]:
        changed = sorted(
            name for name in current.keys() | state["files"].keys()
            if current.get(name) != state["files"].get(name)
        )
        raise ValueError(
            f"Refusing locally modified installation: {target} ({', '.join(changed[:8])}). "
            "Preserve your changes and move the installation aside before reinstalling."
        )
    return current


def make_plan(
    available: dict[str, Path], names: list[str], destination: Path, update: bool,
) -> list[tuple[str, dict[str, str], dict[str, str] | None]]:
    plan = []
    for name in names:
        source = available[name]
        assert_plain_path(source / STATE_FILE)
        if (source / STATE_FILE).exists():
            raise ValueError(f"Canonical skill contains reserved installation state: {source / STATE_FILE}")
        files = inventory(source)
        current = installed_inventory(destination / name)
        if current is not None and current != files and not update:
            raise ValueError(f"{name} is already installed. Preview and authorize its update with --update.")
        plan.append((name, files, current))
    return plan


def publish(
    source: Path, target: Path, files: dict[str, str], current: dict[str, str] | None,
) -> Path | None:
    with tempfile.TemporaryDirectory(prefix=".manuscript-studio-stage-", dir=target.parent.parent) as temporary:
        payload = Path(temporary) / "payload"
        shutil.copytree(source, payload, ignore=lambda _, names: [name for name in names if ignored(name)])
        if inventory(payload) != files:
            raise ValueError(f"Source changed during installation: {source}. Retry after edits finish.")
        state = {
            "schema_version": 1,
            "project": "manuscript-studio",
            "skill": target.name,
            "files": files,
        }
        (payload / STATE_FILE).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        if installed_inventory(target) != current:
            raise ValueError(f"Installation changed during staging: {target}. Retry after edits finish.")
        backup = None
        if current is not None:
            backup_root = target.parent.parent / BACKUP_DIR
            assert_plain_path(backup_root)
            backup_root.mkdir(exist_ok=True)
            backup = backup_root / f"{target.name}-{uuid.uuid4().hex}"
            target.rename(backup)
        try:
            payload.rename(target)
        except OSError:
            if backup is not None:
                backup.rename(target)
            raise
    return backup


def install_skills(
    destination: Path,
    names=(),
    *,
    source_root: Path = SKILLS_ROOT,
    update: bool = False,
    dry_run: bool = False,
) -> list[str]:
    destination = destination.expanduser().absolute()
    assert_plain_path(destination)
    source_root = source_root.absolute()
    available = available_skills(source_root)
    selected = select_skills(available, list(names))
    destination = destination.resolve()
    for protected in (source_root.resolve(), REPO_ROOT):
        if destination.is_relative_to(protected) or protected.is_relative_to(destination):
            raise ValueError(f"Installation destination overlaps the source repository: {destination}")
    plan = make_plan(available, selected, destination, update)
    if dry_run:
        return [
            f"{'Unchanged' if current == files else 'Would install' if current is None else 'Would update'}: "
            f"{name} -> {destination / name}"
            for name, files, current in plan
        ]
    destination.mkdir(parents=True, exist_ok=True)
    lock = destination / LOCK_FILE
    try:
        with lock.open("x", encoding="utf-8") as handle:
            handle.write("Manuscript Studio installation in progress.\n")
    except FileExistsError as exc:
        raise ValueError(f"Installation lock exists: {lock}. Check for another installer before removing it.") from exc
    messages = []
    try:
        plan = make_plan(available, selected, destination, update)
        for name, files, current in plan:
            if current == files:
                messages.append(f"Unchanged: {name}")
                continue
            backup = publish(available[name], destination / name, files, current)
            messages.append(f"{'Installed' if current is None else 'Updated'}: {name} -> {destination / name}")
            if backup is not None:
                messages.append(f"Backup retained: {backup}")
    finally:
        lock.unlink()
    return messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install canonical Manuscript Studio skills for local Codex use.")
    parser.add_argument("skills", nargs="*", help="Skill names; default: all. Shared review dependencies are included.")
    parser.add_argument("--dest", type=Path, default=Path.home() / ".agents/skills", help="Destination skill directory (default: ~/.agents/skills).")
    parser.add_argument("--list", action="store_true", help="List available skills without installing.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and preview without writing files.")
    parser.add_argument("--update", action="store_true", help="Authorize updates of clean, installer-managed skills; keep backups.")
    args = parser.parse_args(argv)
    try:
        if args.list:
            for name in available_skills(SKILLS_ROOT):
                print(name)
        else:
            for message in install_skills(args.dest, args.skills, update=args.update, dry_run=args.dry_run):
                print(message)
        return 0
    except (OSError, ValueError) as exc:
        print(f"install-skills: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
