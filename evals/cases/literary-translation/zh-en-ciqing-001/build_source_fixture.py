"""Reproduce this case's text fixture; not a production DOCX preparation adapter."""

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def expected_source():
    case = json.loads((HERE / "case.json").read_text(encoding="utf-8"))
    metadata_path = (HERE / case["source_metadata_file"]).resolve()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    provenance = metadata["provenance"]
    source = (metadata_path.parent / provenance["original_file"]).resolve()
    if sha(source.read_bytes()) != provenance["original_sha256"]:
        raise ValueError("DOCX changed; establish a new source revision before rebuilding.")
    with ZipFile(source) as archive:
        xml = archive.read("word/document.xml")
    root = ET.fromstring(xml)
    body = root.find(f"{{{W}}}body")
    if any(node.tag not in (f"{{{W}}}p", f"{{{W}}}sectPr") for node in body):
        raise ValueError("Unexpected body structure; review the extraction method.")
    for tag in ("tbl", "drawing", "pict", "footnoteReference", "endnoteReference",
                "ins", "del", "tab", "br", "cr", "sym", "instrText", "txbxContent"):
        if root.find(f".//{{{W}}}{tag}") is not None:
            raise ValueError(f"Unsupported text/format structure: {tag}")
    paragraphs = body.findall(f"{{{W}}}p")
    texts = ["".join(node.text or "" for node in p.iter(f"{{{W}}}t")) for p in paragraphs]
    # Independently traverse the DOM and compare every paragraph, including empties.
    with minidom.parseString(xml) as document:
        dom_body = document.getElementsByTagNameNS(W, "body")[0]
        dom_texts = [
            "".join(child.data for node in p.getElementsByTagNameNS(W, "t")
                    for child in node.childNodes if child.nodeType == child.TEXT_NODE)
            for p in dom_body.childNodes if p.nodeType == p.ELEMENT_NODE and p.localName == "p"
        ]
    if texts != dom_texts:
        raise ValueError("Independent paragraph traversals disagree.")
    inventory = provenance["extraction"]
    headings = []
    for index, paragraph in enumerate(paragraphs, 1):
        style = paragraph.find(f"{{{W}}}pPr/{{{W}}}pStyle")
        if style is not None and style.get(f"{{{W}}}val") == "ChineseSub-Heading":
            headings.append(index)
    if (headings != inventory["section_heading_paragraphs"]
            or [texts[i - 1] for i in headings] != [str(i) for i in range(1, 11)]
            or texts[0] != metadata["work"]["title"]):
        raise ValueError("Title or section boundaries changed.")
    if (len(texts) != inventory["paragraph_count"]
            or sum(bool(t.strip()) for t in texts) != inventory["nonempty_paragraph_count"]
            or sum(not c.isspace() for t in texts for c in t) != inventory["nonwhitespace_character_count"]
            or sha(json.dumps(texts, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            != inventory["ordered_paragraphs_sha256"]):
        raise ValueError("Paragraph inventory differs from the frozen source baseline.")
    data = ("\n\n".join(texts) + "\n").encode("utf-8")
    if sha(data) != provenance["source_text_sha256"]:
        raise ValueError("Extracted text hash differs from the frozen source baseline.")
    return metadata_path.parent / metadata["source_file"], data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify the existing fixture without writing.")
    args = parser.parse_args()
    target, data = expected_source()
    if target.exists():
        if target.read_bytes() != data:
            raise ValueError("Existing fixture differs; refusing to overwrite it.")
    elif args.check:
        raise ValueError("Source fixture is missing.")
    else:
        with target.open("xb") as handle:
            handle.write(data)
    print(f"Verified source fixture: {len(data)} bytes; SHA-256 {sha(data)}")


if __name__ == "__main__":
    main()
