---
name: format-manuscript
description: Design and produce professionally formatted book manuscripts by inspecting the project draft, determining publication purpose, inferring and confirming genre-appropriate typography and layout, preserving an approved reusable format specification, and handing implementation to the appropriate document-generation skill. Use for Word or DOCX manuscripts with a table of contents; submission, editorial-review, or reader-facing editions; manuscript reformatting; front matter, chapter styles, paragraph treatment, headers, footers, page numbering, figures, and navigation; or planning future PDF and EPUB editions from the same format-neutral specification.
---

# Format Manuscript

Turn an unchanged manuscript into a deliberately designed publication artifact. Own format analysis, specification, approval, and cross-format consistency; let the appropriate format skill own file construction and technical verification.

## Governing Contract

1. Preserve manuscript wording, order, and section identity. Formatting authority is not editorial authority.
2. Determine intended use before typography. Submission, editorial-review, and reader-facing editions require different conventions.
3. Inspect available project state before asking questions. Reuse unchanged genre, type, audience, title, author, structure, and prior formatting decisions.
4. Infer a complete recommended system from the draft. Ask only about consequential choices the evidence cannot safely resolve.
5. Persist one format-neutral specification and bind it to the exact manuscript identity or fingerprint.
6. Obtain explicit approval before generating or replacing a formatted edition. A correction revises the proposal; it is not approval of the replacement.
7. Use real semantic styles and navigation structures. Do not simulate headings, lists, page numbers, or a table of contents with manually formatted text.
8. Keep format adapters separate. The approved content hierarchy and design intent may be reused, but format-specific measurements and mechanics belong to the output adapter.
9. Visually verify every final page or viewport through the governing output-format skill before delivery.
10. Use the shared interactive approval sheet as the review surface whenever it is available. Do not replace it with serial chat questions merely because the user asks to continue or go through the review list.

## Initialize or Resume

When a writable project root exists, preserve format-specific state under:

```text
manuscript-formatting/
|-- format-spec.md
|-- format-review.json
`-- outputs/
    `-- <format>/
```

When no writable root exists, use equivalent Codex artifacts. Do not place formatting state inside an editorial or query-package folder.

Inspect the manuscript, existing format specification, review state, project metadata, and requested deliverable. Report a compact freshness summary when reusable state exists. Refresh only changed or unsafe decisions; do not repeat intake because a new output file was requested.

When the designated input is a prepared manuscript, read its `work.json` and
current revision manifest under the sibling
[preparation contract](../prepare-manuscript/references/preparation-contract.md).
Use the verified chapter order and declared assets as the content inventory.
Maintain only `workflows.format-manuscript`, bound to the prepared revision and
edition scope, with `format-spec.md` as the state locator. If preparation is needed,
delegate it to [prepare-manuscript](../prepare-manuscript/SKILL.md). The shared
status is a summary; design approval and output verification remain mandatory.

Read and reuse the [shared manuscript metadata](../prepare-manuscript/references/manuscript-metadata.md)
for title, credits, language, type/form, and edition context. Preserve user edits
and the proposed/confirmed distinction; save explicit corrections under that
contract. Record consumed fields in the format specification and refresh affected
title pages, credits, or edition decisions if they change. Layout settings and
design approvals remain formatting state, not shared descriptive metadata.

## Establish the Edition Profile

Read [references/formatting-spec.md](references/formatting-spec.md) in full before creating or revising a specification.

Determine:

- output format and intended use;
- work type, genre, readership, and stylistic character;
- manuscript structure and valid TOC hierarchy;
- front matter, back matter, notes, figures, tables, captions, and special text forms;
- whether an industry convention or supplied template controls the design.

Present the inferred work type, genre, readership, stylistic character, and intended use as a compact classification and ask the user to confirm or correct it. When the shared approval interface is available, make this classification a consequential `FM` item in that interface instead of creating a separate chat-only gate. Reuse an existing confirmation without asking again only when its manuscript and project inputs remain unchanged.

Classify the edition as `submission`, `editorial-review`, or `reader-facing`. Explain any conflict between the requested features and the controlling convention. A novel submission, for example, normally should not gain a TOC merely because the software can create one; confirm the exception or recommend a separate reader/review edition.

## Build the Format Specification

Create or update `format-spec.md` using the reference schema. Select the lightest coherent system that suits the manuscript. Resolve page geometry, fonts and fallbacks, type scale, paragraph model, chapter openings, scene breaks, heading hierarchy, TOC behavior, page furniture, figures, tables, notes, accessibility, and format-specific exceptions.

Prefer installed, legible, and portable fonts. Never claim a font is available or embeddable without verifying it in the active environment. Preserve poetry lineation, dramatic formatting, code, letters, quotations, and other structurally meaningful forms rather than forcing all text into the main prose style.

Set specification status to `proposed` until the human gate passes.

## Confirm the Design

When the sibling [review-approval-sheet skill](../review-approval-sheet/SKILL.md) is available, read it in full and create synchronized `format-review.json` state. Treat its rendered interactive interface as required for multi-item format review. Use stable `FM###` items for consequential design groups rather than asking the user to approve every numeric token separately. Show the recommendation, evidence, alternatives when useful, and downstream effect.

Validate and render the latest saved revision before soliciting dispositions. If the user asks to `review`, `continue`, `go through the list`, `show the remaining items`, or equivalent, rerender the current revision in the shared interface and return that interface. Do not substitute a one-item-at-a-time chat prompt, a Markdown checklist, or prose summary unless the user explicitly requests a text fallback or the interface cannot be validated or rendered.

Present the rendered fragment in the same response with `::codex-inline-vis{file="<basename>.html"}` on its own line. Store it in the active thread visualization directory and use its basename in the directive. A local path or Markdown link does not satisfy this presentation gate.

After every valid disposition batch, let the formatting workflow update the authoritative specification, increment the review revision, and render a new open-only interface containing only pending or reopened items. Never direct the user back to a stale HTML revision or make resolved items actionable again. A batch may contain one item or many; use the same parser and revision rules in either case.

Use `approve`, `modify`, and `revise recommendation`. Require exact replacement instructions for modification or revision. Treat `revise recommendation` as reopening the item. After all current items resolve, require separate final closure of the complete specification.

Treat the shared interface as unavailable only when its skill, validator, renderer, inline directive, or active display surface cannot be used successfully. In that case, present the same compact specification and revision identity in chat and require explicit approval. A link alone is not an interactive fallback. Persist the decision in `format-spec.md`. Never infer approval from silence, discussion, or a request to continue.

After closure, set the specification to `approved` with its manuscript identity, approval date, and review revision.

## Generate the Requested Format

### DOCX or Word

Use the available Documents skill for construction and follow it in full. Provide the approved specification, unchanged manuscript content, structural map, output location, and any controlling template.

If the Documents skill or its required render workflow is unavailable, mark generation `blocked-adapter` and explain what capability is missing. Do not replace it with an unverified ad hoc DOCX builder.

Require:

- real Word paragraph and character styles;
- correct section breaks and page geometry;
- real heading levels matching the approved hierarchy;
- automatic page numbering and consistent headers or footers;
- a visible, accurate TOC at the approved depth;
- captions and cross-references when figures or tables require them;
- structural audits and render-to-PNG inspection of every page.

Prefer a dynamic Word TOC when fields can be refreshed before delivery. When reliable field refresh cannot be guaranteed, use the Documents skill's static linked-TOC workflow. Never deliver a blank, placeholder, or knowingly stale TOC.

### PDF

When requested, derive PDF from the approved specification and a verified source edition. Use the appropriate PDF or document-export workflow and visually inspect every page. Record unavoidable pagination or font changes as format-specific exceptions; do not silently alter the general specification.

### EPUB or another format

Reuse the approved semantic hierarchy and design intent only when an appropriate output skill or validated adapter is available. Until then, the specification may be prepared, but mark generation `blocked-adapter` rather than inventing an unverified conversion workflow.

## Validate and Deliver

Before delivery, verify:

- the output is bound to the approved specification and unchanged manuscript;
- no prose or structural content changed without separate authority;
- every expected component appears exactly once and in order;
- styles, spacing, chapter openings, scene breaks, page furniture, and special forms match the specification;
- TOC entries, levels, links, and displayed page numbers are accurate for the delivered edition;
- there are no blank placeholders, font substitutions, clipping, collisions, stranded headings, or accidental blank pages;
- the governing format skill's structural and visual QA passed.

Save the final artifact beneath `outputs/<format>/` or as a Codex artifact. Report the selected profile, specification revision, output format, TOC method, and verification result.

## Invalidation

A manuscript-identity or structural change invalidates navigation, pagination, and the affected format outputs. A content-only correction may also change pagination. Reuse unaffected design decisions, refresh the structural map, regenerate the output, and repeat format-specific QA. A deliberate design change reopens only affected `FM` items and dependent outputs.
