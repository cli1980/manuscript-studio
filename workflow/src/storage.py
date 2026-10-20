"""SQLite lifecycle records and immutable, content-addressed file snapshots."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sqlite3
import stat
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plain(path: Path) -> Path:
    """Reject links before resolving: resolving first would conceal an escape."""
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError(f"Links/reparse points are not permitted: {part}")
    return path


def local_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("Artifact paths must be relative forward-slash paths.")
    part = Path(relative)
    if part.is_absolute() or ".." in part.parts:
        raise ValueError("Artifact path escapes the workspace.")
    path = plain(root / part)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Missing workspace file: {relative}")
    if path.stat().st_nlink != 1:
        raise ValueError("Hard-linked artifacts are not permitted.")
    return path


def read_bytes(path: Path) -> bytes:
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError(f"File exceeds the 64 MiB prototype limit: {path}")
    return path.read_bytes()


class Store:
    def __init__(self, root: Path):
        self.root = plain(root)
        if not (self.root / "state.sqlite3").is_file():
            raise ValueError(f"Not a workflow run: {root}")
        self.db = sqlite3.connect(self.root / "state.sqlite3", timeout=5)
        self.db.execute("PRAGMA foreign_keys=ON")

    @classmethod
    def create(cls, root: Path, state: dict):
        root = plain(root)
        root.mkdir()  # Refuse existing directories; never initialize over user files.
        for name in ("objects", "input", "workspace", "skills"):
            (root / name).mkdir()
        db = sqlite3.connect(root / "state.sqlite3")
        with db:
            db.executescript("""
                CREATE TABLE run (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL,
                                  state TEXT NOT NULL);
                CREATE TABLE events (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
                                     kind TEXT NOT NULL, payload TEXT NOT NULL);
            """)
            db.execute("INSERT INTO run VALUES (1, 0, ?)", (json.dumps(state),))
        db.close()
        return cls(root)

    def close(self):
        self.db.close()

    @contextlib.contextmanager
    def locked(self):
        """OS lock is released on process exit, including a crash."""
        with (self.root / ".run.lock").open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ValueError("Another process is operating on this run.") from exc
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle, fcntl.LOCK_UN)

    def load(self):
        revision, value = self.db.execute("SELECT revision, state FROM run WHERE id=1").fetchone()
        return revision, json.loads(value)

    def save(self, revision, state, kind, payload=None):
        with self.db:
            changed = self.db.execute(
                "UPDATE run SET revision=revision+1, state=? WHERE id=1 AND revision=?",
                (json.dumps(state, ensure_ascii=False), revision),
            ).rowcount
            if changed != 1:
                raise ValueError("Run revision changed; reload before continuing.")
            self.db.execute("INSERT INTO events(created_at,kind,payload) VALUES (?,?,?)",
                            (now(), kind, json.dumps(payload or {}, ensure_ascii=False)))
        return revision + 1

    def event(self, kind, payload):
        with self.db:
            self.db.execute("INSERT INTO events(created_at,kind,payload) VALUES (?,?,?)",
                            (now(), kind, json.dumps(payload, ensure_ascii=False)))

    def events(self, after=0):
        return [dict(id=i, created_at=at, kind=kind, payload=json.loads(payload))
                for i, at, kind, payload in self.db.execute(
                    "SELECT id,created_at,kind,payload FROM events WHERE id>? ORDER BY id", (after,))]

    def snapshot(self, path: Path, role: str):
        data = read_bytes(plain(path))
        sha = digest(data)
        target = self.root / "objects" / sha
        try:
            with target.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if target.read_bytes() != data:
                raise ValueError("Corrupted artifact object.")
        return {"sha256": sha, "role": role, "name": path.name, "bytes": len(data)}

    def content(self, artifact):
        sha = artifact["sha256"]
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError("Invalid artifact identity.")
        data = read_bytes(plain(self.root / "objects" / sha))
        if digest(data) != sha:
            raise ValueError("Artifact checksum mismatch.")
        return data
