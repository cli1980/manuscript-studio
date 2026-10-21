"""Evaluate prepare-manuscript outputs against case-defined reference data, without an LLM."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import importlib.metadata
import json
import os
import re
import sys
import uuid
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent
SKILL = ROOT.parent / "plugins/manuscript-studio/skills/prepare-manuscript"
SPEC = importlib.util.spec_from_file_location("preparation_contract_validator", SKILL / "scripts/validate_preparation.py")
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)
MARKDOWN = MarkdownIt("commonmark").enable("table")
STRUCTURAL = {
    "blockquote_open", "blockquote_close", "bullet_list_open", "bullet_list_close",
    "ordered_list_open", "ordered_list_close", "list_item_open", "list_item_close",
    "table_open", "table_close", "thead_open", "thead_close", "tbody_open", "tbody_close",
    "tr_open", "tr_close", "th_open", "th_close", "td_open", "td_close",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return CONTRACT.digest(path)


def read_json(path):
    return CONTRACT.load_json(path)


def reference_path(base, relative, allowed):
    require(isinstance(relative, str) and relative and "\\" not in relative and ":" not in relative,
            "Reference paths must be relative and use forward slashes.")
    require(not Path(relative).is_absolute(), "Absolute reference paths are not allowed.")
    path = CONTRACT.plain_path(base / relative)
    require(any(path.is_relative_to(area) for area in allowed), "Reference escapes its allowed input area.")
    require(path.is_file(), f"Missing reference file: {relative}")
    return path


def schema_check(value, name):
    schema = read_json(ROOT / "schemas" / name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    error = next(iter(validator.iter_errors(value)), None)
    if error:
        location = ".".join(map(str, error.absolute_path)) or "<root>"
        raise ValueError(f"{name}:{location}: {error.message}")


def visible_statistics(blocks):
    paragraphs = ["".join(character for character in block["text"] if not character.isspace())
                  for block in blocks]
    paragraphs = [text for text in paragraphs if text]
    combined = "".join(paragraphs)
    return {
        "nonempty_paragraphs": len(paragraphs),
        "characters_excluding_whitespace": len(combined),
        "text_sha256_excluding_whitespace": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        "paragraph_sequence_sha256": hashlib.sha256(
            json.dumps(paragraphs, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }


def asset_resolver(markdown_path, assets):
    def resolve(target):
        parts = urllib.parse.urlsplit(target or "")
        if parts.scheme in {"http", "https"}:
            return {"url": target}
        require(not parts.scheme and not parts.netloc, "Unsupported image URI.")
        relative = Path(urllib.parse.unquote(parts.path))
        require(not relative.is_absolute(), "Images must reference declared package assets.")
        path = Path(os.path.abspath(markdown_path.parent / relative))
        require(path in assets, "Image references an undeclared asset.")
        return {"sha256": assets[path], "fragment": parts.fragment, "query": parts.query}
    return resolve


def canonical_markdown(text, profile, resolve_asset=None):
    tokens = MARKDOWN.parse(text)
    noncode_lines = text.splitlines(keepends=True)
    for token in tokens:
        if token.type in {"fence", "code_block"} and token.map:
            noncode_lines[token.map[0]:token.map[1]] = ["\n"] * (token.map[1] - token.map[0])
    require(not re.search(r"(?m)^ {0,3}\[\^[^\]]+\]:", "".join(noncode_lines)),
            "Footnote syntax requires a supported footnote profile; it cannot be silently ignored.")
    blocks, structure, parents = [], [], []
    for token in tokens:
        if token.type == "html_block":
            raise ValueError("Raw HTML requires a different reference profile; it cannot be silently ignored.")
        if token.type in STRUCTURAL:
            entry = {"type": token.type, "at_block": len(blocks)}
            if token.type == "ordered_list_open":
                entry["start"] = token.attrGet("start") or 1
            structure.append(entry)
        if token.nesting == 1:
            parents.append(token)
        elif token.nesting == -1:
            parents.pop()
        if token.type == "inline":
            parent = parents[-1]
            kind = "heading" if parent.tag.startswith("h") and parent.tag[1:].isdigit() else (
                "table_cell" if parent.tag in {"th", "td"} else "paragraph"
            )
            visible, marks, links, images = "", [], [], []
            for child in token.children or []:
                if child.type in {"text", "code_inline"}:
                    if child.type == "code_inline":
                        marks.append(("code", len(visible), len(child.content)))
                    visible += child.content
                elif child.type == "softbreak":
                    visible += " "
                elif child.type == "hardbreak":
                    visible += "\n"
                elif child.type in {"em_open", "em_close", "strong_open", "strong_close"}:
                    marks.append((child.type, len(visible)))
                elif child.type == "link_open":
                    links.append((len(visible), child.attrGet("href"), child.attrGet("title")))
                elif child.type == "link_close":
                    links.append((len(visible), "link_end"))
                elif child.type == "image":
                    target = child.attrGet("src")
                    images.append({"alt": child.content, "target": resolve_asset(target) if resolve_asset else target,
                                   "title": child.attrGet("title")})
                else:
                    raise ValueError(f"Unsupported inline Markdown token: {child.type}")
            block = {"kind": kind, "text": visible.replace("\t", " ")}
            if kind == "heading":
                block["level"] = int(parent.tag[1:])
            if kind == "table_cell":
                block["cell_type"] = parent.tag
            if profile["check_inline_formatting"]:
                block["marks"] = marks
            if profile["check_links"]:
                block["links"] = links
            block["images"] = images
            blocks.append(block)
        elif token.type in {"fence", "code_block"}:
            blocks.append({"kind": "code", "text": token.content.replace("\r\n", "\n"), "language": token.info.strip()})
        elif token.type == "hr":
            blocks.append({"kind": "thematic_break", "text": ""})
    return {"blocks": blocks, "structure": structure if profile["check_block_structure"] else []}


def load_case(case_path, eval_root):
    case_path = CONTRACT.plain_path(case_path)
    require(case_path.is_relative_to(eval_root / "cases/prepare-manuscript"), "Case must be in the preparation case directory.")
    case = read_json(case_path)
    schema_check(case, "preparation-case.schema.json")
    input_root = CONTRACT.plain_path(case_path.parent / case["input_location"])
    require(input_root.is_relative_to(eval_root / "fixtures/manuscripts") and input_root.is_dir(),
            "Input location must be a manuscript fixture directory.")
    sources = {}
    for source in case["sources"]:
        require(source["source_id"] not in sources, "Source IDs must be unique.")
        path = reference_path(input_root, source["file"], [input_root])
        require(case["recursive"] or path.parent == input_root, "Source requires unapproved recursive discovery.")
        sources[source["source_id"]] = {"path": path, "sha256": source["sha256"]}
    require(sources or case["expected_preparation_status"] == "blocked",
            "A successful preparation case must supply source fixtures.")
    ref_path = reference_path(case_path.parent, case["reference_file"],
                              [case_path.parent, eval_root / "fixtures/reference-outputs"])
    reference = read_json(ref_path)
    schema_check(reference, "preparation-reference.schema.json")
    require(reference["case_id"] == case["case_id"], "Reference belongs to a different case.")
    require(reference["source_hashes"] == {key: value["sha256"] for key, value in sources.items()},
            "Reference is not bound to the case's source identities.")
    ids = [unit["unit_id"] for unit in reference["units"]]
    require(len(ids) == len(set(ids)), "Reference unit IDs must be unique.")
    require(case["expected_preparation_status"] != "ready" or reference["units"],
            "A ready-case reference must describe at least one unit.")
    require(len({value["path"] for value in sources.values()}) == len(sources), "Source files must be unique.")
    for asset in reference["assets"]:
        asset["resolved_file"] = reference_path(ref_path.parent, asset["file"],
                                               [case_path.parent, eval_root / "fixtures/reference-outputs"])
        require(digest(asset["resolved_file"]) == asset["sha256"], "Reference asset hash does not match.")
    asset_hashes = {asset["resolved_file"]: asset["sha256"] for asset in reference["assets"]}
    for unit in reference["units"]:
        unit["resolved_file"] = reference_path(ref_path.parent, unit["file"],
                                               [case_path.parent, eval_root / "fixtures/reference-outputs"])
        require(digest(unit["resolved_file"]) == unit["sha256"], "Reference Markdown hash does not match.")
        canonical_markdown(unit["resolved_file"].read_text(encoding="utf-8"), reference["profile"],
                           asset_resolver(unit["resolved_file"], asset_hashes))
    if case.get("ground_truth_file"):
        path = reference_path(case_path.parent, case["ground_truth_file"],
                              [case_path.parent, eval_root / "fixtures/reference-outputs"])
        require(digest(path) == case["ground_truth_sha256"], "Frozen ground-truth hash does not match.")
        ground_truth = read_json(path)
        schema_check(ground_truth, "preparation-ground-truth.schema.json")
        require(ground_truth["case_id"] == case["case_id"] and ground_truth["source_hashes"] == reference["source_hashes"],
                "Ground truth belongs to different source inputs or case.")
        require([unit["unit_id"] for unit in ground_truth["units"]] == ids,
                "Reference units differ from the frozen ground truth.")
        combined_blocks = []
        for unit, truth in zip(reference["units"], ground_truth["units"]):
            require(all(unit[key] == truth[key] for key in ("title", "source_number", "role")),
                    "Reference section identity differs from source ground truth.")
            blocks = canonical_markdown(unit["resolved_file"].read_text(encoding="utf-8"), reference["profile"],
                                        asset_resolver(unit["resolved_file"], asset_hashes))["blocks"]
            require(visible_statistics(blocks) == truth["statistics"],
                    f"Reference content differs from source ground truth: {unit['unit_id']}")
            combined_blocks.extend(blocks)
        require(visible_statistics(combined_blocks) == ground_truth["totals"]["whole_document"],
                "Reference whole-document totals differ from source ground truth.")
        reference["ground_truth"] = ground_truth
        reference["ground_truth_path"] = path
    return case, reference, sources, input_root, ref_path


def differences(expected, actual):
    encode = lambda block: json.dumps(block, sort_keys=True, ensure_ascii=False)
    left, right = list(map(encode, expected)), list(map(encode, actual))
    mismatches = []
    counts = {"missing_blocks": 0, "extra_blocks": 0, "replaced_blocks": 0}
    for operation, a, b, c, d in difflib.SequenceMatcher(a=left, b=right, autojunk=False).get_opcodes():
        if operation == "equal":
            continue
        if operation == "delete":
            counts["missing_blocks"] += b - a
        elif operation == "insert":
            counts["extra_blocks"] += d - c
        else:
            counts["replaced_blocks"] += max(b - a, d - c)
        if len(mismatches) < 10:
            mismatches.append({
                "operation": operation, "expected_range": [a, b], "actual_range": [c, d],
                "expected_excerpt": expected[a].get("text", "")[:160] if a < b else None,
                "actual_excerpt": actual[c].get("text", "")[:160] if c < d else None,
            })
    return {**counts, "differences": mismatches}


def evaluate(case_path, work_path, *, eval_root=ROOT, trace_path=None, visual_review_path=None):
    eval_root = CONTRACT.plain_path(eval_root)
    case_path = CONTRACT.plain_path(case_path)
    case, reference, sources, input_root, ref_path = load_case(case_path, eval_root)
    work_path = CONTRACT.plain_path(work_path)
    root = work_path.parent
    require(not any(root.is_relative_to(area) or area.is_relative_to(root)
                    for area in (eval_root / "cases", eval_root / "fixtures")),
            "Candidate output must be separate from evaluation cases and reference/input fixtures.")
    checks = []
    report = {
        "schema_version": 1, "skill": "prepare-manuscript", "case_id": case["case_id"],
        "case_sha256": digest(case_path), "reference_sha256": digest(ref_path),
        "reference_status": reference["review"]["status"], "candidate": str(work_path),
        "checked_at": datetime.now(timezone.utc).isoformat(), "checks": checks, "chapters": [],
        "validation_contract": {
            "evaluator_sha256": digest(Path(__file__)),
            "skill_definition_sha256_at_check": digest(SKILL / "SKILL.md"),
            "validator_sha256": digest(Path(CONTRACT.__file__)),
            "schema_hashes": {name: digest(SKILL / "schemas" / name)
                              for name in ("work.schema.json", "revision.schema.json")},
            "markdown_it_version": importlib.metadata.version("markdown-it-py"),
        },
    }
    expected_hashes = {case_path: report["case_sha256"], ref_path: report["reference_sha256"]}
    expected_hashes.update({item["path"]: item["sha256"] for item in sources.values()})
    expected_hashes.update({unit["resolved_file"]: unit["sha256"] for unit in reference["units"]})
    expected_hashes.update({asset["resolved_file"]: asset["sha256"] for asset in reference["assets"]})
    ground_truth = reference.get("ground_truth")
    if ground_truth:
        report["ground_truth_sha256"] = case["ground_truth_sha256"]
        report["ground_truth_counts"] = ground_truth["counts"]
        expected_hashes[reference["ground_truth_path"]] = case["ground_truth_sha256"]
    if work_path.is_file():
        expected_hashes[work_path] = digest(work_path)

    def add(name, status, detail, required=True):
        checks.append({"check": name, "status": status, "required": required, "detail": detail})

    source_ok = all(digest(value["path"]) == value["sha256"] for value in sources.values())
    add("source_integrity", ("passed" if source_ok else "failed") if sources else "not_checked",
        "Compared current source bytes with case-bound SHA-256 hashes." if sources else "No source files are supplied for this blocked-input scenario.",
        required=bool(sources))
    review = reference["review"]
    approved = review["status"] == "approved" and bool(review["reviewed_by"]) and bool(review["reviewed_at"])
    add("reference_review", "passed" if approved else "not_checked",
        "Reference independently reviewed." if approved else (
            "Frozen source text/structure is verified; Markdown presentation review remains pending."
            if ground_truth else "Reference is a draft; content differences are provisional until it is reviewed."
        ))
    work, manifest = None, None
    try:
        candidate_work = read_json(work_path)
        work_validator, revision_validator = CONTRACT.validators()
        CONTRACT.schema_check(work_validator, candidate_work, "work")
        work = candidate_work
        revision = work["preparation"]["current_revision"]
        manifest_path = CONTRACT.local_file(root, f"revisions/{revision}/manifest.json") if revision else None
        if manifest_path:
            expected_hashes[manifest_path] = digest(manifest_path)
        manifest = read_json(manifest_path) if manifest_path else None
        if manifest:
            CONTRACT.schema_check(revision_validator, manifest, "manifest")
        declared = work["discovery"]
        require(declared["location_kind"] == "directory" and
                CONTRACT.plain_path(declared["location"]) == input_root and
                declared["recursive"] == case["recursive"], "Candidate declares a different discovery location or recursion policy.")
        if manifest:
            expected_sources = {str(value["path"]): value["sha256"] for value in sources.values()}
            actual_sources = {
                str(CONTRACT.plain_path(source["locator"])): source["identity"]["value"]
                for source in manifest["sources"] if source["identity"]["kind"] == "sha256"
            }
            require(len(actual_sources) == len(manifest["sources"]) and actual_sources == expected_sources,
                    "Selected source inventory differs from the case-defined inputs.")
        add("declared_source_scope", "passed", "Candidate source declarations match the case-defined location and selected sources.")
        CONTRACT.validate(work_path, check_sources=manifest is not None)
        if manifest:
            expected_hashes.update({
                CONTRACT.local_file(manifest_path.parent, entry["file"]): entry["sha256"]
                for entry in [*manifest["chapters"], *manifest["assets"]]
            })
        add("package_contract", "passed", "Schemas, source bindings, paths, hashes, chapter files, and workflow states validated.")
    except (ValueError, OSError, UnicodeError) as exc:
        add("package_contract", "failed", str(exc))
        manifest = None
    if isinstance(work, dict):
        legacy = CONTRACT.legacy_metadata(work)
        comparable_metadata = legacy | work["metadata"]
        if "edition" in case["expected_metadata"] and not isinstance(case["expected_metadata"]["edition"], dict):
            comparable_metadata["edition"] = legacy["edition"]
        matches = {
            key: {"expected": value, "actual": comparable_metadata.get(key)}
            for key, value in case["expected_metadata"].items()
            if comparable_metadata.get(key) != value
        }
        add("metadata", "failed" if matches else "passed", matches or "Expected work metadata matches.")
        actual_status = work.get("preparation", {}).get("status")
        add("preparation_status", "passed" if actual_status == case["expected_preparation_status"] else "failed",
            {"expected": case["expected_preparation_status"], "actual": actual_status})
        workflow_mismatches = {
            name: {key: {"expected": value, "actual": work["workflows"][name].get(key)}
                   for key, value in expected.items() if work["workflows"][name].get(key) != value}
            for name, expected in case["expected_workflows"].items()
        }
        workflow_mismatches = {name: values for name, values in workflow_mismatches.items() if values}
        add("downstream_ownership", "failed" if workflow_mismatches else "passed",
            workflow_mismatches or "Downstream states match the case's freshness/preservation expectations.")
    package_files = [work_path]
    if manifest is not None:
        package_files.append(manifest_path)
        units, chapters = reference["units"], manifest["chapters"]
        add("scope", "passed" if manifest["scope"]["kind"] == case["scope_kind"] else "failed",
            {"expected": case["scope_kind"], "actual": manifest["scope"]["kind"]})
        add("unit_count", "passed" if len(chapters) == len(units) else "failed",
            {"expected": len(units), "actual": len(chapters)})
        structure_ok, content_ok = True, True
        counts_ok, source_text_ok = True, True
        all_actual_blocks = []
        expected_assets = {asset["resolved_file"]: asset["sha256"] for asset in reference["assets"]}
        actual_assets = {
            CONTRACT.local_file(manifest_path.parent, asset["file"]): asset["sha256"]
            for asset in manifest["assets"]
        }
        for index, (unit, chapter) in enumerate(zip(units, chapters), 1):
            path = CONTRACT.local_file(manifest_path.parent, chapter["file"])
            package_files.append(path)
            expected = canonical_markdown(unit["resolved_file"].read_text(encoding="utf-8"), reference["profile"],
                                          asset_resolver(unit["resolved_file"], expected_assets))
            result = {"unit_id": unit["unit_id"], "order": index, "candidate_file": chapter["file"]}
            identity_ok = all(chapter.get(key) == unit.get(key) for key in ("title", "source_number", "role"))
            structure_ok &= identity_ok
            try:
                actual = canonical_markdown(path.read_text(encoding="utf-8"), reference["profile"],
                                            asset_resolver(path, actual_assets))
                result.update(differences(expected["blocks"], actual["blocks"]))
                result["content_matches"] = expected["blocks"] == actual["blocks"]
                result["structure_matches"] = expected["structure"] == actual["structure"] and identity_ok
                all_actual_blocks.extend(actual["blocks"])
                if ground_truth:
                    actual_stats = visible_statistics(actual["blocks"])
                    truth_stats = ground_truth["units"][index - 1]["statistics"]
                    result["source_statistics"] = {"expected": truth_stats, "actual": actual_stats}
                    counts_ok &= all(actual_stats[key] == truth_stats[key]
                                     for key in ("nonempty_paragraphs", "characters_excluding_whitespace"))
                    source_text_ok &= actual_stats == truth_stats
            except ValueError as exc:
                result.update(content_matches=False, structure_matches=False, error=str(exc))
                counts_ok = source_text_ok = False
            structure_ok &= result["structure_matches"]
            content_ok &= result["content_matches"]
            report["chapters"].append(result)
        complete = len(units) == len(chapters)
        add("chapter_boundaries_and_structure", "passed" if structure_ok and complete else "failed",
            "Compared source-order titles, source numbers, roles, headings, and configured Markdown structure.")
        add("content_preservation", "passed" if content_ok and complete else "failed",
            "Compared ordered paragraph/content blocks using the case's Markdown profile; see per-unit diagnostics.")
        if ground_truth:
            report["source_statistics"] = {
                "expected": ground_truth["totals"]["whole_document"],
                "actual": visible_statistics(all_actual_blocks),
            }
            add("source_character_and_paragraph_counts", "passed" if counts_ok and complete else "failed",
                report["source_statistics"])
            add("source_text_fingerprints", "passed" if source_text_ok and complete else "failed",
                "Compared each unit's whitespace-excluded text and ordered-paragraph fingerprints to the fixed source baseline.")
        assets = manifest["assets"]
        package_files.extend(CONTRACT.local_file(manifest_path.parent, asset["file"]) for asset in assets)
        add("asset_inventory", "passed" if sorted(set(actual_assets.values())) == sorted(set(expected_assets.values())) else "failed",
            "Compared declared asset content hashes and image references independently of asset filenames.")
    elif case["expected_preparation_status"] == "ready":
        add("content_preservation", "not_checked", "A valid prepared revision is required for content comparison.")
    fingerprint = hashlib.sha256()
    for path in sorted(set(package_files)):
        if path.is_file():
            fingerprint.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
            fingerprint.update(digest(path).encode())
    report["candidate_fingerprint"] = fingerprint.hexdigest()
    if trace_path is None:
        add("observed_access_scope", "not_checked", "No trusted harness access trace was supplied.", case["require_trace"])
    else:
        try:
            trace = read_json(CONTRACT.plain_path(trace_path))
            require(isinstance(trace, dict), "Trace must be an object.")
            require(not CONTRACT.plain_path(trace_path).is_relative_to(root), "Harness evidence must be stored outside candidate output.")
            require(trace.get("case_id") == case["case_id"] and trace.get("producer") == "harness"
                    and trace.get("complete") is True and trace.get("candidate_fingerprint") == report["candidate_fingerprint"],
                    "Trace must be a complete, case- and candidate-bound harness record.")
            require(trace.get("case_sha256") == report["case_sha256"], "Trace was recorded for a different case definition.")
            require(isinstance(trace.get("events"), list) and trace["events"], "Trace contains no source-access events.")
            read_sources = set()
            for event in trace["events"]:
                require(isinstance(event, dict) and event.get("operation") in {"read", "write"}
                        and isinstance(event.get("path"), str) and Path(event["path"]).is_absolute(),
                        "Invalid source-access event.")
                path = CONTRACT.plain_path(event["path"])
                if event["operation"] == "read":
                    allowed_source = path == input_root or (
                        path.is_relative_to(input_root) and (case["recursive"] or path.parent == input_root)
                    )
                    require(allowed_source or path.is_relative_to(root), "Trace includes an out-of-scope data read.")
                    read_sources.add(path)
                else:
                    require(path.is_relative_to(root), "Trace includes a write outside candidate output.")
            if case["expected_preparation_status"] == "ready":
                require({s["path"] for s in sources.values()} <= read_sources, "Trace omits a selected source read.")
            add("observed_access_scope", "passed", "Supplied trusted harness trace records only permitted data access.")
        except (ValueError, OSError, KeyError, TypeError) as exc:
            add("observed_access_scope", "failed", str(exc), case["require_trace"])
    manual = case["manual_checks"]
    if manual:
        if visual_review_path is None:
            add("visual_review", "not_checked", {"missing_checks": manual})
        else:
            try:
                receipt = read_json(CONTRACT.plain_path(visual_review_path))
                require(isinstance(receipt, dict), "Review receipt must be an object.")
                require(not CONTRACT.plain_path(visual_review_path).is_relative_to(root), "Review evidence must be outside candidate output.")
                require(receipt.get("case_id") == case["case_id"] and
                        receipt.get("candidate_fingerprint") == report["candidate_fingerprint"]
                        and isinstance(receipt.get("reviewer"), str) and receipt["reviewer"].strip()
                        and isinstance(receipt.get("reviewed_at"), str)
                        and FormatChecker().conforms(receipt["reviewed_at"], "date-time"),
                        "Visual review is missing identity or candidate binding.")
                require(receipt.get("case_sha256") == report["case_sha256"]
                        and receipt.get("reference_sha256") == report["reference_sha256"],
                        "Visual review was recorded for a different case or reference revision.")
                require(isinstance(receipt.get("checks"), dict)
                        and all(receipt["checks"].get(name) == "passed" for name in manual),
                        "Required visual checks are missing or failed.")
                add("visual_review", "passed", "Supplied reviewer receipt covers the required visual checks.")
            except (ValueError, OSError, TypeError) as exc:
                add("visual_review", "failed", str(exc))
    try:
        stable = all(digest(CONTRACT.plain_path(path)) == expected for path, expected in expected_hashes.items())
    except (ValueError, OSError):
        stable = False
    add("inputs_stable", "passed" if stable else "failed",
        "Checked source, candidate, and reference hashes again before finalizing the report.")
    report["status"] = (
        "failed" if any(check["status"] == "failed" for check in checks)
        else "incomplete" if any(check["required"] and check["status"] != "passed" for check in checks)
        else "passed"
    )
    report["summary"] = {
        "checks_passed": sum(check["status"] == "passed" for check in checks),
        "checks_failed": sum(check["status"] == "failed" for check in checks),
        "checks_not_checked": sum(check["status"] == "not_checked" for check in checks),
        "units_expected": len(reference["units"]), "units_compared": len(report["chapters"]),
        "units_content_matched": sum(unit["content_matches"] for unit in report["chapters"]),
    }
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, help="Preparation evaluation case ID.")
    parser.add_argument("--data-dir", type=Path, default=ROOT)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--work", type=Path, help="Candidate prepared package's work.json.")
    selection.add_argument("--check-reference", action="store_true")
    parser.add_argument("--trace", type=Path, help="Trusted harness data-access trace.")
    parser.add_argument("--visual-review", type=Path, help="Candidate-bound human review receipt.")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    try:
        require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.case), "Invalid case ID.")
        root = CONTRACT.plain_path(args.data_dir)
        case_path = root / "cases/prepare-manuscript" / args.case / "case.json"
        if args.check_reference:
            case, reference, sources, _, _ = load_case(case_path, root)
            require(all(digest(source["path"]) == source["sha256"] for source in sources.values()), "Fixture source hash mismatch.")
            print(f"Reference valid: {case['case_id']}; {len(reference['units'])} units; review status: {reference['review']['status']}")
            if reference.get("ground_truth"):
                truth = reference["ground_truth"]
                print(f"Frozen source ground truth verified: {truth['totals']['whole_document']['characters_excluding_whitespace']} non-whitespace characters.")
            print("No candidate was evaluated. Source facts are frozen; Markdown presentation approval is separate."
                  if reference.get("ground_truth") else
                  "No candidate was evaluated. A draft reference is not approved ground truth.")
            return 0
        report = evaluate(case_path, args.work, eval_root=root, trace_path=args.trace, visual_review_path=args.visual_review)
        output = CONTRACT.plain_path(root / "results" / ("preparation-" + uuid.uuid4().hex[:12]))
        output.mkdir(parents=True)
        (output / "evaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{report['status']}: {report['case_id']}")
        for check in report["checks"]:
            print(f"{check['status']:>11}  {check['check']}")
            if check["status"] != "passed":
                print("             " + json.dumps(check["detail"], ensure_ascii=False)[:500])
        print(f"Report: {output / 'evaluation.json'}")
        return {"passed": 0, "failed": 1, "incomplete": 2}[report["status"]]
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as exc:
        print(f"check-preparation: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
