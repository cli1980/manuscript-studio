#!/usr/bin/env python3
"""Migrate, enrich, or edit shared metadata without changing manuscript text.

Semantic deductions are supplied by the preparation agent as evidence-bound
proposals. This helper validates their evidence and fills only missing values.
"""

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import validate_preparation as contract


SKILL = Path(__file__).resolve().parents[1]
FIELDS = contract.load_json(SKILL / "schemas/manuscript-metadata.schema.json")["$defs"]["field"]["enum"]
INFERABLE = {
    "/manuscript_language", "/work_type", "/form", "/genres", "/audience",
    "/keywords", "/description", "/series/relationship",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def value_hash(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def field_value(metadata, field):
    value = metadata
    for key in field.strip("/").split("/"):
        value = value[key]
    return value


def put(metadata, field, value):
    contract.require(field in FIELDS, f"Unknown metadata field: {field}")
    keys = field.strip("/").split("/")
    target = metadata
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = copy.deepcopy(value)


def missing(value):
    return value is None or value == [] or value == {}


def record(work, field, origin, *, actor, rationale, basis=None, evidence=None,
           confidence=None, review="unreviewed"):
    work["metadata_provenance"][field] = {
        "origin": origin, "review_status": review, "confidence": confidence,
        "basis_revision": basis, "evidence": evidence or [], "rationale": rationale,
        "value_sha256": value_hash(field_value(work["metadata"], field)),
        "updated_at": now(), "updated_by": actor,
    }


def migrate(work):
    """Return a v2 copy. Preserve original-language uncertainty and all workflow state."""
    result = copy.deepcopy(work)
    if result["schema_version"] == 2:
        return result
    old = result["metadata"]
    result["metadata"] = copy.deepcopy(contract.load_json(
        SKILL / "references/work.example.json",
    )["metadata"])
    result["metadata"].update({
        "title": old["title"], "manuscript_language": old["source_language"],
        "work_type": old["work_type"], "genres": [old["genre"]] if old["genre"] else [],
        "contributors": [
            {"id": f"author-{index}", "name": name, "roles": ["author"]}
            for index, name in enumerate(old["authors"], 1)
        ],
    })
    result["metadata"]["edition"]["label"] = old["edition"]
    result["schema_version"] = 2
    result["metadata_provenance"] = {}
    for field in FIELDS:
        if not missing(field_value(result["metadata"], field)):
            record(result, field, "legacy", actor="prepare-metadata",
                   rationale="Preserved from schema version 1; confirmation history is unknown.")
    return result


def reconcile_edits(work):
    """Protect externally edited values, including deliberate nulls and empty lists."""
    changed = []
    for field in FIELDS:
        value = field_value(work["metadata"], field)
        previous = work["metadata_provenance"].get(field)
        if previous and previous["value_sha256"] != value_hash(value):
            record(work, field, "user_edit", actor="external-edit",
                   rationale="External edit detected; preserved without assuming author approval.")
            changed.append(field)
        elif not previous and not missing(value):
            record(work, field, "provided", actor="existing-record",
                   rationale="Existing value preserved; its confirmation history is unknown.")
    return changed


def source_texts(work_path, work):
    revision = work["preparation"]["current_revision"]
    contract.require(revision is not None, "Enrichment requires a prepared revision.")
    manifest_path = contract.local_file(work_path.parent, f"revisions/{revision}/manifest.json")
    manifest = contract.load_json(manifest_path)
    contract.require(manifest["status"] == "verified", "Enrichment requires verified extracted text.")
    texts = {
        item["chapter_id"]: contract.local_file(
            manifest_path.parent, item["file"],
        ).read_text(encoding="utf-8")
        for item in manifest["chapters"]
    }
    return manifest, texts


def measure(manifest, texts):
    from markdown_it import MarkdownIt

    parts = []
    parser = MarkdownIt("commonmark")
    for text in texts.values():
        for token in parser.parse(text):
            if token.type in {"fence", "code_block"}:
                parts.append(token.content)
            elif token.type == "inline":
                parts.append("".join(
                    child.content if child.type in {"text", "code_inline"} else
                    "\n" if child.type in {"softbreak", "hardbreak"} else ""
                    for child in token.children or []
                ))
    text = "\n".join(parts)
    # These scripts require language-specific segmentation; do not call a
    # whitespace count a Chinese/Japanese/Thai/Khmer word count.
    unsegmented = re.search(r"[\u3400-\u9fff\u3040-\u30ff\u0e00-\u0e7f\u1780-\u17ff\U00020000-\U0003134f]", text)
    words = None if unsegmented else len(re.findall(r"\w+(?:['’\-]\w+)*", text, re.UNICODE))
    return {
        "word_count": words,
        "non_whitespace_character_count": sum(not char.isspace() for char in text),
        "unit_count": len(manifest["chapters"]),
        "method": (
            "commonmark-text-v1: text and code, all prepared units including headings and notes; "
            "excludes markup, link destinations and image alt text. Unicode word tokens with "
            "internal apostrophes/hyphens; word_count=null when segmentation is required."
        ),
        "basis_revision": manifest["revision"],
        "scope": copy.deepcopy(manifest["scope"]),
    }


def enrich(work, manifest, texts, proposals, actor):
    revision = manifest["revision"]
    applied, skipped = [], []
    seen = set()
    for proposal in proposals:
        contract.require(isinstance(proposal, dict), "Each proposal must be an object.")
        contract.require(set(proposal) == {
            "field", "value", "origin", "confidence", "basis_revision", "evidence", "rationale",
        }, "Proposal fields must match the metadata contract.")
        field = proposal["field"]
        contract.require(field in FIELDS and field != "/extent", "Invalid proposal field.")
        contract.require(field not in seen, f"Duplicate proposal for {field}.")
        seen.add(field)
        contract.require(proposal["origin"] in ("extracted", "inferred"), "Invalid proposal origin.")
        if proposal["origin"] == "inferred":
            contract.require(field in INFERABLE, f"{field} requires explicit source information, not inference.")
            if field in {"/form", "/series/relationship"}:
                contract.require(manifest["scope"]["kind"] == "whole_work",
                                 "Whole-work form or series inference requires whole-work coverage.")
        contract.require(proposal["confidence"] in ("low", "medium", "high"),
                         "A proposal requires an explicit confidence level.")
        contract.require(proposal["basis_revision"] == revision, "Proposal uses a different source revision.")
        contract.require(proposal["evidence"], "A proposal requires manuscript evidence.")
        for evidence in proposal["evidence"]:
            contract.require(isinstance(evidence, dict) and set(evidence) == {"chapter_id", "locator", "quote"},
                             "Evidence requires chapter_id, locator, and quote.")
            quote = evidence["quote"]
            contract.require(isinstance(evidence["chapter_id"], str)
                             and isinstance(evidence["locator"], str) and evidence["locator"].strip()
                             and isinstance(quote, str) and quote.strip()
                             and quote in texts.get(evidence["chapter_id"], ""),
                             "Proposal quote is absent from its cited chapter.")
        # Validate even proposals that will be skipped; never silently accept an
        # invalid field value or forged provenance.
        candidate = copy.deepcopy(work)
        put(candidate["metadata"], field, proposal["value"])
        record(candidate, field, proposal["origin"], actor=actor,
               rationale=proposal["rationale"], basis=revision, evidence=proposal["evidence"],
               confidence=proposal["confidence"], review="proposed")
        contract.schema_check(contract.validators()[0], candidate, "proposal")
        contract.require(not missing(proposal["value"]), "Do not propose an empty value.")
        if (not missing(field_value(work["metadata"], field))
                or field in work["metadata_provenance"]):
            skipped.append(field)
            continue
        put(work["metadata"], field, proposal["value"])
        work["metadata_provenance"][field] = candidate["metadata_provenance"][field]
        applied.append(field)

    if missing(work["metadata"]["extent"]) and "/extent" not in work["metadata_provenance"]:
        work["metadata"]["extent"] = measure(manifest, texts)
        record(work, "/extent", "computed", actor=actor, basis=revision,
               rationale="Computed from the verified prepared scope using the recorded method.")
        applied.append("/extent")
    for field, provenance in work["metadata_provenance"].items():
        basis = (work["metadata"]["extent"]["basis_revision"]
                 if field == "/extent" and work["metadata"]["extent"] else provenance["basis_revision"])
        if basis not in {None, revision} and provenance["review_status"] != "stale":
            provenance["review_status"] = "stale"
            provenance["updated_at"] = now()
    return applied, skipped


def save(work_path, before, work):
    """Serialize helper writers and reject a concurrently changed work record."""
    if work == json.loads(before):
        return False
    work["record_revision"] += 1
    work["updated_at"] = now()
    lock = contract.plain_path(work_path.parent / ".metadata.lock")
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    temporary = None
    try:
        os.close(descriptor)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=work_path.parent, suffix=".json", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(work, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        contract.validate(temporary)
        contract.require(work_path.read_bytes() == before, "Work record changed concurrently; reread and retry.")
        history = contract.plain_path(work_path.parent / "metadata-history")
        history.mkdir(exist_ok=True)
        backup = contract.plain_path(history / f"{work['record_revision'] - 1}-{hashlib.sha256(before).hexdigest()[:16]}.json")
        if not backup.exists():
            with backup.open("xb") as handle:
                handle.write(before)
        contract.require(work_path.read_bytes() == before, "Work record changed concurrently; reread and retry.")
        os.replace(temporary, work_path)
        return True
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def update(work_path, operation, *, proposals=None, field=None, value=None, actor="user", rationale="Explicit metadata edit."):
    work_path = contract.plain_path(work_path)
    before = work_path.read_bytes()
    contract.validate(work_path)
    original = contract.load_json(work_path)
    contract.require(work_path.read_bytes() == before, "Work record changed concurrently; reread and retry.")
    work = migrate(original)
    changed = reconcile_edits(work)
    applied, skipped = [], []
    if operation == "set":
        put(work["metadata"], field, value)
        record(work, field, "user_edit", actor=actor, rationale=rationale, review="confirmed")
        changed.append(field)
    elif operation == "enrich":
        manifest, texts = source_texts(work_path, work)
        proposals = [] if proposals is None else proposals
        contract.require(isinstance(proposals, list), "Proposals must be a JSON array.")
        applied, skipped = enrich(work, manifest, texts, proposals, actor)
    else:
        contract.require(operation == "migrate", "Unknown metadata operation.")
    written = save(work_path, before, work)
    return {
        "written": written, "schema_version": work["schema_version"],
        "record_revision": work["record_revision"], "applied": applied, "skipped": skipped,
        "edited_fields": changed,
        "missing_fields": [
            path for path in FIELDS
            if missing(field_value(work["metadata"], path)) and path not in work["metadata_provenance"]
        ],
        "stale_fields": [path for path, item in work["metadata_provenance"].items() if item["review_status"] == "stale"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["migrate", "enrich", "set"])
    parser.add_argument("work_json", type=Path)
    parser.add_argument("--proposals", type=Path, help="Evidence-bound JSON array written by the preparation agent")
    parser.add_argument("--field", choices=FIELDS)
    parser.add_argument("--value-file", type=Path, help="JSON value for an explicit edit, including null or []")
    parser.add_argument("--by", default="user", help="Actor responsible for this operation")
    parser.add_argument("--reason", default="Explicit metadata edit.")
    args = parser.parse_args()
    if args.operation == "set" and (args.field is None or args.value_file is None):
        parser.error("set requires --field and --value-file")
    if args.operation != "set" and (args.field is not None or args.value_file is not None):
        parser.error("--field and --value-file are only valid with set")
    if args.proposals and args.operation != "enrich":
        parser.error("--proposals is only valid with enrich")
    try:
        result = update(
            args.work_json, args.operation,
            proposals=contract.load_json(args.proposals) if args.proposals else None,
            field=args.field, value=contract.load_json(args.value_file) if args.value_file else None,
            actor=args.by, rationale=args.reason,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, UnicodeError, ImportError) as exc:
        print(f"manuscript metadata update failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
