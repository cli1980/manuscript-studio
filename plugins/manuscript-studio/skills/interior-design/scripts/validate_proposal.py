"""Validate proposal shape/references, optionally checking a local preparation."""

from __future__ import annotations

import argparse
import functools
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

SKILL = Path(__file__).resolve().parents[1]
SCHEMA = SKILL / "schemas/interior-design-proposal.schema.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON field: {key}")
            result[key] = value
        return result

    def number(value):
        result = float(value)
        require(math.isfinite(result), "JSON numbers must be finite.")
        return result

    def invalid(value):
        raise ValueError(f"Invalid JSON constant: {value}")

    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_float=number, parse_constant=invalid)


def check_values(value):
    if isinstance(value, float):
        require(math.isfinite(value), "JSON numbers must be finite.")
    elif isinstance(value, str):
        require(value.strip(), "Text values must not be blank.")
    elif isinstance(value, list):
        for child in value:
            check_values(child)
    elif isinstance(value, dict):
        for child in value.values():
            check_values(child)


def index(items, label):
    result = {}
    for item in items:
        require(item["id"] not in result, f"Duplicate {label} ID: {item['id']}")
        result[item["id"]] = item
    return result


def pointer(document, path):
    require(path.startswith("/") and not re.search(r"~(?![01])", path), f"Invalid pointer: {path}")
    value = document
    for token in path[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            require(re.fullmatch(r"0|[1-9][0-9]*", token), f"Invalid list index in {path}")
            require(int(token) < len(value), f"Unknown pointer: {path}")
            value = value[int(token)]
        else:
            require(isinstance(value, dict) and token in value, f"Unknown pointer: {path}")
            value = value[token]
    return value


@functools.lru_cache(maxsize=1)
def vendor_profiles():
    path = SKILL / "scripts/vendor_profiles.py"
    spec = importlib.util.spec_from_file_location("_interior_vendor_profiles", path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


@functools.lru_cache(maxsize=1)
def preparation_helper():
    path = SKILL.parent / "prepare-manuscript/scripts/validate_preparation.py"
    spec = importlib.util.spec_from_file_location("_interior_preparation", path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def occurrences(proposal):
    yield from proposal["reading"]["important_excerpts"]
    for role in proposal["text_roles"]:
        yield from role["occurrences"]


def check_preparation(proposal, work_path):
    helper = preparation_helper()
    work_path = helper.plain_path(work_path)
    helper.validate(work_path, check_sources=True)
    work = helper.load_json(work_path)
    require(work["preparation"]["status"] == "ready", "Preparation must be ready.")
    basis = proposal["basis"]["preparation"]
    revision = work["preparation"]["current_revision"]
    manifest_path = helper.local_file(work_path.parent, f"revisions/{revision}/manifest.json")
    manifest = helper.load_json(manifest_path)
    expected = {
        "work_id": work["work_id"], "record_revision": work["record_revision"],
        "work_sha256": helper.digest(work_path), "revision": revision,
        "manifest_sha256": helper.digest(manifest_path),
        "language": work["metadata"]["manuscript_language"], "scope": manifest["scope"],
        "units": [{"chapter_id": unit["chapter_id"], "sha256": unit["sha256"]}
                  for unit in manifest["chapters"]],
    }
    require(basis == expected, "Stale or mismatched preparation/metadata basis.")
    units = {unit["chapter_id"]: unit for unit in manifest["chapters"]}
    locators = {f"revisions/{revision}/{unit['file']}": unit["sha256"] for unit in manifest["chapters"]}
    for evidence in proposal["evidence"]:
        if evidence["source"] == "prepared-text":
            require(evidence["locator"] in locators
                    and evidence["sha256"] == locators[evidence["locator"]],
                    "Prepared-text evidence must identify an exact bound unit.")
        elif evidence["source"] == "metadata":
            require(evidence["sha256"] == basis["work_sha256"]
                    and evidence["locator"].startswith("/metadata/"),
                    "Metadata evidence must bind work.json and a metadata pointer.")
            pointer(work, evidence["locator"])
    for occurrence in occurrences(proposal):
        unit = units[occurrence["chapter_id"]]
        data = helper.local_file(manifest_path.parent, unit["file"]).read_bytes()
        require(hashlib.sha256(data).hexdigest() == unit["sha256"], "Prepared unit changed.")
        start, end = occurrence["start_byte"], occurrence["end_byte"]
        require(end <= len(data), "Text span exceeds its prepared unit.")
        # Decode prefixes as well, so neither endpoint can split a UTF-8 character.
        data[:start].decode("utf-8")
        data[:end].decode("utf-8")
        require(hashlib.sha256(data[start:end]).hexdigest() == occurrence["text_sha256"],
                "Text span hash does not match prepared bytes.")


def validate(proposal, *, work_path=None):
    schema = load_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    error = next(Draft202012Validator(schema).iter_errors(proposal), None)
    if error:
        location = "/".join(map(str, error.absolute_path)) or "/"
        raise ValueError(f"{location}: {error.message}")
    check_values(proposal)
    vendor_profiles().validate(proposal)
    evidence = index(proposal["evidence"], "evidence")
    styles = index(proposal["design_system"]["styles"], "style")
    index(proposal["text_roles"], "text role")
    index(proposal["edition_brief"]["production_targets"], "production target")
    for key in ("recommendations", "questions"):
        index(proposal[key], key)
        for item in proposal[key]:
            if item["path"] is not None:
                pointer(proposal, item["path"])
    covered = {item["path"].split("/")[2] for item in proposal["recommendations"]}
    require({"page", "styles", "navigation", "furniture"} <= covered,
            "Provide rationale/evidence for page, styles, navigation and furniture.")

    def references(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "evidence_refs":
                    require(set(child) <= evidence.keys(), "Unknown evidence reference.")
                else:
                    references(child)
        elif isinstance(value, list):
            for child in value:
                references(child)
    references(proposal)
    require(proposal["reading"]["evidence_refs"], "Reading requires evidence.")
    require(proposal["reading"]["source"] != "supplied" or proposal["basis"]["reading_ref"],
            "Supplied reading requires a bound artifact reference.")
    preferences = proposal["author_preferences"]
    if any(preferences[key] for key in (
        "imprint", "isbn", "prior_design_ref", "likes", "avoid", "reference_designs",
    )) or preferences["expected_changes"] != "unknown" or preferences["series_direction"] != "unknown":
        require(preferences["evidence_refs"] and all(
            evidence[key]["source"] in ("author", "metadata") for key in preferences["evidence_refs"]
        ), "Author preferences require author/metadata evidence, not inferred reading.")

    basis = proposal["basis"]["preparation"]
    unit_ids = [unit["chapter_id"] for unit in basis["units"]]
    require(unit_ids == basis["scope"]["chapter_ids"], "Unit order must match prepared scope.")
    require(len(set(unit_ids)) == len(unit_ids), "Duplicate prepared unit ID.")
    units = {unit["chapter_id"]: unit["sha256"] for unit in basis["units"]}
    require(sum(style["role"] == "body" for style in styles.values()) == 1,
            "Exactly one body style is required.")
    levels = []
    for style in styles.values():
        level, paragraph = style["heading_level"], style["paragraph"]
        require((style["role"] == "heading") == (level is not None), "Heading level/role mismatch.")
        if level is not None:
            levels.append(level)
        if paragraph["model"] == "block":
            require(paragraph["first_line_indent_mm"] == 0, "Block paragraphs cannot have first-line indentation.")
    require(len(levels) == len(set(levels)), "Duplicate heading level.")
    for role in proposal["text_roles"]:
        require(role["style_id"] in styles, "Unknown text-role style.")
    for occurrence in occurrences(proposal):
        require(units.get(occurrence["chapter_id"]) == occurrence["chapter_sha256"],
                "Text span refers to an unknown or changed prepared unit.")
        require(occurrence["start_byte"] < occurrence["end_byte"], "Text range must not be empty/reversed.")
    page = proposal["design_system"]["page"]
    margins, trim = page["margins_mm"], page["trim_mm"]
    require(margins["inside"] + margins["outside"] + page["gutter_mm"] < trim["width"]
            and margins["top"] + margins["bottom"] < trim["height"], "Margins leave no text area.")
    require(page["chapter_start"] != "recto" or page["blank_policy"] != "no-added-blanks",
            "Recto openings require an explicit permitted-blank policy.")
    navigation = proposal["design_system"]["navigation"]
    require(navigation["include_toc"] == (navigation["toc_depth"] > 0), "TOC inclusion/depth mismatch.")
    require((navigation["scene_break"] == "ornament") == (navigation["ornament"] is not None),
            "Ornament must be specified only for ornamental scene breaks.")
    if work_path is not None:
        check_preparation(proposal, work_path)
    return {"valid": True, "status": "proposed", "preparation_checked": work_path is not None,
            "vendor_warnings": vendor_profiles().design_warnings(proposal),
            "external_artifacts_checked": False, "approved": False, "production_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposal", type=Path)
    parser.add_argument("--work", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(validate(load_json(args.proposal), work_path=args.work), indent=2))
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"interior-design validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
