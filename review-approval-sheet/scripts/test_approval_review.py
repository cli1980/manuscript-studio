#!/usr/bin/env python3
"""Regression tests for the shared approval-review contract and renderer."""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import approval_review


def decision(
    decision_id: str,
    command: str,
    label: str,
    requires_note: bool,
    effect: str,
) -> dict:
    return {
        "id": decision_id,
        "command": command,
        "label": label,
        "requires_note": requires_note,
        "effect": effect,
    }


def item(item_id: str, allowed: list[str], status: str = "pending") -> dict:
    result = {
        "id": item_id,
        "section": "Section",
        "summary": f"Review {item_id}.",
        "details": [
            {"label": "Current", "value": "Current text."},
            {"label": "Proposed", "value": "Proposed text."},
        ],
        "status": status,
        "status_label": status.title(),
        "allowed_decisions": allowed,
        "dependencies": [],
        "response": None,
    }
    if status == "reopened":
        result["reopened_reason"] = "An upstream decision changed."
    if status == "resolved":
        result["response"] = {"decision": allowed[0], "note": "", "date": "2026-08-02"}
    return result


def make_sheet(domain: str = "query", count: int = 3) -> dict:
    if domain == "query":
        decisions = [
            decision("approve", "approve", "Approve", False, "resolve"),
            decision("qualify", "qualify", "Qualify", True, "resolve"),
            decision("correct", "correct", "Correct", True, "reopen"),
            decision("keep-ambiguous", "keep ambiguous", "Keep ambiguous", False, "resolve"),
        ]
        allowed = [entry["id"] for entry in decisions]
        prefix = "HG"
        closure_required = True
    elif domain == "editing":
        decisions = [
            decision("accept", "accept", "Accept", False, "resolve"),
            decision("modify", "accept with modification", "Modify", True, "resolve"),
            decision("reject", "reject", "Reject", False, "resolve"),
            decision("defer", "defer", "Defer", False, "resolve"),
            decision("revise", "revise proposal", "Revise proposal", True, "reopen"),
        ]
        allowed = [entry["id"] for entry in decisions]
        prefix = "LE-"
        closure_required = False
    else:
        decisions = [
            decision("option-a", "choose option A", "Option A", False, "resolve"),
            decision("option-b", "choose option B", "Option B", False, "resolve"),
            decision("replacement", "replacement wording", "Replacement", True, "resolve"),
            decision("reopen", "reopen issue", "Reopen", True, "reopen"),
        ]
        allowed = [entry["id"] for entry in decisions]
        prefix = "TR-"
        closure_required = False

    items = []
    for number in range(1, count + 1):
        if prefix == "HG":
            item_id = f"HG{number:03d}"
        else:
            item_id = f"{prefix}{number:03d}"
        items.append(item(item_id, allowed))

    return {
        "schema_version": "1.0",
        "sheet_id": f"{domain}-review",
        "revision": "rev-1",
        "title": f"{domain.title()} review",
        "bindings": [
            {"label": "Source", "value": "source-sha"},
            {"label": "Review", "value": "review-rev-1"},
        ],
        "decisions": decisions,
        "items": items,
        "gate": {
            "status": "open",
            "closure_required": closure_required,
            "final_closure": "pending" if closure_required else "not-required",
            "ready_state": "not-ready",
        },
        "presentation": {
            "mode": "open-only",
            "note_label": "Comment or replacement",
            "note_placeholder": "Required for revisions",
            "submit_label": "Send reviewed items to Codex",
        },
        "submission": {
            "instruction": "Apply these explicit dispositions to the bound domain record.",
            "rules": ["Treat every enumerated item independently."],
            "closure_command": "confirm final closure",
            "closure_label": "Confirm final closure",
        },
    }


def envelope(sheet: dict, disposition_lines: list[str]) -> str:
    return "\n".join(
        [
            sheet["submission"]["instruction"],
            f"Approval sheet: {sheet['sheet_id']}",
            f"Revision: {sheet['revision']}",
            *sheet["submission"]["rules"],
            "",
            *disposition_lines,
        ]
    )


class SchemaTests(unittest.TestCase):
    def test_three_domain_profiles_validate(self) -> None:
        for domain in ("query", "editing", "translation"):
            with self.subTest(domain=domain):
                summary = approval_review.validate_sheet(make_sheet(domain))
                self.assertEqual(summary["items"], 3)
                self.assertEqual(summary["open"], 3)

    def test_duplicate_item_id_is_rejected(self) -> None:
        sheet = make_sheet()
        sheet["items"].append(copy.deepcopy(sheet["items"][0]))
        with self.assertRaisesRegex(approval_review.ApprovalError, "Duplicate item id"):
            approval_review.validate_sheet(sheet)

    def test_duplicate_command_case_insensitive_is_rejected(self) -> None:
        sheet = make_sheet()
        sheet["decisions"][1]["command"] = "APPROVE"
        with self.assertRaisesRegex(approval_review.ApprovalError, "Duplicate decision command"):
            approval_review.validate_sheet(sheet)

    def test_closure_command_cannot_duplicate_decision_command(self) -> None:
        sheet = make_sheet()
        sheet["submission"]["closure_command"] = "approve"
        with self.assertRaisesRegex(approval_review.ApprovalError, "must differ"):
            approval_review.validate_sheet(sheet)

    def test_reopened_item_requires_reason(self) -> None:
        sheet = make_sheet()
        sheet["items"][0]["status"] = "reopened"
        with self.assertRaisesRegex(approval_review.ApprovalError, "reopened_reason"):
            approval_review.validate_sheet(sheet)

    def test_resolved_item_requires_resolving_response(self) -> None:
        sheet = make_sheet()
        sheet["items"][0]["status"] = "resolved"
        sheet["items"][0]["response"] = {
            "decision": "correct",
            "note": "Change it.",
            "date": "2026-08-02",
        }
        with self.assertRaisesRegex(approval_review.ApprovalError, "effect resolve"):
            approval_review.validate_sheet(sheet)

    def test_confirmed_closure_with_open_item_is_rejected(self) -> None:
        sheet = make_sheet()
        sheet["gate"]["final_closure"] = "confirmed"
        with self.assertRaisesRegex(approval_review.ApprovalError, "cannot be confirmed"):
            approval_review.validate_sheet(sheet)

    def test_malformed_allowed_decision_is_reported_not_crashed(self) -> None:
        sheet = make_sheet()
        sheet["items"][0]["allowed_decisions"] = [{"bad": "value"}]
        with self.assertRaises(approval_review.ApprovalError):
            approval_review.validate_sheet(sheet)


class ParseTests(unittest.TestCase):
    def test_disposition_only_payload(self) -> None:
        sheet = make_sheet()
        result = approval_review.parse_response(
            sheet,
            "HG001 approve\nHG002 qualify: Preserve uncertainty\nHG003 correct: Use green eyes",
        )
        self.assertEqual(result["type"], "dispositions")
        self.assertEqual(len(result["dispositions"]), 3)
        self.assertEqual(result["dispositions"][2]["effect"], "reopen")

    def test_full_envelope_payload(self) -> None:
        sheet = make_sheet("editing")
        text = envelope(
            sheet,
            [
                "LE-001 accept",
                "LE-002 accept with modification: Keep the semicolon.",
                "LE-003 reject",
            ],
        )
        result = approval_review.parse_response(sheet, text)
        self.assertEqual([row["decision"] for row in result["dispositions"]], ["accept", "modify", "reject"])

    def test_longest_command_wins(self) -> None:
        sheet = make_sheet("editing", 1)
        result = approval_review.parse_response(sheet, "LE-001 accept with modification: Exact wording")
        self.assertEqual(result["dispositions"][0]["decision"], "modify")

    def test_required_note_is_enforced(self) -> None:
        sheet = make_sheet()
        with self.assertRaisesRegex(approval_review.ApprovalError, "requires a note"):
            approval_review.parse_response(sheet, "HG001 correct")

    def test_duplicate_id_is_rejected(self) -> None:
        sheet = make_sheet()
        with self.assertRaisesRegex(approval_review.ApprovalError, "Duplicate disposition"):
            approval_review.parse_response(sheet, "HG001 approve\nHG001 approve")

    def test_blanket_approval_is_rejected(self) -> None:
        sheet = make_sheet()
        with self.assertRaisesRegex(approval_review.ApprovalError, "Unrecognized disposition"):
            approval_review.parse_response(sheet, "approve all")

    def test_unknown_id_is_rejected(self) -> None:
        sheet = make_sheet()
        with self.assertRaisesRegex(approval_review.ApprovalError, "Unrecognized disposition"):
            approval_review.parse_response(sheet, "HG999 approve")

    def test_resolved_item_cannot_be_resubmitted(self) -> None:
        sheet = make_sheet(count=1)
        sheet["items"][0]["status"] = "resolved"
        sheet["items"][0]["response"] = {"decision": "approve", "note": "", "date": "2026-08-02"}
        with self.assertRaisesRegex(approval_review.ApprovalError, "already resolved"):
            approval_review.parse_response(sheet, "HG001 approve")

    def test_stale_revision_envelope_is_rejected(self) -> None:
        sheet = make_sheet()
        text = envelope(sheet, ["HG001 approve"]).replace("Revision: rev-1", "Revision: rev-0")
        with self.assertRaisesRegex(approval_review.ApprovalError, "do not match"):
            approval_review.parse_response(sheet, text)

    def test_closure_blocked_while_open(self) -> None:
        sheet = make_sheet()
        with self.assertRaisesRegex(approval_review.ApprovalError, "unresolved"):
            approval_review.parse_response(sheet, "confirm final closure")

    def test_valid_separate_closure(self) -> None:
        sheet = make_sheet(count=2)
        for row in sheet["items"]:
            row["status"] = "resolved"
            row["status_label"] = "Approved"
            row["response"] = {"decision": "approve", "note": "", "date": "2026-08-02"}
        result = approval_review.parse_response(sheet, envelope(sheet, ["confirm final closure"]))
        self.assertEqual(result["type"], "final-closure")

    def test_closure_cannot_mix_with_dispositions(self) -> None:
        sheet = make_sheet()
        with self.assertRaisesRegex(approval_review.ApprovalError, "cannot be mixed"):
            approval_review.parse_response(sheet, "HG001 approve\nconfirm final closure")


class RenderTests(unittest.TestCase):
    def render(self, sheet: dict) -> tuple[dict, str]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name) / "review.html"
        summary = approval_review.render_sheet(sheet, output)
        return summary, output.read_text(encoding="utf-8")

    def test_fragment_contract_and_unicode(self) -> None:
        sheet = make_sheet()
        sheet["items"][0]["details"][0]["value"] = "原文：她说“忘记我。”"
        summary, fragment = self.render(sheet)
        self.assertLess(summary["bytes"], approval_review.MAX_FRAGMENT_BYTES)
        self.assertTrue(fragment.startswith("<div "))
        self.assertNotIn("<!doctype", fragment.casefold())
        self.assertNotIn("<html", fragment.casefold())
        self.assertNotIn("fetch(", fragment.casefold())
        self.assertNotIn("document.currentscript", fragment.casefold())
        self.assertIn("原文", fragment)
        self.assertNotIn("__ROOT_ID__", fragment)
        self.assertNotIn("__SHEET_JSON__", fragment)

    def test_script_breakout_is_escaped(self) -> None:
        sheet = make_sheet()
        sheet["items"][0]["summary"] = "</script><script>bad()</script>"
        _, fragment = self.render(sheet)
        embedded_region = fragment.split('data-approval-data>', 1)[1].split("</script>", 1)[0]
        self.assertNotIn("</script>", embedded_region.casefold())
        self.assertIn("<\\/script>", embedded_region)

    def test_user_text_may_contain_quotes_markup_and_code_terms(self) -> None:
        sheet = make_sheet()
        sheet["items"][0]["details"][0]["value"] = 'She wrote "<html>" and said fetch() aloud.'
        _, fragment = self.render(sheet)
        self.assertIn('\\"<html>\\"', fragment)
        self.assertIn("fetch() aloud", fragment)
        self.assertTrue(fragment.startswith("<div "))

    def test_large_68_item_sheet(self) -> None:
        sheet = make_sheet(count=68)
        summary, fragment = self.render(sheet)
        self.assertEqual(summary["open"], 68)
        self.assertEqual(len(re.findall(r'"id":"HG\d{3}"', fragment)), 68)
        self.assertLess(len(fragment.encode("utf-8")), approval_review.MAX_FRAGMENT_BYTES)

    def test_final_closure_view_is_eligible_only_from_saved_state(self) -> None:
        sheet = make_sheet(count=2)
        for row in sheet["items"]:
            row["status"] = "resolved"
            row["status_label"] = "Approved"
            row["response"] = {"decision": "approve", "note": "", "date": "2026-08-02"}
        summary, fragment = self.render(sheet)
        self.assertTrue(summary["closure_eligible"])
        self.assertIn("data-closure-panel", fragment)
        self.assertIn("confirm final closure", fragment)

    def test_final_closure_takes_precedence_in_show_all_mode(self) -> None:
        sheet = make_sheet(count=2)
        sheet["presentation"]["mode"] = "all"
        for row in sheet["items"]:
            row["status"] = "resolved"
            row["status_label"] = "Approved"
            row["response"] = {"decision": "approve", "note": "", "date": "2026-08-02"}
        _, fragment = self.render(sheet)
        self.assertIn('if (!openItems.length && sheet.gate.closure_required', fragment)

    def test_generated_javascript_syntax(self) -> None:
        node = os.environ.get("NODE_BINARY")
        if not node:
            self.skipTest("NODE_BINARY not configured")
        _, fragment = self.render(make_sheet())
        scripts = re.findall(r"<script>\s*(.*?)\s*</script>", fragment, flags=re.DOTALL)
        self.assertEqual(len(scripts), 1)
        completed = subprocess.run(
            [node, "--check", "-"],
            input=scripts[0],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


class CliTests(unittest.TestCase):
    def test_validate_render_and_parse_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sheet_path = root / "sheet.json"
            response_path = root / "response.txt"
            output_path = root / "review.html"
            receipt_path = root / "receipt.json"
            sheet_path.write_text(json.dumps(make_sheet()), encoding="utf-8")
            response_path.write_text("HG001 approve", encoding="utf-8")

            self.assertEqual(approval_review.main(["validate", str(sheet_path)]), 0)
            self.assertEqual(approval_review.main(["render", str(sheet_path), str(output_path)]), 0)
            self.assertEqual(
                approval_review.main(
                    ["parse", str(sheet_path), str(response_path), "--output", str(receipt_path)]
                ),
                0,
            )
            self.assertTrue(output_path.exists())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["dispositions"][0]["item_id"], "HG001")


if __name__ == "__main__":
    unittest.main(verbosity=2)
