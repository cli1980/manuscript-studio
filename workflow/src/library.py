"""Engine-owned per-work artifact library with an append-only publication log."""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

from .engine import WorkflowError
from .storage import digest, file_lock, now, plain, read_bytes, write_atomic, write_new

SOURCE_SUFFIX = re.compile(r"\.[a-z0-9]{1,10}")


class WorkLibrary:
    """works/<work_id>/: browsable latest files, objects/ for every version, publications.jsonl as history."""

    def __init__(self, root):
        self.root = plain(Path(root))
        if not (self.root / "publications.jsonl").is_file():
            raise ValueError(f"Not a work library: {root}")

    @classmethod
    def create(cls, root, *, source, source_name, info):
        root = plain(Path(root))
        root.mkdir()  # A new work always gets a new library; never initialize over files.
        (root / "objects").mkdir()
        write_new(root / "library.json", (json.dumps(info, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        (root / "publications.jsonl").touch()
        library = cls(root)
        data = read_bytes(plain(Path(source)))
        suffix = Path(source_name).suffix.lower()
        suffix = suffix if SOURCE_SUFFIX.fullmatch(suffix) else ".bin"
        library.publish_many([{"artifact": f"sources/{digest(data)}{suffix}", "data": data, "expected_head": None,
                               "source_name": source_name}], run_id=None, workflow=None, stage="create")
        return library

    def locked(self):
        return file_lock(self.root / ".library.lock", "Another process is publishing to this work library.")

    def info(self):
        return json.loads((self.root / "library.json").read_text(encoding="utf-8"))

    def path(self, artifact):
        if (not isinstance(artifact, str) or not artifact or "\\" in artifact or ":" in artifact
                or artifact.endswith("/")):
            raise ValueError("Library artifacts are relative forward-slash file paths.")
        part = Path(artifact)
        if (part.is_absolute() or ".." in part.parts or part.parts[0].startswith(".")
                or part.parts[0] in ("objects", "metadata-history", "publications.jsonl", "finalized", "library.json")):
            raise ValueError(f"Invalid library artifact: {artifact}")
        path = plain(self.root / part)
        if not path.is_relative_to(self.root):
            raise ValueError("Library artifact escapes the work library.")
        return path

    def publications(self, artifact=None):
        records = [json.loads(line) for line in
                   (self.root / "publications.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        return [r for r in records if artifact is None or r["artifact"] == artifact]

    def publication(self, publication_id):
        record = next((r for r in self.publications() if r["id"] == publication_id), None)
        if record is None:
            raise ValueError(f"Unknown publication: {publication_id}")
        return record

    def head(self, artifact):
        records = [r for r in self.publications(artifact) if r["status"] != "finalized"]
        return records[-1] if records else None

    def heads(self):
        result = {}
        for record in self.publications():
            if record["status"] != "finalized":
                result[record["artifact"]] = record
        return result

    def read(self, publication):
        sha = publication["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ValueError("Invalid artifact identity.")
        data = read_bytes(plain(self.root / "objects" / sha))
        if digest(data) != sha:
            raise ValueError("Library object checksum mismatch.")
        return data

    def source(self):
        record = next(r for r in self.publications() if r["artifact"].startswith("sources/"))
        return self.path(record["artifact"]), record

    def finalized(self, workflow=None):
        return [r for r in self.publications()
                if r["status"] == "finalized" and (workflow is None or r["workflow"] == workflow)]

    def _store(self, data):
        sha = digest(data)
        target = self.root / "objects" / sha
        try:
            with target.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if target.read_bytes() != data:
                raise ValueError("Corrupted library object.")
        return sha

    def _append(self, record):
        with (self.root / "publications.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _check_area(self, artifact):
        for record in self.finalized():
            for area in record["areas"]:
                if artifact == area or (area.endswith("/") and artifact.startswith(area)):
                    raise WorkflowError("workflow_read_only",
                                        f"{record['workflow']} is finalized on this work; {artifact} is read-only.")

    def _detect(self, artifacts=None):
        found = []
        for artifact, head in self.heads().items():
            if artifacts is not None and artifact not in artifacts:
                continue
            path = self.path(artifact)
            known = {r["sha256"] for r in self.publications(artifact)}
            if not path.is_file():
                write_atomic(path, self.read(head))  # A deleted browsable copy is restored, not an edit.
                continue
            data = read_bytes(path)
            sha = digest(data)
            if sha == head["sha256"]:
                continue
            if sha in known:
                write_atomic(path, self.read(head))  # An interrupted materialization.
                continue
            self._store(data)
            record = {"id": "pub-" + uuid.uuid4().hex[:12], "created_at": now(), "run_id": None, "workflow": None,
                      "stage": "user_edit", "artifact": artifact, "sha256": sha, "bytes": len(data),
                      "version": head["version"] + 1, "basis": None, "receipts": [], "supersedes": head["id"],
                      "status": "user_edit", "review_status": "unreviewed"}
            self._append(record)
            found.append(record)
        return found

    def detect_edits(self):
        """Record hand edits to browsable files as unreviewed user_edit publications; never overwrite them."""
        with self.locked():
            return self._detect()

    def publish_many(self, entries, *, run_id, workflow, stage=None, receipts=(), finalize=None):
        """All-or-nothing compare-and-swap publication of several artifacts."""
        with self.locked():
            self._detect({entry["artifact"] for entry in entries})
            for entry in entries:
                self.path(entry["artifact"])
                self._check_area(entry["artifact"])
                head = self.head(entry["artifact"])
                if (head["id"] if head else None) != entry["expected_head"]:
                    raise WorkflowError("library_conflict",
                                        f"{entry['artifact']} changed in the work library since this run read it.")
            if finalize is not None and self.finalized(workflow):
                raise WorkflowError("workflow_read_only", f"{workflow} is already finalized on this work.")
            records = []
            for entry in entries:
                head = self.head(entry["artifact"])
                sha = self._store(entry["data"])
                record = {"id": "pub-" + uuid.uuid4().hex[:12], "created_at": now(), "run_id": run_id,
                          "workflow": workflow, "stage": entry.get("stage", stage), "artifact": entry["artifact"],
                          "sha256": sha, "bytes": len(entry["data"]), "version": head["version"] + 1 if head else 1,
                          "basis": entry.get("basis"), "receipts": list(receipts),
                          "supersedes": head["id"] if head else None, "status": "published",
                          "review_status": entry.get("review_status", "accepted")}
                for key in ("contract", "source_name"):
                    if key in entry:
                        record[key] = entry[key]
                self._append(record)
                if entry["artifact"] == "work.json" and head:
                    revision = json.loads(self.read(head)).get("record_revision")
                    write_new(self.root / "metadata-history" / f"{revision}-{head['sha256'][:16]}.json", self.read(head))
                write_atomic(self.path(entry["artifact"]), entry["data"])
                records.append(record)
            if finalize is not None:
                self._append({"id": "pub-" + uuid.uuid4().hex[:12], "created_at": now(), "run_id": run_id,
                              "workflow": workflow, "stage": stage, "artifact": f"finalized/{workflow}",
                              "areas": list(finalize), "status": "finalized"})
            return records
