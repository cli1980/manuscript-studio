"""Check the versioned UX inventory and local links; no browser or npm required."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
UX = ROOT / "docs/ux"
FLOW_NAME = re.compile(r"UF-(\d{2})-[a-z0-9-]+\.md")
LINK = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^)\s]+)\)")
FENCE = re.compile(r"^```[^\n]*\n.*?^```[ \t]*$", re.MULTILINE | re.DOTALL)
SECTIONS = (
    "Current flow", "Alternatives and recovery", "Target and open questions",
    "Acceptance checks", "Evidence",
)


def headings(path):
    text = FENCE.sub("", path.read_text(encoding="utf-8"))
    result, counts = set(), {}
    for heading in re.findall(r"^#{1,6}\s+(.+)$", text, re.MULTILINE):
        slug = re.sub(r"[^\w -]", "", heading.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(f"{slug}-{count}" if count else slug)
    return result


def check():
    errors = []
    documents = sorted(UX.rglob("*.md"))
    index = (UX / "README.md").read_text(encoding="utf-8")
    inventory = re.findall(r"^\| (UF-\d{2}) \|", index, re.MULTILINE)
    expected = set(inventory)
    if not inventory or len(inventory) != len(expected):
        errors.append("Flow inventory is empty or contains duplicate IDs")
    screen_inventory = re.findall(r"^\| (SC-\d{2}) \|", index, re.MULTILINE)
    expected_screens = set(screen_inventory)
    if not screen_inventory or len(screen_inventory) != len(expected_screens):
        errors.append("Screen inventory is empty or contains duplicate IDs")
    found, screens, diagrams = set(), set(), 0
    for path in documents:
        text = path.read_text(encoding="utf-8")
        if b"\r\n" in path.read_bytes():
            errors.append(f"{path.relative_to(ROOT)}: CRLF line endings")
        name = FLOW_NAME.fullmatch(path.name)
        if path.parent == UX / "flows" and name:
            flow_id = f"UF-{name[1]}"
            if flow_id in found:
                errors.append(f"Duplicate flow ID: {flow_id}")
            found.add(flow_id)
            if not text.startswith(f"# {flow_id} - "):
                errors.append(f"{path.name}: heading does not match ID")
            if f"(flows/{path.name})" not in index:
                errors.append(f"{flow_id}: absent from index")
            for section in SECTIONS:
                if f"## {section}\n" not in text:
                    errors.append(f"{flow_id}: missing {section}")
            if not re.search(r"^```mermaid\n.+?^```", text, re.MULTILINE | re.DOTALL):
                errors.append(f"{flow_id}: missing current-flow diagram")
        elif path.parent == UX / "flows" and path.name != "_template.md":
            errors.append(f"Unrecognized flow filename: {path.name}")
        if path.parent == UX / "screens":
            screen = re.match(r"# (SC-\d{2}) - ", text)
            if not screen:
                errors.append(f"{path.name}: missing screen ID")
            else:
                if screen[1] in screens:
                    errors.append(f"Duplicate screen ID: {screen[1]}")
                screens.add(screen[1])
            if f"(screens/{path.name})" not in index:
                errors.append(f"{path.name}: absent from screen index")
            for section in ("Current contract", "Target boundary", "Validation"):
                if f"## {section}\n" not in text:
                    errors.append(f"{path.name}: missing {section}")
        diagrams += len(re.findall(r"^```mermaid\s*$", text, re.MULTILINE))
        for link in LINK.findall(FENCE.sub("", text)):
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(ROOT):
                errors.append(f"{path.name}: link escapes repository: {link}")
            elif not target.exists():
                errors.append(f"{path.name}: missing link target: {link}")
            elif url.fragment and target.suffix == ".md" and unquote(url.fragment) not in headings(target):
                errors.append(f"{path.name}: missing heading: {link}")
    if found != expected:
        errors.append(f"Inventory mismatch: missing={sorted(expected-found)}, extra={sorted(found-expected)}")
    if screens != expected_screens:
        errors.append(f"Screen inventory mismatch: missing={sorted(expected_screens-screens)}, "
                      f"extra={sorted(screens-expected_screens)}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"UX specification checks passed: {len(found)} flows, {len(screens)} screens, "
          f"{len(documents)} Markdown documents, {diagrams} Mermaid diagrams.")
    return 0


if __name__ == "__main__":
    raise SystemExit(check())
