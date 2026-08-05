#!/usr/bin/env python3
"""Build and validate page-limited manuscript samples at natural boundaries."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_paragraphs(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n[ \t]*\n+", text)
    paragraphs: list[str] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        paragraph = " ".join(lines)
        paragraph = re.sub(r"^\s{0,3}#{1,6}\s*", "", paragraph)
        paragraph = paragraph.replace("**", "").replace("__", "")
        paragraph = normalize(paragraph)
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE))


def sentence_closed(paragraph: str) -> bool:
    tail = paragraph.rstrip()
    while tail and tail[-1] in "\"'\u201d\u2019)]}":
        tail = tail[:-1].rstrip()
    return bool(tail) and tail[-1] in ".?!\u2026"


def locate_cutoff(paragraphs: list[str], fragment: str) -> tuple[int, str]:
    needle = normalize(fragment)
    if not needle:
        raise ValueError("Cutoff fragment must not be empty.")
    matches: list[tuple[int, str]] = []
    for index, paragraph in enumerate(paragraphs):
        haystack = normalize(paragraph)
        position = haystack.find(needle)
        if position < 0:
            continue
        remainder = haystack[position + len(needle):].strip()
        matches.append((index, "paragraph-end" if not remainder else "mid-paragraph"))
    if not matches:
        raise ValueError("Cutoff fragment was not found in the source manuscript.")
    if len(matches) > 1:
        raise ValueError("Cutoff fragment is not unique in the source manuscript.")
    return matches[0]


def build_sample(source_text: str, cutoff_fragment: str, requested_pages: int) -> tuple[str, dict[str, Any]]:
    if requested_pages < 1:
        raise ValueError("Requested pages must be a positive integer.")
    paragraphs = clean_paragraphs(source_text)
    cutoff_index, cutoff_position = locate_cutoff(paragraphs, cutoff_fragment)
    include_count = cutoff_index + 1 if cutoff_position == "paragraph-end" else cutoff_index
    if include_count < 1:
        raise ValueError("The page cutoff occurs before any complete paragraph.")
    included = paragraphs[:include_count]
    final_paragraph = included[-1]
    validation = {
        "within_requested_page_limit": True,
        "complete_paragraph": cutoff_position == "paragraph-end" or include_count == cutoff_index,
        "complete_sentence": sentence_closed(final_paragraph),
        "source_prefix_exact": True,
    }
    validation["passed"] = all(validation.values())
    if not validation["passed"]:
        raise ValueError("The effective sample ending is not a complete sentence and paragraph.")
    sample = "\n\n".join(included).rstrip() + "\n"
    report: dict[str, Any] = {
        "schema_version": 1,
        "requested_pages": requested_pages,
        "physical_cutoff": {
            "paragraph_number": cutoff_index + 1,
            "position": cutoff_position,
            "fragment": normalize(cutoff_fragment),
        },
        "rollback_applied": cutoff_position == "mid-paragraph",
        "rollback_reason": (
            "Physical page cutoff intersects a paragraph; omitted that paragraph."
            if cutoff_position == "mid-paragraph"
            else "No rollback; physical cutoff is at a paragraph boundary."
        ),
        "effective_end": {
            "paragraph_number": include_count,
            "text": final_paragraph,
        },
        "sample_words": word_count(sample),
        "validation": validation,
    }
    return sample, report


def validate_sample(
    source_text: str,
    sample_text: str,
    requested_pages: int,
    boundary_report: dict[str, Any] | None,
) -> dict[str, Any]:
    source = clean_paragraphs(source_text)
    sample = clean_paragraphs(sample_text)
    prefix_exact = bool(sample) and len(sample) <= len(source) and sample == source[:len(sample)]
    complete_paragraph = prefix_exact
    complete_sentence = bool(sample) and sentence_closed(sample[-1])
    report_end = (boundary_report or {}).get("effective_end", {}).get("paragraph_number", 0)
    report_pages = (boundary_report or {}).get("requested_pages")
    report_passed = (boundary_report or {}).get("validation", {}).get("passed") is True
    within_limit = (
        report_pages == requested_pages
        and report_passed
        and bool(sample)
        and len(sample) <= report_end
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "requested_pages": requested_pages,
        "sample_paragraphs": len(sample),
        "sample_words": word_count(sample_text),
        "effective_end": sample[-1] if sample else "",
        "validation": {
            "within_requested_page_limit": within_limit,
            "complete_paragraph": complete_paragraph,
            "complete_sentence": complete_sentence,
            "source_prefix_exact": prefix_exact,
        },
    }
    result["validation"]["passed"] = all(result["validation"].values())
    return result


def write_json(path: Path | None, data: dict[str, Any]) -> None:
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("--source", type=Path, required=True)
    build.add_argument("--cutoff-fragment", required=True)
    build.add_argument("--requested-pages", type=int, required=True)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--source", type=Path, required=True)
    validate.add_argument("--sample", type=Path, required=True)
    validate.add_argument("--requested-pages", type=int, required=True)
    validate.add_argument("--boundary-report", type=Path, required=True)
    validate.add_argument("--report", type=Path)

    args = parser.parse_args()
    try:
        source_text = args.source.read_text(encoding="utf-8-sig")
        if args.command == "build":
            sample, report = build_sample(source_text, args.cutoff_fragment, args.requested_pages)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(sample, encoding="utf-8")
            write_json(args.report, report)
            return 0
        sample_text = args.sample.read_text(encoding="utf-8-sig")
        boundary_report = json.loads(args.boundary_report.read_text(encoding="utf-8-sig"))
        report = validate_sample(source_text, sample_text, args.requested_pages, boundary_report)
        write_json(args.report, report)
        return 0 if report["validation"]["passed"] else 1
    except (OSError, ValueError) as exc:
        sys.stderr.write("sample-boundary: " + str(exc) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
