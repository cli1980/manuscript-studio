"""Authoring aid for this fixture's draft reference; never produces a candidate work package."""

import hashlib
import json
import os
import re
import string
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS = HERE.parents[2]
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"


def children(node):
    if node.tag == MC + "AlternateContent":
        choice = node.find(MC + "Choice")
        selected = choice if choice is not None else node.find(MC + "Fallback")
        return list(selected) if selected is not None else []
    if node.tag == W + "sdt":
        content = node.find(W + "sdtContent")
        return list(content) if content is not None else []
    return list(node)


def visible_text(node):
    if node.tag == W + "t":
        return node.text or ""
    if node.tag == W + "tab":
        return " "
    if node.tag in {W + "br", W + "cr"}:
        return "\n"
    return "".join(visible_text(child) for child in children(node))


def paragraphs(node):
    if node.tag == W + "p":
        yield node
    else:
        for child in children(node):
            yield from paragraphs(child)


def escape(text):
    return re.sub("([" + re.escape(string.punctuation) + "])", r"\\\1", text)


def main():
    case = json.loads((HERE / "case.json").read_text(encoding="utf-8"))
    existing = HERE / "reference-map.json"
    if existing.exists():
        review = json.loads(existing.read_text(encoding="utf-8"))["review"]
        if review["status"] == "approved":
            raise SystemExit("Refusing to regenerate an approved reference. Create and review a new reference revision.")
    source = (HERE / case["input_location"] / case["sources"][0]["file"]).resolve()
    if hashlib.sha256(source.read_bytes()).hexdigest() != case["sources"][0]["sha256"]:
        raise SystemExit("Source fixture hash changed; review the case definition before rebuilding its reference.")
    with zipfile.ZipFile(source) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
    units = [{"unit_id": "front-matter", "title": None, "source_number": None,
              "role": "front_matter", "body": [], "source_locator": "Cover content control and TOC before first ChineseHeading paragraph"}]
    chapter_count = 0
    for ordinal, paragraph in enumerate(paragraphs(document.find(W + "body")), 1):
        text = visible_text(paragraph)
        if not text.strip():
            continue
        style = paragraph.find(W + "pPr/" + W + "pStyle")
        style_id = style.get(W + "val") if style is not None else ""
        rendered = escape(text).replace("\n", "  \n")
        if style_id == "ChineseHeading":
            chapter_count += 1
            numbered = re.match(r"^([一二三四五六七八九十]+)、", text)
            units.append({
                "unit_id": f"body-unit-{chapter_count:02d}", "title": text,
                "source_number": numbered.group(1) if numbered else None,
                "role": "back_matter" if text.startswith("附录") or text == "后记" else "chapter",
                "source_locator": f"word/document.xml logical paragraph {ordinal}: {text}; through next ChineseHeading or EOF",
                "body": ["# " + rendered],
            })
        elif style_id in {"ChineseDiary", "ChineseQuote"}:
            units[-1]["body"].append("\n".join("> " + line for line in rendered.split("\n")))
        else:
            units[-1]["body"].append(rendered)
    if chapter_count != 22:
        raise SystemExit(f"Unexpected chapter heading inventory: {chapter_count}; review boundaries manually.")
    output = EVALS / "fixtures/reference-outputs/prepare-manuscript/docx-novel-001"
    output.mkdir(parents=True, exist_ok=True)
    reference_units = []
    for number, unit in enumerate(units, 1):
        raw = ("\n\n".join(unit.pop("body")) + "\n").encode("utf-8")
        path = output / f"{number:04d}.md"
        path.write_bytes(raw)
        reference_units.append({
            **unit, "file": Path(os.path.relpath(path, HERE)).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    reference = {
        "schema_version": 1, "case_id": case["case_id"],
        "review": {"status": "draft", "reviewed_by": None, "reviewed_at": None},
        "source_hashes": {case["sources"][0]["source_id"]: case["sources"][0]["sha256"]},
        "profile": {"name": "commonmark-v1", "check_inline_formatting": False,
                    "check_block_structure": True, "check_links": False},
        "units": reference_units, "assets": [],
        "notes": [
            "Draft oracle authored from direct OOXML inspection, not from a candidate preparation output.",
            "Human source/visual review is required before changing review.status to approved.",
            "Choice/Fallback content is selected once; cover title, dedication, and author are retained.",
            "The 22 body headings comprise 19 numbered chapters, an epilogue, an appendix, and an afterword.",
            "The leading front_matter unit retains cover information and displayed TOC entries/page numbers.",
            "Tabs become one space; empty layout paragraphs are omitted. Scene-break interpretation still needs review.",
            "ChineseDiary and ChineseQuote paragraphs are blockquotes under the public case instructions.",
            "Inline emphasis and hyperlink destinations are not certified by this draft profile; manual checks remain mandatory.",
            "Embedded fonts and separator-only footnote/endnote parts are not manuscript assets or textual notes.",
            "This authoring script is not a DOCX preparation adapter and must not be used to generate evaluated candidates."
        ],
    }
    existing.write_text(json.dumps(reference, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Authored {len(units)} draft reference units. No candidate was prepared or evaluated.")


if __name__ == "__main__":
    main()
