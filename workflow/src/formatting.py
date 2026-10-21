"""Optional, isolated formatting jobs over accepted English manuscript snapshots."""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import struct
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from .engine import Engine, RESULT_SCHEMA, SKILLS, WORKFLOW_ROOT
from .storage import Store, digest, local_file, now, plain, read_bytes

FORMAT_DEFINITION = WORKFLOW_ROOT / "definitions/formatting.json"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
FORMAT_RESULT_SCHEMA = copy.deepcopy(RESULT_SCHEMA)
FORMAT_RESULT_SCHEMA["properties"]["gate"] = {"enum": [None, "format_spec", "question"]}
FORMAT_RESULT_SCHEMA["properties"]["qa_path"] = {"type": ["string", "null"]}
FORMAT_RESULT_SCHEMA["required"].append("qa_path")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def select_renderer(override=None):
    backend = json.loads(FORMAT_DEFINITION.read_text(encoding="utf-8"))["document_backend"]
    require(backend["builder"] == "python-docx" and backend["require_visual_review"] is True,
            "The built-in adapter requires python-docx and visual review.")
    renderer = override or backend["renderer"]
    if renderer == "platform-default":
        renderer = "word" if os.name == "nt" else "libreoffice"
    require(renderer in ("word", "libreoffice"), "Unsupported configured renderer.")
    return renderer


def manuscript_paragraphs(text):
    """Visible source paragraphs and semantic headings; unsupported content fails closed."""
    from markdown_it import MarkdownIt
    result, heading = [], False
    for token in MarkdownIt("commonmark").parse(text):
        if token.type in ("html_block", "html_inline", "image", "hr", "fence", "code_block"):
            raise ValueError(f"Unsupported manuscript block for content audit: {token.type}")
        if token.type == "heading_open":
            heading = True
        if token.type == "inline":
            value = ""
            for child in token.children or []:
                if child.type in ("text", "code_inline"):
                    value += child.content
                elif child.type == "softbreak":
                    value += " "
                elif child.type == "hardbreak":
                    value += "\n"
                elif child.type not in ("em_open", "em_close", "strong_open", "strong_close",
                                        "link_open", "link_close", "text_special"):
                    raise ValueError(f"Unsupported inline content for audit: {child.type}")
                elif child.type == "text_special":
                    value += child.content
            if value.strip():
                result.append({"text": value, "heading": heading})
        if token.type == "heading_close":
            heading = False
    require(result, "Accepted manuscript has no readable paragraphs.")
    return result


def normalized(text):
    # Ignore layout spaces, but preserve hard line breaks within literary paragraphs.
    return "\n".join(re.sub(r"[ \t\r]+", " ", line).strip() for line in text.split("\n")).strip()


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


class FormattingEngine(Engine):
    agent_stages = ("format",)
    result_schema = FORMAT_RESULT_SCHEMA

    def __init__(self, root):
        super().__init__(root)
        if self.state().get("backend"):
            self.result_schema = copy.deepcopy(FORMAT_RESULT_SCHEMA)
            self.result_schema["properties"]["settings_path"] = {"type": ["string", "null"]}
            self.result_schema["required"].append("settings_path")

    @classmethod
    def create_from_run(cls, parent, *, documents_skill=None, renderer=None, purpose="reader-facing", model=None, new_edition=False):
        require(purpose in ("reader-facing", "editorial-review", "submission"), "Unsupported edition purpose.")
        require(not (documents_skill and renderer), "Choose an external Documents skill OR a built-in renderer.")
        backend = None
        if documents_skill is None:
            from .document_adapters import preflight
            renderer = select_renderer(renderer)
            capabilities = preflight(renderer)
            backend = {"builder": "python-docx", "renderer": renderer, "capabilities": capabilities,
                       "code_sha256": digest(Path(__file__).with_name("document_adapters.py").read_bytes()),
                       "require_visual_review": True}
            documents_skill = WORKFLOW_ROOT / "adapters/documents-local"
        adapter = plain(Path(documents_skill))
        if adapter.is_file():
            require(adapter.name == "SKILL.md", "Supply the Documents skill directory or its SKILL.md.")
            adapter = adapter.parent
        require((adapter / "SKILL.md").is_file(), "Documents/output-format skill is unavailable.")
        definition = json.loads(FORMAT_DEFINITION.read_text(encoding="utf-8"))
        definition["agents"]["format"]["model"] = model
        if backend:
            definition["document_backend"] = backend
        else:
            definition["document_backend"] = {"builder": "external-documents-skill", "renderer": "external",
                                              "require_visual_review": True}
        with parent.store.locked():
            parent_revision, source_state = parent.store.load()
            require(source_state.get("kind") != "manuscript-formatting" and source_state["status"] == "COMPLETED",
                    "Formatting requires a completed translation export.")
            parent.verify(source_state)
            require(source_state.get("acceptance", {}).get("hashes") == [a["sha256"] for a in source_state["outputs"]],
                    "Formatting requires exactly accepted English chapters.")
            input_data = [parent.store.content(a) for a in source_state["outputs"]]
            combined = b"\n".join(input_data)
            expected_paragraphs = manuscript_paragraphs(combined.decode("utf-8"))
            identity = digest(combined)
            adapter_hash = digest((adapter / "SKILL.md").read_bytes())
            for previous in reversed(source_state.get("format_jobs", [])):
                if (not new_edition and previous["input_sha256"] == identity and previous["purpose"] == purpose
                        and previous["model"] == model and previous["adapter_sha256"] == adapter_hash
                        and previous.get("backend") == backend):
                    return cls(parent.root / previous["path"])
            sources = {name: SKILLS / name for name in ("prepare-manuscript", "review-approval-sheet", "format-manuscript")}
            sources["documents"] = adapter
            inventory = {}
            for name, directory in sources.items():
                require((directory / "SKILL.md").is_file(), f"Missing required skill: {name}")
                for path in directory.rglob("*"):
                    if "__pycache__" in path.parts or path.suffix == ".pyc":
                        continue
                    plain(path)
                    if path.is_file():
                        require(path.stat().st_nlink == 1, "Linked skill resource is not supported.")
                        inventory[f"{name}/{path.relative_to(directory).as_posix()}"] = (path, digest(read_bytes(path)))
            job_id = "edition-" + uuid.uuid4().hex[:12]
            destination = plain(parent.root / "formatting")
            destination.mkdir(exist_ok=True)
            root = destination / job_id
            source_manifest = {
                "parent_run_id": source_state["id"], "acceptance": source_state["acceptance"],
                "chapters": [{"chapter_id": a["chapter_id"], "sha256": a["sha256"],
                              "file": f"chapters/{index:04d}.md"}
                             for index, a in enumerate(source_state["outputs"], 1)],
                "manuscript_sha256": identity, "content_reference": "content.json",
            }
            manifest_bytes = (json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            content_bytes = (json.dumps(expected_paragraphs, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            state = {
                "id": job_id, "kind": "manuscript-formatting", "created_at": now(),
                "definition": definition, "status": "READY", "stage": "format", "chapter_index": 0,
                "attempts": 0, "thread_id": None, "gate": None, "receipts": [], "next_input": None,
                "domain_state": None, "error": None, "prepared": None, "continuity": {}, "outputs": [],
                "chapters": source_manifest["chapters"], "purpose": purpose, "format_approval": None,
                "source_name": "manuscript.md", "source_hash": identity, "source_language": "en",
                "parent_run": str(parent.root), "parent_run_id": source_state["id"],
                "input_manifest_sha256": digest(manifest_bytes),
                "expected_paragraphs": expected_paragraphs,
                "skills": {relative: sha for relative, (_, sha) in inventory.items()},
                "adapter_origin": str(adapter), "adapter_sha256": adapter_hash,
                "backend": backend, "approved_settings": None, "generated": None,
                "input_files": {"manuscript.md": identity, "manifest.json": digest(manifest_bytes),
                                "content.json": digest(content_bytes),
                                **{f"chapters/{i:04d}.md": digest(data) for i, data in enumerate(input_data, 1)}},
            }
            store = Store.create(root, state)
            try:
                (root / "input/chapters").mkdir()
                (root / "input/manuscript.md").write_bytes(combined)
                (root / "input/manifest.json").write_bytes(manifest_bytes)
                (root / "input/content.json").write_bytes(content_bytes)
                for index, data in enumerate(input_data, 1):
                    (root / f"input/chapters/{index:04d}.md").write_bytes(data)
                for relative, (source, sha) in inventory.items():
                    target = root / "skills" / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    require(digest(target.read_bytes()) == sha, "Skill changed while pinning the format job.")
                state["source"] = store.snapshot(root / "input/manuscript.md", "accepted_english_manuscript")
                if backend:
                    state["adapter_code"] = store.snapshot(Path(__file__).with_name("document_adapters.py"),
                                                          "document_adapter_code")
                store.save(0, state, "formatting.created", {"parent_run_id": source_state["id"]})
            finally:
                store.close()
            source_state.setdefault("format_jobs", []).append({
                "job_id": job_id, "path": root.relative_to(parent.root).as_posix(),
                "input_sha256": identity, "purpose": purpose, "model": model, "adapter_sha256": adapter_hash,
                "backend": backend,
            })
            parent.store.save(parent_revision, source_state, "formatting.requested", {"job_id": job_id})
        return cls(root)

    def verify(self, state):
        if state.get("backend") and state["status"] != "COMPLETED":
            require(digest(Path(__file__).with_name("document_adapters.py").read_bytes()) == state["backend"]["code_sha256"],
                    "Document adapter implementation changed; start a new edition.")
        if state.get("adapter_code"):
            self.store.content(state["adapter_code"])
        parent = Store(Path(state["parent_run"]))
        try:
            parent_state = parent.load()[1]
            manifest = json.loads((self.root / "input/manifest.json").read_text(encoding="utf-8"))
            require(parent_state["id"] == state["parent_run_id"]
                    and parent_state.get("acceptance") == manifest["acceptance"],
                    "Accepted source version changed; create a newly reviewed edition.")
        finally:
            parent.close()
        for relative, sha in state["input_files"].items():
            require(digest(read_bytes(local_file(self.root / "input", relative))) == sha, "Formatting input changed.")
        for relative, sha in state["skills"].items():
            require(digest(read_bytes(local_file(self.root / "skills", relative))) == sha, "Pinned formatting skill changed.")
        for artifact in state["outputs"]:
            self.store.content(artifact)
        if state.get("generated"):
            settings = state["approved_settings"]
            require(digest(read_bytes(self.file(settings["path"]))) == settings["sha256"],
                    "Approved settings changed after rendering.")
            for artifact in [state["generated"]["document"], state["generated"]["pdf"], *state["generated"]["pages"]]:
                require(digest(read_bytes(self.file(artifact["path"]))) == artifact["sha256"],
                        "Generated rendering evidence changed; rebuild through the approved adapter.")

    def prompt(self, state):
        if state.get("backend"):
            return self._local_prompt(state)
        context = {
            "input_manifest": str(self.root / "input/manifest.json"),
            "manuscript": str(self.root / "input/manuscript.md"), "purpose": state["purpose"],
            "content_reference": str(self.root / "input/content.json"),
            "input_manifest_sha256": state["input_manifest_sha256"],
            "manuscript_sha256": state["source_hash"], "approved_spec": state["format_approval"],
            "python_executable_for_review_helpers": sys.executable,
            "skills": {name: str(self.root / "skills" / name / "SKILL.md")
                       for name in ("format-manuscript", "prepare-manuscript", "review-approval-sheet", "documents")},
            "adapter_origin": state["adapter_origin"], "adapter_sha256": state["adapter_sha256"],
            "domain_state": state["domain_state"], "user_receipt": state["next_input"],
            "expected_paragraph_count": len(state["expected_paragraphs"]),
        }
        return (
            "Act as the final manuscript formatter. Read the pinned format-manuscript skill and its "
            "required references, shared approval helper, and Documents skill. Consolidate all accepted "
            "English chapters in manifest order into ONE readable DOCX. This is formatting only: preserve "
            "every word, punctuation mark, paragraph, heading, intentional ambiguity and literary line break. "
            "Do not apply the Documents skill's generic prose-rewriting/introduction suggestions to this "
            "already accepted manuscript. Do not invent an author, copyright claim, subtitle, or front matter. "
            "Use the source's title. Title and section headings must appear once in the body, with semantic "
            "Word styles; any TOC is additional navigation. Input paths and skill resources are read-only; "
            "write only inside this job workspace. Keep manuscript-formatting/format-spec.md, "
            "format-review.json and outputs/docx/ as the formatting skill requires. The input is a set of "
            "accepted English artifact snapshots, not the original-language prepared package.\n\n"
            "Before document generation, inspect fonts and adapter/render capabilities, infer a full "
            "specification for the requested purpose, and put classification/intended use and consequential "
            "choices into FM### items. Save a complete immutable proposal copy as the binding_path, separate "
            "from the mutable approved-status format-spec.md. Return needs_human_input with gate=format_spec, "
            "state_path=format-spec.md, review_path=the JSON sheet and binding_path=that proposal. Use the "
            "shared schema/parser with item dispositions and a NEW revision for separate final closure. "
            "The CLI has no inline host; present its permitted full readable text fallback. Never mark an "
            "item resolved without its recorded receipt. After a correction, revalidate affected items and "
            "closure. Do not generate DOCX before closure. Unknown author identity stays absent.\n\n"
            "After explicit closure, apply the exact approved design using the pinned Documents skill and "
            "its required dependency/runtime/render workflow. Use its managed tool environment for building "
            "and rendering; the supplied Python is for review helpers only. If those capabilities are missing, "
            "return blocked with a concrete blocked-adapter reason; do not substitute an unverified ad hoc "
            "builder. Render and visually inspect EVERY page, fixing layout issues and stale/blank TOCs. "
            "Do not change prose to fix pagination. Save PNG page evidence and a QA JSON manifest.\n\n"
            "Return the supplied structured schema (all paths workspace-relative; null unused values). "
            "Completed requires state_path, output_path under manuscript-formatting/outputs/docx/ ending "
            ".docx, and qa_path. QA JSON must contain schema_version=1, input_manifest_sha256, "
            "approved_spec_sha256 (immutable approved proposal hash), docx_sha256, adapter_skill_sha256, "
            "page_count, visual_review_passed=true, specification_matches=true, and content_paragraph_indexes: "
            "one zero-based DOCX body-paragraph index for EACH source Markdown visible paragraph/heading in "
            "source order. Index all w:p descendants of w:body, including empty/TOC paragraphs, from zero. "
            "Emphasis/link markup is formatting; its visible text must be unchanged. Additional nonempty "
            "body paragraphs are permitted only for Contents/Table of Contents labels and TOC entries "
            "derived from source headings, optionally followed by page numbers. For each rendered page add "
            "pages:[{page:1,image:<relative PNG path>,sha256:<hash>,reviewed:true,findings:[]}]. Include every "
            "PNG page from the render directory. Use named TOC styles for TOC entries. Multi-page documents require automatic PAGE fields. "
            "This QA record is an auditable visual-review attestation, not permission to skip inspection. "
            "The host will compare actual DOCX text and semantic heading styles against the immutable source, "
            "verify hashes/pages/approval and publish the document only if checks pass.\n\n"
            + json.dumps(context, ensure_ascii=False, indent=2)
        )

    def _record_closure(self, state, gate):
        require(gate["kind"] == "format_spec", "Unexpected formatting closure.")
        state["format_approval"] = gate["binding"]
        if state.get("backend"):
            state["approved_settings"] = gate["settings"]

    def _result(self, state, result):
        require(result["state_path"] or result["outcome"] == "blocked", "Formatting needs a saved format specification.")
        if result["state_path"]:
            state["domain_state"] = self.checkpoint(result["state_path"], "format_specification")
        if result["outcome"] == "blocked":
            state.update(status="BLOCKED", error=result["message"])
            return
        if result["outcome"] == "needs_human_input":
            require(result["gate"] in ("format_spec", "question"), "Unexpected formatting gate.")
            if result["gate"] == "format_spec":
                require(result["review_path"] and result["binding_path"], "Format review needs a sheet and specification binding.")
                sheet = self.approval.load_sheet(self.file(result["review_path"]))
                require(sheet["gate"]["closure_required"] and sheet["gate"]["final_closure"] == "pending",
                        "Format specification needs separate final closure.")
                state["format_approval"] = None
                state["approved_settings"] = None
                if state.get("generated"):
                    state.setdefault("previous_builds", []).append(state["generated"])
                    state["generated"] = None
            self._wait(state, result)
            if result["gate"] == "format_spec" and state.get("backend"):
                from .document_adapters import validate_settings
                settings = self.checkpoint(result["settings_path"], "format_settings")
                values = validate_settings(json.loads(self.store.content(settings)))
                require(values["profile"] == state["purpose"], "Settings profile differs from the requested edition.")
                state["gate"]["settings"] = settings
            return
        require(result["gate"] is None and state["format_approval"], "Format specification has not been approved.")
        approved = state["format_approval"]
        require(digest(read_bytes(self.file(approved["path"]))) == approved["sha256"], "Approved format specification changed.")
        relative = result["output_path"]
        require(relative and relative.startswith("manuscript-formatting/outputs/docx/") and relative.endswith(".docx"),
                "Formatted output must be a DOCX inside the formatting output directory.")
        document = self.checkpoint(relative, "formatted_docx")
        if state.get("backend"):
            require(state.get("generated") and document["sha256"] == state["generated"]["document"]["sha256"],
                    "Local DOCX must come from the approved builder/renderer.")
        qa_artifact = self.checkpoint(result["qa_path"], "format_qa")
        qa = json.loads(self.store.content(qa_artifact))
        require(qa.get("schema_version") == 1 and qa.get("input_manifest_sha256") == state["input_manifest_sha256"]
                and qa.get("approved_spec_sha256") == approved["sha256"]
                and qa.get("docx_sha256") == document["sha256"]
                and qa.get("adapter_skill_sha256") == state["adapter_sha256"], "Formatting QA bindings do not match.")
        require(qa.get("visual_review_passed") is True and qa.get("specification_matches") is True,
                "Visual/specification QA is incomplete.")
        if state.get("backend"):
            require(qa.get("settings_sha256") == state["approved_settings"]["sha256"]
                    and qa.get("renderer") == state["backend"]["renderer"]
                    and qa.get("pdf_sha256") == state["generated"]["pdf"]["sha256"],
                    "QA does not match the selected renderer/settings/rendered PDF.")
        actual, automatic_folios = docx_paragraphs(self.file(relative))
        indexes = qa.get("content_paragraph_indexes")
        expected = state["expected_paragraphs"]
        require(isinstance(indexes, list) and len(indexes) == len(expected)
                and all(type(i) is int and 0 <= i < len(actual) for i in indexes)
                and indexes == sorted(set(indexes)), "Content paragraph mapping is incomplete or out of order.")
        headings = [normalized(p["text"]) for p in expected if p["heading"]]
        for offset, (source, index) in enumerate(zip(expected, indexes)):
            paragraph = actual[index]
            require(normalized(source["text"]) == normalized(paragraph["text"]), "DOCX changes accepted manuscript text.")
            if source["heading"]:
                require(paragraph["heading"] or (offset == 0 and paragraph["title"]),
                        "DOCX headings must use semantic Word styles/outline levels.")
        mapped = set(indexes)
        for index, paragraph in enumerate(actual):
            text = normalized(paragraph["text"])
            if not text or index in mapped:
                continue
            require(text in ("Contents", "Table of Contents") or (paragraph["toc"] and any(
                re.fullmatch(re.escape(heading) + r"(?:[ \t]+\d+|[ \t]+[ivxlcdm]+)?", text, re.I)
                for heading in headings)), "DOCX contains undeclared extra body text.")
        pages = qa.get("pages")
        require(type(qa.get("page_count")) is int and qa["page_count"] > 0
                and isinstance(pages, list) and len(pages) == qa["page_count"], "Rendered page coverage is incomplete.")
        require(qa["page_count"] == 1 or automatic_folios, "Multi-page DOCX needs automatic page-number fields.")
        evidence, paths = [], set()
        for number, page in enumerate(pages, 1):
            require(page.get("page") == number and page.get("reviewed") is True and page.get("findings") == [],
                    "Every rendered page needs a successful visual-review record.")
            path = self.file(page["image"])
            data = read_bytes(path)
            require(path.suffix.lower() == ".png" and data[:8] == b"\x89PNG\r\n\x1a\n"
                    and len(data) >= 24 and data[12:16] == b"IHDR"
                    and all(struct.unpack(">II", data[16:24])), "Missing or invalid rendered page PNG.")
            require(digest(data) == page["sha256"] and path not in paths, "Rendered page identity mismatch.")
            paths.add(path)
            evidence.append(self.checkpoint(page["image"], "rendered_page"))
        require(len({p.parent for p in paths}) == 1
                and {p for p in next(iter(paths)).parent.glob("*.png")} == paths,
                "QA must cover every PNG in the render directory.")
        state.update(outputs=[document], qa=qa_artifact, rendered_pages=evidence, status="COMPLETED")
        export = plain(self.root / "export")
        export.mkdir(exist_ok=True)
        target = export / "manuscript.docx"
        data = self.store.content(document)
        if target.exists():
            require(target.read_bytes() == data, "Existing formatted export differs; start a new edition.")
        else:
            with target.open("xb") as handle:
                handle.write(data)
        state["document_path"] = str(target)
        state["export_path"] = str(export)
        publication = {
            "job_id": state["id"], "parent_run_id": state["parent_run_id"],
            "input_manifest_sha256": state["input_manifest_sha256"],
            "manuscript_sha256": state["source_hash"], "approved_spec": approved,
            "document": document, "qa": qa_artifact, "rendered_pages": evidence,
            "backend": state.get("backend"),
            "adapter_code": state.get("adapter_code"),
        }
        publication_bytes = (json.dumps(publication, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        manifest_path = plain(export / "manifest.json")
        if manifest_path.exists():
            require(manifest_path.read_bytes() == publication_bytes, "Existing publication manifest differs.")
        else:
            with manifest_path.open("xb") as handle:
                handle.write(publication_bytes)

    def _local_prompt(self, state):
        context = {
            "input_manifest": str(self.root / "input/manifest.json"),
            "manuscript": str(self.root / "input/manuscript.md"),
            "content_reference": str(self.root / "input/content.json"),
            "purpose": state["purpose"], "backend": state["backend"],
            "skills": {name: str(self.root / "skills" / name / "SKILL.md")
                       for name in ("format-manuscript", "review-approval-sheet", "documents")},
            "python_executable": sys.executable, "user_receipt": state["next_input"],
            "approved_spec": state["format_approval"], "approved_settings": state["approved_settings"],
            "generated": state.get("generated"), "domain_state": state["domain_state"],
        }
        return (
            "Act as the manuscript formatter using the pinned format-manuscript, review-approval-sheet "
            "and documents-local adapter instructions. The user selected the local python-docx builder "
            "and the renderer in the context. This is NOT the desktop-managed Documents adapter: no "
            "managed dependency loader, Node marker, or bundled LibreOffice runtime is required for Word. "
            "The host preflighted the selected renderer. Preserve every accepted word, heading, paragraph, "
            "and inline emphasis. Do not retranslate, rewrite, add an introduction/author/copyright, or "
            "substitute original-language content. The input manifest orders all English chapters.\n\n"
            "Before generation, save manuscript-formatting/format-spec.md and format-settings.json "
            "with exactly the fields in documents-local/SKILL.md. Check installed fonts before proposing "
            "the design. State the indent_opening_paragraphs choice explicitly and consistently with "
            "its JSON value; do not promise settings unsupported by this builder. Present "
            "profile/classification and consequential design groups as FM items, "
            "including exact settings in their details. Readable fiction can use a 6x9 inch Georgia "
            "edition when those choices suit the manuscript and are approved. Save an immutable proposal "
            "copy for binding_path. Return needs_human_input with gate=format_spec, review_path=the "
            "shared JSON sheet, binding_path=the immutable proposal, settings_path=the JSON settings, "
            "state_path=format-spec.md and qa_path/output_path=null. The CLI lacks inline display; use "
            "the approved text fallback. Parse incoming receipts, preserve decision provenance, update "
            "the domain records, and present a NEW revision for separate final closure. Do not change "
            "the settings while merely recording acceptance. All accepting FM items can be handled in "
            "one batch. No document generation before closure.\n\n"
            "Use one exact line '- Status: proposed' in format-spec.md before approval. "
            "After closure the HOST records its receipt in format-spec.md and format-review.json, "
            "then builds and renders the approved edition "
            "and provides generated artifacts/QA metadata. Do not create a different DOCX or edit these "
            "generated DOCX/PDF/PNG files. When generated is present: verify the host's closure receipt "
            "in format-spec.md without duplicating it, inspect EVERY listed full-page PNG with the image-view tool, and verify "
            "typography, paragraph treatment, headings, navigation/TOC, page numbers and page flow. "
            "Use explicit absolute image paths from workspace plus the saved relative paths. Read the "
            "generated QA JSON at generated.qa_path. For each inspected clean page, set reviewed=true "
            "and findings=[]; set visual_review_passed/specification_matches=true only after all checks. "
            "Keep all binding hashes, paragraph indexes, renderer data and page paths unchanged. "
            "If design changes are needed, return a new format_spec gate with revised settings and no "
            "completed output; the host rebuilds after approval. If tooling or inspection is unavailable, "
            "return blocked with the concrete reason, never claim visual review without images.\n\n"
            "Completed requires output_path=generated.document.path, qa_path=generated.qa_path, "
            "state_path=format-spec.md, settings_path=the approved settings path, and gate=null. "
            "Use null for unused fields. The host performs independent text/order/style/hash/evidence "
            "checks before publishing the DOCX. Do not include internal QA images in the user manuscript.\n"
            + json.dumps(context, ensure_ascii=False, indent=2)
        )

    def advance(self, runtime):
        state = self.state()
        if not (state.get("backend") and state["status"] == "READY"
                and state.get("format_approval") and state.get("approved_settings") and not state.get("generated")):
            return super().advance(runtime)
        from .document_adapters import build_and_render, validate_settings
        with self.store.locked():
            revision, state = self.store.load()
            require(state["status"] == "READY" and not state.get("generated"), "Formatting state changed.")
            self.verify(state)
            for artifact in (state["format_approval"], state["approved_settings"]):
                require(digest(self.file(artifact["path"]).read_bytes()) == artifact["sha256"],
                        "Approved specification/settings changed before generation.")
            settings = validate_settings(json.loads(self.store.content(state["approved_settings"])))
            state.update(status="RUNNING", error=None)
            revision = self.store.save(revision, state, "formatting.build.started", state["backend"])
            try:
                self._record_native_closure(state)
                folder = self.workspace / "manuscript-formatting/outputs/docx" / ("build-" + uuid.uuid4().hex[:10])
                generated = build_and_render(
                    self.store.content(state["source"]).decode("utf-8"), settings, folder, state["backend"]["renderer"],
                )
                document = self.checkpoint(Path(generated["docx"]).relative_to(self.workspace).as_posix(), "formatted_docx")
                pdf = self.checkpoint(Path(generated["pdf"]).relative_to(self.workspace).as_posix(), "rendered_pdf")
                pages = [self.checkpoint(Path(page["path"]).relative_to(self.workspace).as_posix(), "rendered_page")
                         for page in generated["pages"]]
                actual, _ = docx_paragraphs(self.file(document["path"]))
                indexes, cursor = [], 0
                for expected in state["expected_paragraphs"]:
                    while cursor < len(actual):
                        paragraph = actual[cursor]
                        if (not paragraph["toc"] and normalized(paragraph["text"]) == normalized(expected["text"])
                                and (not expected["heading"] or paragraph["heading"] or paragraph["title"])):
                            break
                        cursor += 1
                    require(cursor < len(actual), "Built DOCX lost or changed a source paragraph.")
                    indexes.append(cursor)
                    cursor += 1
                qa = {
                    "schema_version": 1, "input_manifest_sha256": state["input_manifest_sha256"],
                    "approved_spec_sha256": state["format_approval"]["sha256"],
                    "settings_sha256": state["approved_settings"]["sha256"],
                    "docx_sha256": document["sha256"], "pdf_sha256": pdf["sha256"],
                    "adapter_skill_sha256": state["adapter_sha256"],
                    "builder": generated["builder"], "builder_version": generated["builder_version"],
                    "renderer": generated["renderer"], "renderer_version": generated["renderer_version"],
                    "page_count": len(pages), "toc_pages": generated["toc_pages"], "layout_passes": generated["layout_passes"],
                    "visual_review_passed": False, "specification_matches": False,
                    "content_paragraph_indexes": indexes,
                    "pages": [{"page": i, "image": page["path"], "sha256": page["sha256"],
                               "reviewed": False, "findings": ["Visual review pending"]}
                              for i, page in enumerate(pages, 1)],
                }
                qa_path = folder / "qa.json"
                qa_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
                state["generated"] = {"document": document, "pdf": pdf, "pages": pages,
                                      "qa_path": qa_path.relative_to(self.workspace).as_posix()}
                state["status"] = "READY"
                self.store.save(revision, state, "formatting.rendered", {"page_count": len(pages), "renderer": generated["renderer"]})
            except (Exception, KeyboardInterrupt) as exc:
                state.update(status="PAUSED" if isinstance(exc, KeyboardInterrupt) else "BLOCKED",
                             error="blocked-adapter: " + str(exc))
                self.store.save(revision, state, "formatting.build.failed", {"error": state["error"]})
                raise
            return state

    def _record_native_closure(self, state):
        receipt = state["next_input"]
        require(receipt and receipt["parsed"]["type"] == "final-closure"
                and receipt["gate"]["kind"] == "format_spec", "Missing native formatting closure receipt.")
        path = self.file(state["domain_state"]["path"])
        text = path.read_text(encoding="utf-8-sig")
        marker = f"Closure receipt: {receipt['id']}"
        if marker not in text:
            text, count = re.subn(r"(?m)^(- )?Status: proposed[ \t]*$", "- Status: approved", text)
            require(count == 1, "Format specification needs one explicit Status: proposed line.")
            text += (
                "\n## Recorded specification closure\n"
                f"- {marker}\n- Decision source: {receipt.get('decision_source', 'human')}\n"
                f"- Approved proposal SHA-256: {state['format_approval']['sha256']}\n"
                f"- Approved settings SHA-256: {state['approved_settings']['sha256']}\n"
            )
            path.write_text(text, encoding="utf-8", newline="\n")
        sheet_path = self.file(receipt["gate"]["sheet"]["path"])
        sheet = self.approval.load_sheet(sheet_path)
        if sheet["gate"]["final_closure"] != "confirmed":
            sheet["gate"].update(final_closure="confirmed", status="approved", ready_state="ready")
            sheet["revision"] += "-closed-" + receipt["id"][:8]
            self.approval.validate_sheet(sheet)
            sheet_path.write_text(json.dumps(sheet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        state["domain_state"] = self.checkpoint(state["domain_state"]["path"], "approved_format_specification")
