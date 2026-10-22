"""Shared source-task/candidate contract and automatic case discovery."""

import copy
import re
import uuid

IDENTIFIER = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
OPAQUE_CANDIDATE = re.compile(r"c-[a-f0-9]{16}\Z")


def new_candidate_id():
    return "c-" + uuid.uuid4().hex[:16]


def discover_cases(directory, pattern="*"):
    """Automatic batches exclude local manual cases; explicit IDs still work."""
    return [path for path in sorted(directory.glob(f"{pattern}/case.json"))
            if not path.parent.name.startswith(".") and not (path.parent / ".local-only").exists()]


def candidates(case):
    """Read v2 candidates or project a legacy single-candidate case."""
    version = case.get("schema_version", 1)
    if type(version) is not int or version not in {1, 2}:
        raise ValueError("Unsupported translation case version.")
    if type(case.get("revision")) is not int or case["revision"] < 1:
        raise ValueError("Case revisions must be positive integers.")
    if version == 1:
        if not isinstance(case.get("translation_file"), str) or not case["translation_file"]:
            raise ValueError("Legacy cases require a translation file.")
        if not isinstance(case.get("provenance", {}), dict):
            raise ValueError("Candidate provenance must be an object.")
        return [{
            "candidate_id": "baseline", "revision": case["revision"],
            "translation_file": case["translation_file"],
            "status": case.get("status", "placeholder"),
            "provenance": copy.deepcopy(case.get("provenance", {})),
        }]
    if version != 2 or "translation_file" in case:
        raise ValueError("Expected a version-2 source task with candidates, or a legacy version-1 case.")
    values = case.get("candidates")
    if not isinstance(values, list):
        raise ValueError("Case candidates must be an array.")
    ids = set()
    for item in values:
        if not isinstance(item, dict):
            raise ValueError("Each candidate must be an object.")
        cid = item.get("candidate_id")
        if not isinstance(cid, str) or len(cid) > 100 or not IDENTIFIER.fullmatch(cid) or cid in ids:
            raise ValueError("Candidate identifiers must be valid and unique within a case.")
        ids.add(cid)
        if type(item.get("revision")) is not int or item["revision"] < 1:
            raise ValueError("Candidate revisions must be positive integers.")
        if not isinstance(item.get("translation_file"), str) or not item["translation_file"]:
            raise ValueError("Each candidate requires a translation file.")
        if item.get("status") not in {"ready", "placeholder"}:
            raise ValueError("Candidate status must be ready or placeholder.")
        if not isinstance(item.get("provenance"), dict):
            raise ValueError("Candidate provenance must be an object.")
        if "derived_from" in item and not isinstance(item["derived_from"], str):
            raise ValueError("derived_from must name another candidate or be omitted.")
    parents = {item["candidate_id"]: item.get("derived_from") for item in values}
    for cid, parent in parents.items():
        visited = {cid}
        while parent is not None:
            if not isinstance(parent, str) or parent not in ids or parent in visited:
                raise ValueError("Candidate derivation must refer to another candidate without cycles.")
            visited.add(parent)
            parent = parents[parent]
    return copy.deepcopy(values)


def select_candidate(case, candidate_id=None):
    values = candidates(case)
    if candidate_id is None:
        if len(values) != 1:
            raise ValueError("Select a candidate explicitly for a case with zero or multiple candidates.")
        return values[0]
    for item in values:
        if item["candidate_id"] == candidate_id:
            return item
    raise ValueError("Candidate not found in this case.")


def judgment_candidate(record, case):
    cid = record.get("candidate_id")
    revision = record.get("candidate_revision")
    if cid is None and case.get("schema_version", 1) == 1:
        return "baseline", record.get("case_revision")
    if not isinstance(cid, str) or not IDENTIFIER.fullmatch(cid) or type(revision) is not int or revision < 1:
        raise ValueError("Judgments must bind a candidate ID and revision.")
    return cid, revision


def migrate_case(case, judgments):
    """Preserve text paths and historical revisions; never invent human ratings."""
    values = candidates(case)
    if case.get("schema_version", 1) == 2:
        return copy.deepcopy(case), copy.deepcopy(judgments)
    result = copy.deepcopy(case)
    result.update(schema_version=2, candidates=values, translation_instructions=None)
    result.pop("translation_file", None)
    result.pop("provenance", None)
    migrated = []
    for record in judgments:
        item = copy.deepcopy(record)
        cid, revision = judgment_candidate(record, case)
        item.update(candidate_id=cid, candidate_revision=revision)
        migrated.append(item)
    return result, migrated
