"""Immutable Work inputs, independent of the runs that produce or consume them."""

from __future__ import annotations

import copy
import json
import uuid
from pathlib import PurePosixPath

from .engine import WorkflowError
from .analysis import CONTRACT as ANALYSIS_CONTRACT
from .storage import digest, json_bytes, now, read_bytes, write_new

CONTRACT = "prepared-work-version/1"


def version_publications(library):
    return [record for record in library.publications() if record.get("contract") == CONTRACT]


def versions(library):
    return [{**json.loads(library.read(record)), "publication_id": record["id"]}
            for record in version_publications(library)]


def _relative(path):
    if not isinstance(path, str) or not path or "\\" in path or ":" in path:
        raise ValueError("Work version paths must be relative forward-slash paths.")
    parts = PurePosixPath(path)
    if parts.is_absolute() or ".." in parts.parts or parts.as_posix() != path:
        raise ValueError("Work version path escapes its package.")
    return path


def load_version(library, version_id, *, ready=True):
    matches = [record for record in version_publications(library)
               if json.loads(library.read(record)).get("version_id") == version_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown or ambiguous Work version: {version_id}")
    publication = matches[0]
    version = json.loads(library.read(publication))
    if version.get("contract") != CONTRACT or version.get("work_id") != library.info()["work_id"]:
        raise ValueError("Work version identity differs from its library.")
    if ready and version.get("status") != "ready":
        raise WorkflowError("work_not_prepared", "Prepare and validate this Work version before starting a workflow.")
    if version.get("status") == "ready" and (not version.get("prepared") or not version.get("chapters")
            or not version.get("metadata_approval") or (version.get("analysis") or {}).get("contract") != ANALYSIS_CONTRACT):
        raise ValueError("Work version lacks a complete, compatible preparation/analysis contract.")
    source = library.publication(version["source"]["publication_id"])
    if source["artifact"] != version["source"]["artifact"] or source["sha256"] != version["source"]["sha256"]:
        raise ValueError("Work version source binding differs from its publication.")
    if digest(read_bytes(library.path(source["artifact"]))) != source["sha256"]:
        raise ValueError("The Work version's read-only source changed.")
    library.read(source)
    prefix = f"work-versions/{version_id}/files/"
    for path, artifact in version.get("files", {}).items():
        _relative(path)
        if artifact["artifact"] != prefix + path:
            raise ValueError("Work version file belongs to another package.")
        record = library.publication(artifact["publication_id"])
        if record["artifact"] != artifact["artifact"] or record["sha256"] != artifact["sha256"]:
            raise ValueError("Work version file binding differs from its publication.")
        library.read(record)
    for sha, artifact in version.get("metadata_objects", {}).items():
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha) \
                or artifact["artifact"] != f"work-versions/{version_id}/objects/{sha}":
            raise ValueError("Invalid Work metadata object identity.")
        record = library.publication(artifact["publication_id"])
        if record["artifact"] != artifact["artifact"] or record["sha256"] != sha or artifact["sha256"] != sha:
            raise ValueError("Work metadata object binding differs from its publication.")
        library.read(record)
    return {**version, "publication_id": publication["id"]}


def publish_prepared(engine, state):
    """A final descriptor is the commit marker; incomplete file batches are not inputs."""
    library = engine.library
    if library is None:
        raise ValueError("Work preparation requires a Work library.")
    engine.verify(state)
    version_id = state.setdefault("prepared_version_id", "wv-" + uuid.uuid4().hex)
    existing = [v for v in versions(library) if v["version_id"] == version_id]
    if existing:
        return load_version(library, version_id)
    source = state.get("preparation_source")
    if source is None:
        raise ValueError("Work preparation has no designated source publication.")
    paths = set(state["prepared"]["files"])
    paths.add(state["prepared"]["work_record"])
    paths.update(a["path"] for a in [state["analysis"]["manifest"], *state["analysis"]["artifacts"].values()])
    prefix = f"work-versions/{version_id}"
    entries = [{"artifact": f"{prefix}/files/{_relative(path)}", "data": read_bytes(engine.file(path)),
                "expected_head": None, "review_status": "provisional"} for path in sorted(paths)]
    metadata_hashes = {version["sha256"] for version in state["metadata_versions"]}
    metadata_hashes.add(state["metadata_approval"]["sha256"])
    metadata_hashes.update(receipt["gate"]["binding"]["sha256"] for receipt in state["receipts"]
                           if receipt["gate"]["kind"] == "metadata_review")
    entries.extend({"artifact": f"{prefix}/objects/{sha}", "data": engine.store.content({"sha256": sha}),
                    "expected_head": None, "review_status": "provisional"} for sha in sorted(metadata_hashes))
    for entry in entries:
        head = library.head(entry["artifact"])
        if head:
            if head["sha256"] != digest(entry["data"]):
                raise ValueError("An interrupted Work version differs from its frozen input.")
            entry["expected_head"] = head["id"]
    records = library.publish_many(entries, run_id=state["id"], workflow=None, stage="work-preparation")
    files = {path: {"artifact": record["artifact"], "publication_id": record["id"], "sha256": record["sha256"]}
             for path, record in zip(sorted(paths), records)}
    metadata_objects = {record["sha256"]: {"artifact": record["artifact"], "publication_id": record["id"],
                                         "sha256": record["sha256"]} for record in records[len(paths):]}
    version = {
        "contract": CONTRACT, "version_id": version_id, "work_id": state["work_id"], "status": "ready",
        "kind": state.get("preparation_kind", "original"), "created_at": now(), "producer_job_id": state["id"],
        "parent_version_id": state.get("preparation_parent_version_id"),
        "language": state["manuscript_language"], "source": source, "files": files,
        "prepared": state["prepared"], "chapters": state["chapters"], "analysis": state["analysis"],
        "metadata_approval": state["metadata_approval"], "metadata_versions": state["metadata_versions"],
        "metadata_review_receipts": state["receipts"],
        "metadata_objects": metadata_objects,
    }
    library.publish_many([{"artifact": f"{prefix}/manifest.json", "data": json_bytes(version),
                          "expected_head": None, "contract": CONTRACT, "review_status": "provisional"}],
                         run_id=state["id"], workflow=None, stage="work-preparation", finalize=[prefix + "/"])
    return load_version(library, version_id)


def checkout_version(engine, version):
    """Copy verified immutable objects; never rewrite provenance to fit another run."""
    with engine.store.locked():
        revision, state = engine.store.load()
        if state["attempts"] or state.get("prepared"):
            raise ValueError("Only a new workflow can select a Work version.")
        if version["work_id"] != state["work_id"] or version["source"]["sha256"] != state["source"]["sha256"]:
            raise ValueError("Selected Work version does not match the workflow source.")
        for relative, artifact in version["files"].items():
            relative = _relative(relative)
            target = engine.workspace / relative
            if target.exists():
                raise ValueError(f"Work version would overwrite a workspace file: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(engine.library.read(artifact))
            engine.checkpoint(relative, "work_version_input")
        for key in ("prepared", "chapters", "analysis", "metadata_approval", "metadata_versions"):
            state[key] = copy.deepcopy(version[key])
        for sha, artifact in version["metadata_objects"].items():
            write_new(engine.root / "objects" / sha, engine.library.read(artifact))
        state["receipts"] = copy.deepcopy(version["metadata_review_receipts"])
        state["manuscript_language"] = version["language"]
        state["input_version"] = {key: version[key] for key in (
            "version_id", "publication_id", "work_id", "language", "source")}
        state["input_version"]["analysis_id"] = version["analysis"]["analysis_id"]
        state["input_version"]["analysis_manifest_sha256"] = version["analysis"]["manifest"]["sha256"]
        state["settings"] = engine.resolve_settings(state["definition"], state["settings"], version["language"])
        first = next((stage for stage in state["definition"]["stages"] if stage.get("iterate")), None)
        state["iterations"] = engine.build_iterations(state, first) if first else []
        engine.verify(state)
        engine.store.save(revision, state, "work_version.selected", state["input_version"])
        return state


def publish_changed_output(engine, state):
    """Accepted changed Markdown becomes a pending input, never pre-approved analysis."""
    if not state.get("input_version") or not state.get("acceptance"):
        return None
    old = [chapter["sha256"] for chapter in state["chapters"]]
    new = [artifact["sha256"] for artifact in state["outputs"]]
    if old == new and engine.output_language(state) == state["manuscript_language"]:
        return None
    existing = [v for v in versions(engine.library) if v.get("producer_run_id") == state["id"]]
    if existing:
        return existing[0]
    version_id = "wv-" + uuid.uuid4().hex
    prefix = f"work-versions/{version_id}"
    data = b"\n\n".join(engine.store.content(artifact).rstrip(b"\n") for artifact in state["outputs"]) + b"\n"
    source_path = f"{prefix}/source.md"
    source = engine.library.publish_many(
        [{"artifact": source_path, "data": data, "expected_head": None, "review_status": "accepted"}],
        run_id=state["id"], workflow=state["workflow"], stage="accepted-text",
        receipts=[state["acceptance"]["id"]])[0]
    version = {
        "contract": CONTRACT, "version_id": version_id, "work_id": state["work_id"], "status": "analysis_pending",
        "kind": "translation" if engine.output_language(state) != state["manuscript_language"] else "edited",
        "created_at": now(), "producer_run_id": state["id"],
        "parent_version_id": state["input_version"]["version_id"], "language": engine.output_language(state),
        "source": {"artifact": source_path, "publication_id": source["id"], "sha256": source["sha256"],
                   "source_name": f"{version_id}.md"},
        "chapters": state["outputs"], "files": {}, "analysis": None, "acceptance": state["acceptance"],
    }
    engine.library.publish_many(
        [{"artifact": f"{prefix}/manifest.json", "data": json_bytes(version), "expected_head": None,
          "contract": CONTRACT, "review_status": "accepted"}],
        run_id=state["id"], workflow=None, stage="accepted-text",
        receipts=[state["acceptance"]["id"]], finalize=[prefix + "/"])
    return version
