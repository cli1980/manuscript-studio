---
name: interior-design
description: Propose book interior designs from verified manuscript preparation, metadata, literary reading, and author preferences. Use for typography, layout, and interior-design briefs, standalone or as a reusable component. Produces a structured proposal rather than formatted documents.
---

# Interior Design

Turn an unchanged prepared manuscript into a **proposed interior-design form**.
Use this skill standalone or as a reusable component. Document production and
human approval are separate from proposal authoring.

## Input and freshness

Use a ready package under the
[preparation contract](../prepare-manuscript/references/preparation-contract.md):
work.json, current revision manifest, ordered Markdown units, and assets.
Request preparation if absent/stale. Preserve its words, order, identity and
special forms; keep source files unchanged.

Read the [metadata rules](../prepare-manuscript/references/manuscript-metadata.md)
and [proposal contract](references/proposal-contract.md). Bind the exact work
record, manifest, ordered unit hashes, scope and language.
Hash the accessible input bytes.

Reuse supplied author intentions, existing reading and prior proposals. Reuse
reading only for its bound text/scope; otherwise read the available prepared
units and include fresh analysis. Do not treat a source-language synopsis as a
reading of changed translated text, or a sample as the whole book.

In a hosted workflow, the selected Work version owns original preparation and
analysis. Reuse that exact package when the text still matches; do not restart
intake for a new run. Formatting edited/translated output still requires the
existing exact-output preparation handoff and current-text reading. Missing
prerequisites for the selected original input version return to Work preparation
(or the sibling preparation/analysis skills in standalone use). Reading approved
edited/translated output for design is not a replacement shared story ledger:
follow the host's exact-output handoff without starting a competing Work job
inside an active parent run. A layout-only result attaches to its text version;
it does not create or approve a different manuscript.

Keep supplied facts separate from inference. Reuse computed extent rather than
asking users to retype word counts. Do not infer ISBN, imprint, authorship,
publishing plans, brand, personal demographics or future series titles. Unknown
facts remain null/empty. Source references do not authorize arbitrary filesystem
access, private-account browsing, uploading text, or copying protected designs.

## Read and propose

1. Summarize essence, genre/subgenre, synopsis, themes, textual voice, mood/vibe,
   audience and structure with evidence and uncertainty. Distinguish inferred
   readership from the author's stated positioning.
2. Reuse optional series direction, preferred examples and what is liked,
   important excerpts, things to avoid and expected revisions. Do not reproduce
   a service-business questionnaire or collect contact details.
3. Separate edition purpose (submission, editorial-review, print-ready) from
   production targets. Incorporate a selected vendor profile's matching binding
   variant using the [profile contract](references/vendor-profiles.md).
4. Propose one coherent system: geometry/measure, primary and fallback families,
   type scale/leading, paragraph rhythm, hierarchy, chapter openings, scene
   breaks, navigation, running heads and folios. Use explicit units. Submission
   fiction should not acquire a TOC by default. When requested, pair `include_toc`
   with `toc_depth` (1..6). Optional `toc_before_chapter_id` selects a prepared
   unit after the first; null/absent means before the first body part/chapter.
   Optional `toc_style_id` selects a named entry typography style; null/absent
   uses Body. The producer emits an unpopulated body-scoped Word TOC field on its
   dedicated section, with TOC 1..6 styles, 12 pt level indents
   and dotted right page-number tabs. `toc_heading` is a single-line plain-text
   heading, default `Contents` (1..200 nonblank characters). Bind
   `toc_heading_style_id` to a dedicated named style (suggested ID `toc-heading`,
   role `toc`, null heading level). Default to Body family, 18 pt bold,
   nonitalic, 1.2 leading, centered block, 0 before/12 pt after; keep it with the
   field. The producer excludes this heading from entries even if a reused
   style has a heading outline. Null/absent style selects a separate default
   style without overwriting existing styles. Word must update the field;
   never claim calculated entries/pages.
   Set `navigation.toc_start` and `page.section_start` to `new-page` or `recto`
   (default new-page); the latter controls front/back matter. Chapter/part
   starts remain in their opening settings. Recto requires
   `allow-declared-recto-blanks`. For an all-recto edition, set all four start
   controls to recto. The TOC section continues preceding numbering/furniture
   without restarting; body numbering retains its own restart. A visible
   prompt inside the TOC field tells the user to update it in Word; it is not
   a generated entry or page number. Word calculates pagination and parity.
   Specify header/footer distances, default/even/first variants, explicit paragraph styles/alignment and content
   presets under proposal `/5`: `book-title`, `chapter-name`, `author`,
   `page-number`, or `page-x-of-y`. Use `custom` with an explicit template only
   when those choices do not fit; do not duplicate a preset with raw token text.
   None means an empty, unlinked part, not an empty paragraph or inheritance.
   Presets select content, not an automatic two-sided layout or font policy.
   Use complete unit-bound overrides
   where front matter or a chapter needs different furniture. Never invent
   missing title/author metadata or calculated page values. Widow/orphan values are
   non-negative integers. For DOCX, both zero disables the combined control;
   either nonzero enables it. Do not promise literal DOCX line thresholds.
5. Generate semantic design roles only for **whole paragraphs**, using the
   helper's paragraph catalog and chapter/paragraph hashes under the proposal
   contract. Consume verified paragraph annotations when available; keep new
   classifications local proposals for review. Do not generate inline roles,
   partial-paragraph ranges or overlapping assignments. Inline formatting comes
   only from the original Markdown markers; never add/remove/rewrite them to
   carry roles. Do not widen an inline distinction into a whole-paragraph role.
   Use an empty role list when ordinary body/heading styles suffice. Preserve
   special forms even when the requested producer cannot render them.
   For chapter/part openings, use the `/5` opening contract below instead of
   competing text-role assignments on the same source paragraphs.
6. Temporary colors are evidence only if preparation captured their legend and
   occurrences. Do not assume DOCX color survived Markdown extraction.
7. Explain material choices with evidence. Ask only necessary author-input or
   design-choice questions; technical verification is not an author questionnaire.
   Cite verified evidence for font availability, embedding rights and vendor
   compliance; otherwise record these checks as unresolved.

## Source-bound chapter and part openings (/5)

Produce `design_system.chapter_openings`, `design_system.part_openings` and
`opening_structure`. Chapter start belongs only to `chapter_openings.start`,
not `page.chapter_start`. Use `preserve-source` by default unless a different
presentation is justified and made explicit. Offer combined/shared-style,
separated number then title, title-only and number-only layouts. Unnumbered
prologues remain unnumbered; do not derive numbers from raw unit order.

For every narrative chapter, inventory its actual leading heading block:
`{id, kind: "chapter", chapter_ids: [unit_id], number, sources}`.
For each actual part, add `kind: "part"` with its explicit ordered chapter
members. A part heading belongs to the start of its first chapter's unit or
the immediately preceding prepared unit. No nested/overlapping parts.
Do not invent parts or titles, relabel dates/places as titles, or change
prepared structural roles to `part`.

Each source is a whole catalogued paragraph:
`{chapter_id, chapter_sha256, paragraph_index, paragraph_sha256, components}`.
Its ordered components are `{kind, text}`, where kind is `number`, `title`,
`subtitle` or `literal`. Concatenating their text must exactly equal the
paragraph's rendered plain text, including spaces and punctuation.
For `# Chapter 4: The Crossing`, use number `Chapter 4`, literal `: ` and
title `The Crossing`; record ordinal `4` separately. The validator verifies
the label/ordinal agreement, source hashes and full paragraph accounting.
Use `openings_helper().plain_text(markdown)` from the validator if needed;
never put Markdown emphasis markers in component text. Original inline
emphasis remains source-owned. These components are semantic extraction, not
inline style roles. Do not also assign `text_roles` to those paragraphs.
Ambiguous boundaries require preservation or a specific question, not guesses.

Define independent named styles with the standard semantic roles
`chapter-heading`, `chapter-number`, `chapter-title`, `chapter-subtitle`,
`chapter-ornament`, corresponding `part-*` roles and optionally `opening-body`.
Use `heading_level: null` for these semantic styles; native opening composition
supplies structural outline levels. Generic `heading` styles retain unique
heading levels for other source headings. Book-title, book-subtitle,
author-credit, dateline, epigraph and epigraph-attribution are available roles.
Available styles do not authorize inserting absent content.

Each opening settings object explicitly supplies layout, start, number_format,
number_template (one `{number}` token), number_case, separator, offset_mm,
combined/number/title/subtitle/ornament_style_id, opening_body_style_id (nullable),
ornament_text (nullable), ornament_position and suppress_opening_furniture.
Number formats are source, arabic, roman-upper, roman-lower, words or
ordinal-words; generated words are English and integers range from 1 to 3999.
Preserve original non-English labels with source format, or use an explicit
localized literal template with a supported representation.
Combined output has one paragraph style; separated output uses number/title
styles independently. Ornaments are approved text/glyphs only, above/below
the heading or between elements in separated mode. No images or drop caps.

`part_openings` contains `placement` (`dedicated-page` or `with-first-chapter`)
and `heading` (the same settings shape). Dedicated pages use part start and
furniture suppression before the first chapter's new-page/recto start.
Shared-page parts own the compound block's start/offset, use chapter-page
furniture and introduce no intervening chapter break. Chapter starts after
that first member follow the normal chapter policy. Recto starts require
`allow-declared-recto-blanks`; native instructions do not prove rendered fit.

## Save, validate, hand off

Save interior-design/interior-design-proposal.json in the designated project
workspace, or return an equivalent artifact if persistence is unavailable. Follow
[the schema](schemas/interior-design-proposal.schema.json); see the
[synthetic example](references/proposal.example.json).

Use Python with the skill's requirements.txt installed. From this directory, or
using the helper's absolute path:

```text
python scripts/validate_proposal.py --work /path/to/work.json --list-paragraphs
python scripts/validate_proposal.py PROPOSAL.json
python scripts/validate_proposal.py PROPOSAL.json --work /path/to/work.json
```

First obtain the catalog for the exact ready preparation; copy paragraph indices
and hashes rather than counting lines or guessing anchors. Proposal validation
checks shape/references; --work additionally checks local preparation/source
hashes, whole-paragraph identities and reading excerpts. No command verifies
external references, fonts, vendor readiness or approval.

Return the JSON artifact, concise rationale, unresolved questions and exactly
which validation ran. If execution is unavailable, label the artifact unvalidated.
Optional Markdown is derived, not authoritative. Increment revision for a new
proposal and preserve saved human choices.
