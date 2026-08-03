#!/usr/bin/env python3
"""Validate, render, and parse revision-bound interactive approval sheets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
MAX_FRAGMENT_BYTES = 2 * 1024 * 1024
SHEET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
ITEM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
DECISION_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
ITEM_STATUSES = {"pending", "resolved", "reopened"}
DECISION_EFFECTS = {"resolve", "reopen", "clear"}
FINAL_CLOSURES = {"not-required", "pending", "confirmed"}
PRESENTATION_MODES = {"all", "open-only"}


class ApprovalError(ValueError):
    """Raised when approval state or a response is invalid."""


def load_sheet(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ApprovalError(f"Sheet not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ApprovalError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ApprovalError("The approval sheet root must be an object.")
    return data


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_labeled_rows(value: Any, path: str, errors: list[str], minimum: int = 1) -> None:
    if not isinstance(value, list) or len(value) < minimum:
        errors.append(f"{path} must be an array with at least {minimum} row(s).")
        return
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            errors.append(f"{path}[{index}] must be an object.")
            continue
        if not _nonempty_string(row.get("label")):
            errors.append(f"{path}[{index}].label must be a nonempty string.")
        if not _nonempty_string(row.get("value")):
            errors.append(f"{path}[{index}].value must be a nonempty string.")


def validate_sheet(sheet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if sheet.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}.")

    sheet_id = sheet.get("sheet_id")
    if not _nonempty_string(sheet_id) or not SHEET_ID_RE.fullmatch(sheet_id):
        errors.append("sheet_id must match [A-Za-z0-9][A-Za-z0-9._:-]{0,127}.")

    if not _nonempty_string(sheet.get("revision")):
        errors.append("revision must be a nonempty string.")
    if not _nonempty_string(sheet.get("title")):
        errors.append("title must be a nonempty string.")

    _validate_labeled_rows(sheet.get("bindings"), "bindings", errors)

    decisions = sheet.get("decisions")
    decision_by_id: dict[str, dict[str, Any]] = {}
    command_keys: set[str] = set()
    if not isinstance(decisions, list) or len(decisions) < 2:
        errors.append("decisions must be an array with at least two definitions.")
        decisions = []
    for index, decision in enumerate(decisions):
        path = f"decisions[{index}]"
        if not isinstance(decision, dict):
            errors.append(f"{path} must be an object.")
            continue
        decision_id = decision.get("id")
        if not _nonempty_string(decision_id) or not DECISION_ID_RE.fullmatch(decision_id):
            errors.append(f"{path}.id must be a lowercase machine ID.")
        elif decision_id in decision_by_id:
            errors.append(f"Duplicate decision id: {decision_id}.")
        else:
            decision_by_id[decision_id] = decision
        command = decision.get("command")
        if not _nonempty_string(command) or ":" in command or "\n" in command or "\r" in command:
            errors.append(f"{path}.command must be nonempty and contain no colon or newline.")
        else:
            command_key = command.casefold()
            if command_key in command_keys:
                errors.append(f"Duplicate decision command: {command}.")
            command_keys.add(command_key)
        if not _nonempty_string(decision.get("label")):
            errors.append(f"{path}.label must be a nonempty string.")
        if not isinstance(decision.get("requires_note"), bool):
            errors.append(f"{path}.requires_note must be boolean.")
        if decision.get("effect") not in DECISION_EFFECTS:
            errors.append(f"{path}.effect must be resolve, reopen, or clear.")

    items = sheet.get("items")
    item_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(items, list) or not items:
        errors.append("items must be a nonempty array.")
        items = []
    for index, item in enumerate(items):
        path = f"items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path} must be an object.")
            continue
        item_id = item.get("id")
        if not _nonempty_string(item_id) or not ITEM_ID_RE.fullmatch(item_id):
            errors.append(f"{path}.id must be a stable 1-64 character ID.")
        elif item_id in item_by_id:
            errors.append(f"Duplicate item id: {item_id}.")
        else:
            item_by_id[item_id] = item
        if not _nonempty_string(item.get("summary")):
            errors.append(f"{path}.summary must be a nonempty string.")
        _validate_labeled_rows(item.get("details"), f"{path}.details", errors)
        status = item.get("status")
        if status not in ITEM_STATUSES:
            errors.append(f"{path}.status must be pending, resolved, or reopened.")
        if not _nonempty_string(item.get("status_label")):
            errors.append(f"{path}.status_label must be a nonempty string.")
        allowed = item.get("allowed_decisions")
        if not isinstance(allowed, list) or not allowed:
            errors.append(f"{path}.allowed_decisions must be a nonempty array.")
            allowed = []
        comparable_allowed = [value for value in allowed if isinstance(value, str)]
        if len(set(comparable_allowed)) != len(comparable_allowed):
            errors.append(f"{path}.allowed_decisions contains duplicates.")
        for decision_id in allowed:
            if not _nonempty_string(decision_id):
                errors.append(f"{path}.allowed_decisions entries must be nonempty strings.")
            elif decision_id not in decision_by_id:
                errors.append(f"{path}.allowed_decisions references unknown decision {decision_id!r}.")
        dependencies = item.get("dependencies")
        if not isinstance(dependencies, list) or any(not _nonempty_string(value) for value in dependencies):
            errors.append(f"{path}.dependencies must be an array of nonempty strings.")
        if status == "reopened" and not _nonempty_string(item.get("reopened_reason")):
            errors.append(f"{path}.reopened_reason is required for reopened items.")
        response = item.get("response")
        if status == "resolved":
            if not isinstance(response, dict):
                errors.append(f"{path}.response is required for resolved items.")
            else:
                response_decision = response.get("decision")
                definition = decision_by_id.get(response_decision)
                if response_decision not in allowed:
                    errors.append(f"{path}.response.decision is not allowed for this item.")
                if definition and definition.get("effect") != "resolve":
                    errors.append(f"{path}.response.decision must have effect resolve.")
                note = response.get("note")
                if not isinstance(note, str):
                    errors.append(f"{path}.response.note must be a string.")
                elif definition and definition.get("requires_note") and not note.strip():
                    errors.append(f"{path}.response.note is required for {response_decision}.")
                if not _nonempty_string(response.get("date")):
                    errors.append(f"{path}.response.date must be a nonempty string.")
        elif response is not None:
            errors.append(f"{path}.response must be null while the item is pending or reopened.")

    gate = sheet.get("gate")
    if not isinstance(gate, dict):
        errors.append("gate must be an object.")
        gate = {}
    if not _nonempty_string(gate.get("status")):
        errors.append("gate.status must be a nonempty string.")
    closure_required = gate.get("closure_required")
    if not isinstance(closure_required, bool):
        errors.append("gate.closure_required must be boolean.")
    final_closure = gate.get("final_closure")
    if final_closure not in FINAL_CLOSURES:
        errors.append("gate.final_closure must be not-required, pending, or confirmed.")
    if closure_required is False and final_closure != "not-required":
        errors.append("gate.final_closure must be not-required when closure_required is false.")
    if closure_required is True and final_closure == "not-required":
        errors.append("gate.final_closure cannot be not-required when closure_required is true.")
    if final_closure == "confirmed" and any(item.get("status") != "resolved" for item in items if isinstance(item, dict)):
        errors.append("Final closure cannot be confirmed while any item is unresolved.")
    if not _nonempty_string(gate.get("ready_state")):
        errors.append("gate.ready_state must be a nonempty string.")

    presentation = sheet.get("presentation")
    if not isinstance(presentation, dict):
        errors.append("presentation must be an object.")
        presentation = {}
    if presentation.get("mode") not in PRESENTATION_MODES:
        errors.append("presentation.mode must be all or open-only.")
    for field in ("note_label", "note_placeholder", "submit_label"):
        if not _nonempty_string(presentation.get(field)):
            errors.append(f"presentation.{field} must be a nonempty string.")

    submission = sheet.get("submission")
    if not isinstance(submission, dict):
        errors.append("submission must be an object.")
        submission = {}
    for field in ("instruction", "closure_command", "closure_label"):
        if not _nonempty_string(submission.get(field)):
            errors.append(f"submission.{field} must be a nonempty string.")
    closure_command = submission.get("closure_command")
    if isinstance(closure_command, str) and (":" in closure_command or "\n" in closure_command or "\r" in closure_command):
        errors.append("submission.closure_command must contain no colon or newline.")
    if isinstance(closure_command, str) and closure_command.casefold() in command_keys:
        errors.append("submission.closure_command must differ from every decision command.")
    rules = submission.get("rules")
    if not isinstance(rules, list) or any(not _nonempty_string(rule) for rule in rules):
        errors.append("submission.rules must be an array of nonempty strings.")

    if errors:
        raise ApprovalError("Approval sheet validation failed:\n- " + "\n- ".join(errors))

    return {
        "sheet_id": sheet["sheet_id"],
        "revision": sheet["revision"],
        "items": len(items),
        "resolved": sum(item["status"] == "resolved" for item in items),
        "open": sum(item["status"] != "resolved" for item in items),
        "decisions": len(decisions),
        "closure_eligible": (
            bool(gate["closure_required"])
            and gate["final_closure"] == "pending"
            and all(item["status"] == "resolved" for item in items)
        ),
    }


def _template_path() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "approval-review-template.html"


def render_sheet(sheet: dict[str, Any], output_path: Path) -> dict[str, Any]:
    summary = validate_sheet(sheet)
    template_path = _template_path()
    try:
        template = template_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ApprovalError(f"Template not found: {template_path}") from exc
    if template.count("__ROOT_ID__") < 2 or template.count("__SHEET_JSON__") != 1:
        raise ApprovalError("Template placeholders are missing or ambiguous.")
    lowered_template = template.casefold()
    forbidden = ("<!doctype", "<html", "<head", "<body", "fetch(", "xmlhttprequest", "websocket", "document.currentscript")
    found = [token for token in forbidden if token in lowered_template]
    if found:
        raise ApprovalError("Template contains forbidden content: " + ", ".join(found))

    digest = hashlib.sha256(f"{sheet['sheet_id']}\0{sheet['revision']}".encode("utf-8")).hexdigest()[:12]
    root_id = f"approval-review-{digest}"
    embedded = json.dumps(sheet, ensure_ascii=False, separators=(",", ":"))
    embedded = embedded.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    fragment = template.replace("__ROOT_ID__", root_id).replace("__SHEET_JSON__", embedded)

    if len(fragment.encode("utf-8")) > MAX_FRAGMENT_BYTES:
        raise ApprovalError("Generated fragment exceeds the 2 MB limit.")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(fragment, encoding="utf-8", newline="\n")
    return {**summary, "output": str(output_path), "bytes": len(fragment.encode("utf-8")), "root_id": root_id}


def _envelope_lines(sheet: dict[str, Any]) -> list[str]:
    return [
        sheet["submission"]["instruction"],
        f"Approval sheet: {sheet['sheet_id']}",
        f"Revision: {sheet['revision']}",
        *sheet["submission"]["rules"],
    ]


def _strip_envelope(sheet: dict[str, Any], text: str) -> list[str]:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        raise ApprovalError("Response contains no dispositions.")

    expected = _envelope_lines(sheet)
    if lines[0] == expected[0]:
        if len(lines) < len(expected) or lines[: len(expected)] != expected:
            raise ApprovalError("The approval envelope identity, revision, instruction, or rules do not match the sheet.")
        lines = lines[len(expected) :]
        while lines and not lines[0].strip():
            lines.pop(0)
    elif any(line.startswith("Approval sheet:") or line.startswith("Revision:") for line in lines):
        raise ApprovalError("Identity or revision lines are present without the exact generated envelope.")

    return [line.strip() for line in lines if line.strip()]


def parse_response(sheet: dict[str, Any], text: str) -> dict[str, Any]:
    validate_sheet(sheet)
    lines = _strip_envelope(sheet, text)
    closure_command = sheet["submission"]["closure_command"]
    if len(lines) == 1 and lines[0].casefold() == closure_command.casefold():
        if not sheet["gate"]["closure_required"] or sheet["gate"]["final_closure"] != "pending":
            raise ApprovalError("Final closure is not pending for this sheet.")
        if any(item["status"] != "resolved" for item in sheet["items"]):
            raise ApprovalError("Final closure is unavailable while items remain unresolved.")
        return {
            "schema_version": SCHEMA_VERSION,
            "type": "final-closure",
            "sheet_id": sheet["sheet_id"],
            "revision": sheet["revision"],
            "command": closure_command,
        }
    if any(line.casefold() == closure_command.casefold() for line in lines):
        raise ApprovalError("Final closure cannot be mixed with item dispositions.")

    decision_by_id = {decision["id"]: decision for decision in sheet["decisions"]}
    open_by_id = {item["id"]: item for item in sheet["items"] if item["status"] != "resolved"}
    all_ids = {item["id"] for item in sheet["items"]}
    dispositions: list[dict[str, Any]] = []
    seen: set[str] = set()

    for line in lines:
        matching_ids = [item_id for item_id in open_by_id if line.startswith(item_id + " ")]
        if not matching_ids:
            resolved_match = next((item_id for item_id in all_ids if line.startswith(item_id + " ")), None)
            if resolved_match:
                raise ApprovalError(f"{resolved_match} is already resolved and cannot be resubmitted.")
            raise ApprovalError(f"Unrecognized disposition line: {line}")
        item_id = max(matching_ids, key=len)
        if item_id in seen:
            raise ApprovalError(f"Duplicate disposition for {item_id}.")
        seen.add(item_id)
        item = open_by_id[item_id]
        remainder = line[len(item_id) + 1 :].strip()

        allowed = [decision_by_id[decision_id] for decision_id in item["allowed_decisions"]]
        allowed.sort(key=lambda decision: len(decision["command"]), reverse=True)
        selected: dict[str, Any] | None = None
        note = ""
        for decision in allowed:
            command = decision["command"]
            if remainder.casefold() == command.casefold():
                selected = decision
                break
            prefix = command + ":"
            if remainder[: len(prefix)].casefold() == prefix.casefold():
                selected = decision
                note = remainder[len(prefix) :].strip()
                break
        if selected is None:
            commands = ", ".join(decision["command"] for decision in allowed)
            raise ApprovalError(f"{item_id} must use one of: {commands}.")
        if selected["requires_note"] and not note:
            raise ApprovalError(f"{item_id} requires a note for {selected['command']}.")
        dispositions.append(
            {
                "item_id": item_id,
                "decision": selected["id"],
                "command": selected["command"],
                "effect": selected["effect"],
                "note": note,
            }
        )

    if not dispositions:
        raise ApprovalError("Response contains no item dispositions.")
    return {
        "schema_version": SCHEMA_VERSION,
        "type": "dispositions",
        "sheet_id": sheet["sheet_id"],
        "revision": sheet["revision"],
        "dispositions": dispositions,
    }


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate an approval-sheet JSON file.")
    validate_parser.add_argument("sheet", type=Path)

    render_parser = subparsers.add_parser("render", help="Render a validated sheet as an HTML fragment.")
    render_parser.add_argument("sheet", type=Path)
    render_parser.add_argument("output", type=Path)

    parse_parser = subparsers.add_parser("parse", help="Parse and validate a disposition payload.")
    parse_parser.add_argument("sheet", type=Path)
    parse_parser.add_argument("response", type=Path)
    parse_parser.add_argument("--output", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        sheet = load_sheet(args.sheet)
        if args.command == "validate":
            result = validate_sheet(sheet)
        elif args.command == "render":
            result = render_sheet(sheet, args.output)
        else:
            try:
                response_text = args.response.read_text(encoding="utf-8")
            except FileNotFoundError as exc:
                raise ApprovalError(f"Response not found: {args.response}") from exc
            result = parse_response(sheet, response_text)
            if args.output:
                _write_json(args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ApprovalError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
