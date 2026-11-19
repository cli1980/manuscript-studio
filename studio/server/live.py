"""Change feed: one background watcher fingerprints every run and work, so browsers refetch only what changed."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

# Agent streaming events that the timeline hides by default; turn boundaries stay visible.
QUIET_PREFIXES = ("item/", "thread/", "account/", "mcpServer/", "remoteControl/", "codex/", "test.",
                  "runtime.tool_", "runtime.usage")


def visible(kind):
    return not kind.startswith(QUIET_PREFIXES) or kind in ("turn/started", "turn/completed")


class Watcher:
    """Scans the server root once per interval. A run's fingerprint is its state revision, its last visible event,
    and its worker status; a work's is its publication log. The version increases whenever any fingerprint changes.
    Reads never write, so watching cannot trigger itself."""

    def __init__(self, server_root, workers, interval=1.0):
        self.root = Path(server_root)
        self.workers = workers
        self.interval = interval
        self.lock = threading.Lock()
        self.scanning = threading.Lock()  # The connections are used by one scan at a time.
        self.version = 0  # 0 until the first scan, which always publishes.
        self.snapshot = None
        self.runs = {}  # run_id -> read-only connection and event cursors
        self.thread = None
        self.stopped = threading.Event()

    def start(self):
        """Start lazily, on the first subscriber."""
        with self.lock:
            if self.thread is None and not self.stopped.is_set():
                self.thread = threading.Thread(target=self._loop, name="studio-live", daemon=True)
                self.thread.start()

    def stop(self):
        self.stopped.set()
        if self.thread:
            self.thread.join(5)
        with self.scanning:
            for entry in self.runs.values():
                entry["db"].close()
            self.runs.clear()

    def current(self):
        with self.lock:
            return self.version, self.snapshot

    def _loop(self):
        while not self.stopped.is_set():
            self.scan()
            self.stopped.wait(self.interval)

    def _run(self, run_id, path):
        entry = self.runs.get(run_id)
        if entry is None:
            db = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=1, check_same_thread=False)
            entry = self.runs[run_id] = {"db": db, "seen": 0, "visible": 0}
        revision = entry["db"].execute("SELECT revision FROM run WHERE id=1").fetchone()[0]
        for event_id, kind in entry["db"].execute("SELECT id, kind FROM events WHERE id>? ORDER BY id", (entry["seen"],)):
            entry["seen"] = event_id
            if visible(kind):
                entry["visible"] = event_id
        return {"revision": revision, "event": entry["visible"], "worker": self.workers.status(run_id)}

    def scan(self):
        with self.scanning:
            return self._scan()

    def _scan(self):
        runs = {}
        previous = (self.snapshot or {}).get("runs", {})
        for path in sorted(path for area in ("runs", "preparations")
                           for path in (self.root / area).glob("*/state.sqlite3")):
            run_id = path.parent.name
            try:
                runs[run_id] = self._run(run_id, path)
            except sqlite3.Error:  # Busy or mid-creation: keep the last fingerprint and try again next scan.
                if run_id in previous:
                    runs[run_id] = previous[run_id]
        works = {}
        for path in sorted((self.root / "works").glob("*/publications.jsonl")):
            info = path.stat()
            works[path.parent.name] = f"{info.st_size}:{info.st_mtime_ns}"
        snapshot = {"runs": runs, "works": works}
        with self.lock:
            if snapshot != self.snapshot:
                self.snapshot = snapshot
                self.version += 1
        return self.version
