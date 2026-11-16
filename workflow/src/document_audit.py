"""Document inspection primitives, independent of workflow and agent execution."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def docx_paragraphs(path):
    with ZipFile(path) as archive:
        require(sum(info.file_size for info in archive.infolist()) <= 64 * 1024 * 1024,
                "DOCX exceeds the uncompressed audit size limit.")
        require(archive.testzip() is None, "DOCX archive integrity failed.")
        require({"[Content_Types].xml", "_rels/.rels", "word/document.xml", "word/styles.xml"}
                <= set(archive.namelist()), "DOCX package is missing required document parts.")
        types = ET.fromstring(archive.read("[Content_Types].xml"))
        require(any(node.get("PartName") == "/word/document.xml" and node.get("ContentType") ==
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
                    for node in types), "Package does not declare a standard DOCX main document.")
        relationships = ET.fromstring(archive.read("_rels/.rels"))
        require(any(node.get("Type", "").endswith("/officeDocument")
                    and node.get("Target", "").lstrip("/") == "word/document.xml"
                    and node.get("TargetMode") != "External" for node in relationships),
                "DOCX package has no internal main-document relationship.")
        document = ET.fromstring(archive.read("word/document.xml"))
        styles = ET.fromstring(archive.read("word/styles.xml"))
        style_map = {style.get(W + "styleId"): style for style in styles.findall(W + "style")}
        paragraphs = []
        for paragraph in document.findall(".//" + W + "body//" + W + "p"):
            value = ""
            for node in paragraph.iter():
                if node.tag == W + "t":
                    value += node.text or ""
                elif node.tag == W + "tab":
                    value += "\t"
                elif node.tag == W + "br" and node.get(W + "type") != "page":
                    value += "\n"
            style_ref = paragraph.find(W + "pPr/" + W + "pStyle")
            style = style_map.get(style_ref.get(W + "val")) if style_ref is not None else None
            outline = paragraph.find(W + "pPr/" + W + "outlineLvl")
            if outline is None and style is not None:
                outline = style.find(W + "pPr/" + W + "outlineLvl")
            name = style.find(W + "name") if style is not None else None
            paragraphs.append({
                "text": value, "heading": outline is not None and int(outline.get(W + "val", "9")) < 9,
                "title": name is not None and name.get(W + "val", "").lower() == "title",
                "toc": name is not None and name.get(W + "val", "").lower().startswith("toc"),
            })
        require(paragraphs, "DOCX has no body paragraphs.")
        fields = []
        for name in archive.namelist():
            if name == "word/document.xml" or re.fullmatch(r"word/(header|footer)\d+\.xml", name):
                xml = ET.fromstring(archive.read(name))
                fields.extend(node.text or "" for node in xml.iter(W + "instrText"))
                fields.extend(node.get(W + "instr", "") for node in xml.iter(W + "fldSimple"))
        return paragraphs, any(re.search(r"\bPAGE\b", field) for field in fields)
