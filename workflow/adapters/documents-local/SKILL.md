---
name: documents-local
description: Construct unchanged accepted manuscript DOCX files through the workflow's deterministic python-docx builder and Word or LibreOffice renderer, then visually inspect every rendered page before delivery.
---

# Local and cloud document adapter

This adapter is implemented by `workflow/src/document_adapters.py`. It is a
separate adapter from the desktop-managed Documents package; it uses the
workflow's Python environment and the explicitly selected local renderer.

## Authority and lifecycle

- `format-manuscript` owns design, the specification, FM item dispositions, and
  separate final closure. This adapter never authorizes editorial changes.
- Preserve all accepted words, punctuation, paragraph order, emphasis, headings,
  hyperlinks, and explicit literary line breaks. Never add author or copyright data.
- Save the complete design in `manuscript-formatting/format-spec.md` and the
  corresponding machine settings in `manuscript-formatting/format-settings.json`.
  Include the settings in the presented design; both snapshots are bound to review.
- Before closure, include exactly one line `- Status: proposed` in the canonical
  specification. After closure the host updates that status and the sheet's
  closure state, recording the receipt before building. Reuse that receipt rather
  than applying it again in the visual-review turn.
- The host builds and renders only after closure. Do not write a competing builder,
  invoke the desktop-managed runtime, or generate manuscript DOCX before approval.
- After rendering, inspect every page image listed in the host's QA manifest.
  The host does not automatically declare those pages visually reviewed.
- Mark only inspected, clean pages as reviewed, with no outstanding findings.
  If layout needs a design change, propose revised settings and obtain new approval.
  The host creates a new build directory and regenerates all page evidence.
- Do not change the generated DOCX/PDF/PNG files or their bound hashes by hand.
  Return `completed` only after content checks and visual/specification QA pass.
- Missing dependencies, fonts, Word automation, or LibreOffice produce
  `blocked-adapter`. Report the actual cause; do not claim rendering succeeded.

## Machine settings

Use exactly these JSON fields (the host validates types, ranges and page geometry):

```json
{
  "schema_version": 1,
  "profile": "reader-facing",
  "body_font": "Georgia",
  "fallback_font": "Times New Roman",
  "font_size": 11,
  "title_font_size": 24,
  "heading_font_size": 16,
  "folio_font_size": 9,
  "toc_font_size": 11,
  "page_width_inches": 6,
  "page_height_inches": 9,
  "margin_inches": 0.75,
  "footer_inches": 0.35,
  "first_line_indent_inches": 0.2,
  "line_spacing": 1.2,
  "alignment": "left",
  "include_toc": true,
  "chapter_new_page": true,
  "indent_opening_paragraphs": false,
  "title_space_after_pt": 24,
  "heading_space_before_pt": 24,
  "heading_space_after_pt": 18,
  "toc_space_after_pt": 6
}
```

These values are a proposed reader-facing design, not an automatic approval.
Use the requested profile and source evidence. A fallback font is documented
but never substituted silently: it requires revised settings and renewed review.
The host checks primary font availability in the selected rendering environment.
Only installed fonts are used; fonts are not embedded.

`indent_opening_paragraphs: false` makes the first paragraph after a heading flush
left; `true` applies the same first-line indentation as other body paragraphs.
State that choice explicitly in the specification. Headings are centered, regular,
and kept with following text; body paragraph spacing is zero. The Contents label
uses the larger of the body size and heading size minus 2 pt, with 12 pt before
and after. TOC/title paragraphs do not inherit chapter page breaks.

The builder supports ordinary literary Markdown paragraphs and headings, inline
emphasis/code, block quotations, hyperlinks, and explicit line breaks. Images,
raw HTML, thematic-break markup, fenced code and lists currently need additional
content/layout support and must not be silently discarded.

## Builder and renderer roles

- **Builder:** `python-docx` creates semantic Title/Heading styles, bookmarks,
  linked TOC entries, consistent paragraph formatting, and an automatic PAGE field.
- **Windows renderer:** a dedicated Microsoft Word COM instance updates fields,
  paginates, saves this job's generated DOCX, and exports PDF. It must not attach to
  or close the user's existing documents.
- **Cloud renderer:** isolated headless LibreOffice exports the same DOCX to PDF.
  No Word installation or Windows COM dependency is required.
- **Pagination:** the host reads actual heading destinations from the rendered
  PDF outline and rebuilds the static linked TOC until its page numbers converge.
  It verifies the final rendered TOC text against those destinations.
- **Page evidence:** PDFium rasterizes every PDF page to PNG. The agent inspects
  those full-page images; PDF and PNG files remain internal QA artifacts.

Switching renderers or settings creates a different edition identity and requires
fresh rendering and QA. Do not reuse a previous renderer's pagination evidence.
