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
from string import Formatter

from jsonschema import Draft202012Validator
from markdown_it import MarkdownIt

SKILL = Path(__file__).resolve().parents[1]
SCHEMA = SKILL / "schemas/interior-design-proposal.schema.json"
FURNITURE_TOKENS = {"work_title", "chapter_title", "author", "page", "page_count"}


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


@functools.lru_cache(maxsize=1)
def furniture_presets():
    return load_json(SCHEMA)["$defs"]["furniture_content"]["x-preset-templates"]


def furniture_template(content):
    """Resolve the closed preset selection before token and metadata validation."""
    return content["template"] if content["preset"] == "custom" else furniture_presets()[content["preset"]]


def furniture_tokens(text):
    fields = set()
    try:
        for _, name, spec, conversion in Formatter().parse(text):
            require(name is None or name in FURNITURE_TOKENS, f"Unknown header/footer token: {name}")
            require(not spec and conversion is None, "Header/footer format specifiers/conversions are not allowed.")
            if name is not None:
                fields.add(name)
    except ValueError as exc:
        raise ValueError(f"Invalid header/footer template: {exc}") from exc
    return fields


def furniture_sections(proposal):
    furniture = proposal["design_system"]["furniture"]
    overrides = {item["chapter_id"]: item["settings"] for item in furniture["section_overrides"]}
    return [(unit["chapter_id"], overrides.get(unit["chapter_id"], furniture["default_section"]))
            for unit in proposal["basis"]["preparation"]["units"]]


def check_furniture(proposal, styles):
    furniture = proposal["design_system"]["furniture"]
    unit_ids = {unit["chapter_id"] for unit in proposal["basis"]["preparation"]["units"]}
    overrides = [item["chapter_id"] for item in furniture["section_overrides"]]
    require(len(overrides) == len(set(overrides)), "Duplicate header/footer section override.")
    require(set(overrides) <= unit_ids, "Header/footer override refers to an unknown prepared unit.")
    sections = [furniture["default_section"]] + [item["settings"] for item in furniture["section_overrides"]]
    height = proposal["design_system"]["page"]["trim_mm"]["height"]
    for settings in sections:
        require(settings["header_distance_mm"] < height and settings["footer_distance_mm"] < height,
                "Header/footer distance must be less than page height.")
        for group in ("headers", "footers"):
            for variant, part in settings[group].items():
                require(not part["link_to_previous"] or not part["paragraphs"],
                        "Linked header/footer parts cannot also define local paragraphs.")
                active = (variant == "default" or variant == "even" and furniture["different_odd_even"]
                          or variant == "first" and settings["different_first_page"])
                require(active or not part["paragraphs"] and not part["link_to_previous"],
                        f"Inactive {variant} header/footer variants must be blank and unlinked.")
                for paragraph in part["paragraphs"]:
                    require(paragraph["style_id"] in styles, "Unknown header/footer style.")
                    furniture_tokens(furniture_template(paragraph["content"]))
    for group in ("headers", "footers"):
        require(not any(part["link_to_previous"] for part in furniture_sections(proposal)[0][1][group].values()),
                "The first section cannot link headers/footers to a previous section.")


def paragraphs(data):
    """Catalog whole CommonMark text blocks; never recover inline byte offsets."""
    tokens = MarkdownIt("commonmark").parse(data.decode("utf-8"))
    result = []
    for offset, token in enumerate(tokens):
        if token.type not in ("paragraph_open", "heading_open"):
            continue
        markdown = tokens[offset + 1].content
        result.append({
            "paragraph_index": len(result) + 1,
            "paragraph_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            "kind": "heading" if token.type == "heading_open" else "paragraph",
            "markdown": markdown,
        })
    return result


def prepared_context(work_path):
    helper = preparation_helper()
    work_path = helper.plain_path(work_path)
    helper.validate(work_path, check_sources=True)
    work = helper.load_json(work_path)
    require(work["preparation"]["status"] == "ready", "Preparation must be ready.")
    revision = work["preparation"]["current_revision"]
    manifest_path = helper.local_file(work_path.parent, f"revisions/{revision}/manifest.json")
    manifest = helper.load_json(manifest_path)
    return helper, work_path, work, manifest_path, manifest


def paragraph_catalog(work_path):
    helper, _, _, manifest_path, manifest = prepared_context(work_path)
    return {
        "contract": "interior-design-paragraphs/1",
        "units": [{
            "chapter_id": unit["chapter_id"], "chapter_sha256": unit["sha256"],
            "paragraphs": paragraphs(prepared_unit(helper, manifest_path, unit)),
        } for unit in manifest["chapters"]],
    }


def prepared_unit(helper, manifest_path, unit):
    data = helper.local_file(manifest_path.parent, unit["file"]).read_bytes()
    require(hashlib.sha256(data).hexdigest() == unit["sha256"], "Prepared unit changed.")
    return data


def check_preparation(proposal, work_path):
    helper, work_path, work, manifest_path, manifest = prepared_context(work_path)
    basis = proposal["basis"]["preparation"]
    revision = work["preparation"]["current_revision"]
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
    metadata = work["metadata"]
    authors = [person["name"] for person in metadata["contributors"] if "author" in person["roles"]]
    for chapter_id, settings in furniture_sections(proposal):
        available = {"work_title": metadata["title"], "chapter_title": units[chapter_id]["title"],
                     "author": ", ".join(authors)}
        for group in ("headers", "footers"):
            for part in settings[group].values():
                for paragraph in part["paragraphs"]:
                    tokens = furniture_tokens(furniture_template(paragraph["content"]))
                    if (units[chapter_id]["role"] == "front_matter"
                            and proposal["design_system"]["furniture"]["front_matter_numbering"] == "none"):
                        require("page" not in tokens, "Unnumbered front matter cannot display a {page} field.")
                    for token in tokens - {"page", "page_count"}:
                        require(available[token], f"Missing {token} metadata for header/footer in {chapter_id}.")
    data_by_unit = {}

    def unit_data(chapter_id):
        if chapter_id not in data_by_unit:
            data_by_unit[chapter_id] = prepared_unit(helper, manifest_path, units[chapter_id])
        return data_by_unit[chapter_id]

    catalogs = {}
    for role in proposal["text_roles"]:
        for occurrence in role["occurrences"]:
            chapter_id = occurrence["chapter_id"]
            if chapter_id not in catalogs:
                catalogs[chapter_id] = paragraphs(unit_data(chapter_id))
            catalog = catalogs[chapter_id]
            number = int(occurrence["paragraph_index"])
            require(number <= len(catalog), f"Paragraph {number} exceeds prepared unit {chapter_id}.")
            require(catalog[number - 1]["paragraph_sha256"] == occurrence["paragraph_sha256"],
                    f"Paragraph hash does not match catalog entry {chapter_id}/{number}.")
    for occurrence in proposal["reading"]["important_excerpts"]:
        data = unit_data(occurrence["chapter_id"])
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
    check_furniture(proposal, styles)
    assigned = set()
    for role in proposal["text_roles"]:
        require(role["style_id"] in styles, "Unknown text-role style.")
        for occurrence in role["occurrences"]:
            require(units.get(occurrence["chapter_id"]) == occurrence["chapter_sha256"],
                    "Paragraph refers to an unknown or changed prepared unit.")
            key = occurrence["chapter_id"], occurrence["paragraph_index"]
            require(key not in assigned, "A paragraph may have only one role assignment.")
            assigned.add(key)
    for occurrence in proposal["reading"]["important_excerpts"]:
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
    parser.add_argument("proposal", type=Path, nargs="?")
    parser.add_argument("--work", type=Path)
    parser.add_argument("--list-paragraphs", action="store_true",
                        help="List whole-paragraph role anchors from --work; no proposal is required.")
    args = parser.parse_args(argv)
    if args.list_paragraphs and (not args.work or args.proposal):
        parser.error("--list-paragraphs requires --work and no proposal path.")
    if not args.list_paragraphs and not args.proposal:
        parser.error("Provide a proposal path, or --work WORK --list-paragraphs.")
    try:
        result = (paragraph_catalog(args.work) if args.list_paragraphs
                  else validate(load_json(args.proposal), work_path=args.work))
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"interior-design validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
