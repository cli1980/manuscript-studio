---
name: prepare-manuscript
description: Discover manuscripts within a user-designated location, identify the authoritative work and requested scope, extract verified chapter-based UTF-8 Markdown, and maintain editable shared manuscript metadata with evidence-bound inference of missing descriptive values and downstream status. Use before literary editing or translation, when preparing a PDF, DOC, DOCX, text, or Markdown manuscript for downstream workflows, or when existing prepared source data or shared metadata must be verified, enriched, or refreshed.
---

# Prepare Manuscript

Own manuscript discovery, extraction, structural inventory, and preparation
provenance. Produce a neutral source package for downstream skills. Do not edit,
translate, assess literary quality, format an edition, or approve another workflow.

Read [the preparation contract](references/preparation-contract.md) before creating
or changing project files. Use [work.schema.json](schemas/work.schema.json) for
the shared work record and [revision.schema.json](schemas/revision.schema.json)
for each prepared source revision.
Read [the shared metadata contract](references/manuscript-metadata.md) before
recording or inferring metadata. Use schema-version-2 work records for new packages.

## 1. Resolve the input location and output destination

Obtain a specific source file, directory, attachment, or connected-storage
location from the user or an existing explicit project instruction. Record its
exact locator and whether recursive discovery is authorized. If the location is
missing, ask for it. Do not search the user's home, other projects, connected
drives, or Library outside the designated location. Do not follow links into
another location without explicit authorization.

Identify a separate writable preparation destination. Keep the prepared package
outside the authoritative source location and outside editorial, translation,
formatting, or querying output directories. A neutral sibling directory in a
project is suitable. If only task artifacts are writable, use the actual artifact
location supplied by the environment; do not invent one.

Discovery and preparation never grant permission to change the source. Do not
initialize Git or commit as part of this skill; each downstream workflow retains
its own version-control policy.

## 2. Identify works and select the authoritative source

Inventory manuscript candidates only inside the designated location. Record their
formats, languages, work identity, apparent version, and available scope.
Distinguish different works from different editions, translations, summaries, and
exports of the same work. Never merge candidate versions or choose a newer-looking
file merely by filename or modification time when authority is ambiguous.

For multiple works, create one package and stable `work_id` per work. Resolve
ambiguous source selection with the user. Record `selection_status: confirmed`
only after the choice follows an explicit designation or confirmation.
Preserve supplied metadata. Extract explicit credits and titles, and infer missing
descriptive values from verified manuscript text under the shared metadata
contract. Keep unsupported identities or edition claims null/empty; do not infer
facts from folder names alone.

Confirm whether the requested scope is the whole work or named complete chapters.
An incomplete excerpt is not a complete chapter. Record missing material as a
blocker; do not fabricate it from translations, summaries, or other editions.

## 3. Extract a standard chapter set

Use the appropriate document, PDF, OCR, or text workflow for the selected source
format. If a required adapter is unavailable, record a blocker and stop extraction.

Every prepared text artifact is a chapter-based `.md` file: UTF-8 without BOM,
LF newlines, and source-order filenames `chapters/0001.md`, `0002.md`, and so on
inside a new revision directory. This contract applies even when the input is
already text or Markdown; verified existing chapters may be copied into the
standard layout without re-extracting them.

Find real chapter or section boundaries from the source. Do not split by token,
page, or word limits. A verified self-contained work without chapters is one
`standalone` unit. Front and back matter must be included as explicitly typed
units when preparing the whole work. Follow the Markdown preservation rules in
the contract, including notes, poetry lineation, tables, and non-text anchors.

Preserve wording, punctuation, paragraphing, order, intentional irregularities,
and meaningful formatting. Resolve extraction corruption only when the received
source makes the correct representation objectively clear, and record the repair.
Do not silently copyedit, modernize, translate, expand, or improve the prose.
Keep unresolved OCR, missing-page, boundary, or structural problems as blockers.

## 4. Verify, enrich metadata, and publish the prepared revision

Compare every extracted unit with its source locators. Verify that the requested
scope is represented exactly once, with no missing, duplicated, or reordered
content. Inspect source-dependent formatting; byte hashes alone cannot establish
extraction fidelity.

Record the extraction tool and method, source fingerprints or provider versions,
ordered chapter IDs and paths, source spans, chapter and asset hashes, verification
evidence, and unresolved issues in the revision manifest. Use `verified` only
after the source comparison and coverage checks pass.

While preparation remains `in_progress`, analyze the verified text for missing
language, type, form, genre, audience, keywords, and description; extract other
fields only where explicitly supported. Write the evidence-bound proposal JSON
specified in the metadata contract and run `scripts/prepare_metadata.py enrich`
with that file. The helper computes missing extent and preserves supplied values
and edits. Inference is part of this skill's reading task, not a keyword-based
guess in the validator. Report unsupported fields as unknown and inferred values
as proposed; do not fabricate values or require an extra blanket approval.
When the user edits metadata, save the correction through the helper or reconcile
their direct edits; do not re-extract unchanged chapters.

Validate before marking preparation ready:

```text
python scripts/validate_preparation.py <work-root>/work.json
```

For accessible local source files, also use `--check-sources`. Install the
validator's dependencies from this skill's `requirements.txt` if needed.
If validation cannot be performed, record the limitation and keep preparation
blocked rather than declaring it verified.

Publish the verified revision and update `work.json`. Reuse an unchanged verified
revision. Never overwrite a published revision: source changes, corrected
extraction, or changed boundaries require a new revision, with dependent workflow
records marked stale.

## 5. Hand off

Provide the work-record locator, current revision manifest, ordered chapter
locations, verified scope, and any limitations. Downstream workflows consume the
prepared chapters and use the shared status contract; preparation never marks
editing, translation, querying, or formatting complete.

Prepared source remains immutable. Editors use separate working copies.
Translators write translated outputs separately. Neither preparation readiness
nor a downstream status summary substitutes for the originating workflow's
approval records or source-update authorization.
