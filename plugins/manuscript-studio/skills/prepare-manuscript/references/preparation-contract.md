# Shared manuscript preparation contract

## Package and authority

Use one package per work in a user-designated neutral destination:

```text
prepared-manuscripts/
  <work-id>/
    work.json
    revisions/
      r0001/
        manifest.json
        chapters/
          0001.md
          0002.md
        assets/
```

`assets/` is optional. All prepared manuscript text is in chapter-based Markdown;
the source may still be PDF, DOC, DOCX, text, Markdown, or another supported format.
Metadata is stored separately and must not be inserted into the literary text.
Paths in revision manifests are relative to that revision directory, use `/`,
and cannot contain traversal components, absolute paths, or links outside it.

The received original remains authoritative and read-only during preparation.
The prepared package is a verified source representation, never an editorial
working copy. Keep it outside the original source location and all downstream
working/output directories. It can be shared by several workflows without letting
one workflow's edits replace another workflow's source.

## Work record

`work.json` follows [work.schema.json](../schemas/work.schema.json):

Use [work.example.json](work.example.json) as a not-started template. Replace its
example work ID, location, and timestamp with actual project values; the template
is not evidence that a work has been discovered or prepared.

- `work_id`: stable lowercase identifier, independent of a filename or title edit.
- `record_revision`, `updated_at`: revision and time of this shared metadata record.
- `metadata`: common editable descriptive fields defined by the
  [shared metadata contract](manuscript-metadata.md), including credited contributors,
  manuscript/original languages, type/form, genres, audience, edition, series,
  and revision-scoped extent. Unknown values stay null or empty.
- `metadata_provenance`: field-level evidence, inference/review status, confidence,
  actor, and value hashes. New work records use schema version 2; legacy version-1
  records remain readable and may be explicitly migrated with `prepare_metadata.py`.
- `discovery`: the exact user-designated location, its kind, recursive permission,
  whether source selection is confirmed, and selection notes. A location may
  contain several works; each gets its own work record.
- `preparation`: readiness, current revision ID, and blocking reasons.
- `workflows`: separate records for editing, translation, querying, and formatting.

Preparation states:

| State | Meaning |
| --- | --- |
| `not_started` | Location and metadata recorded; no usable preparation yet. |
| `in_progress` | Discovery, extraction, or verification is underway. |
| `blocked` | A source, adapter, boundary, coverage, or validation problem prevents handoff. |
| `ready` | The confirmed requested scope has a verified, validated chapter set. |
| `stale` | The current package no longer represents the current designated source. |

Before a revision exists, `current_revision` is null. Once assigned, it is a
stable revision identifier such as `r0001`. The corresponding manifest is always
`revisions/<current_revision>/manifest.json`; do not add competing path aliases.

Initialize each downstream workflow record as:

```json
{
  "status": "not_started",
  "basis_revision": null,
  "scope": null,
  "operation": null,
  "state_locator": null,
  "updated_at": null
}
```

## Revision manifest and extraction

`manifest.json` follows [revision.schema.json](../schemas/revision.schema.json).
It records the work/revision identity, creation time, source inventory, requested
scope, ordered chapter records, optional assets, extraction method, and verification.

Each selected source has a stable `source_id`, exact file/attachment/provider
locator, format, and identity. Use a SHA-256 hash of the original bytes when
available; otherwise record an actual durable provider version. A display title
or modification date alone is insufficient. Do not fabricate a checksum for a
document that was not accessible.

For local files/directories, use absolute native filesystem paths for discovery
and source locators. For attachments or connected storage, use the actual opaque
provider locator and version; verify it through the provider rather than treating
it as a local path.

For each chapter unit, record a stable `chapter_id`, order within the prepared
scope, original chapter number/title when available, role, Markdown path, SHA-256
of its saved bytes, source spans, and verification status. `chapter_id` represents
the source unit; filenames represent its order in this prepared revision. Keep
IDs stable when the same source chapter survives a new revision. Do not reuse an
old ID for a materially different boundary or chapter.

Source-span locators must identify the boundaries, using page/paragraph ranges,
source headings, or opening and closing source words as available. A filename
alone does not identify a chapter's coverage.

Chapter files use UTF-8 without BOM, LF newlines, and a final LF. Names are
`chapters/0001.md`, `0002.md`, etc., matching consecutive source-order entries.
Preserve actual chapter numbers and titles in metadata even when a selected
chapter set starts at chapter 12 or uses Roman numerals.

Preserve paragraphs, punctuation, dialogue, meaningful spacing, italics, scene
breaks, poetry lineation, notes, tables, and original headings using ordinary
Markdown. Source headings may become Markdown headings without duplicating their
wording. Do not add generated chapter titles, YAML front matter, analysis,
glossary entries, or provenance headings to chapter bodies. Keep footnotes with
the relevant unit and preserve their text and references.

Keep non-text anchors in their source positions. Store necessary image or other
non-text assets in `assets/`, with hashes and source locators, and reference them
from the chapter. Do not invent descriptions of inaccessible illustrations.
If meaningful content cannot be faithfully represented, record a blocking issue;
do not silently discard it or replace chapter Markdown with a PDF/DOCX deliverable.

A self-contained short story, essay, or poem without chapters is one `standalone`
unit. Front and back matter are typed units in the same ordered Markdown set.
A partial excerpt from a larger chapter is `incomplete`, not a standalone work.
Do not manufacture chapters to fit processing limits.

`scope.kind` is `whole_work` or `selected_chapters`; `chapter_ids` lists the
prepared units in order. Selected-chapter preparation may be ready for those
complete chapters, but must not support a whole-work completion claim.

Verification records name the verifier, date the source comparison, state whether
the requested scope is complete, and enumerate warnings or blockers. Check the
chapter bodies against source locators for exact coverage and structural fidelity.
The validator verifies schema, identifiers, paths, hashes, and state consistency;
it cannot independently prove that an extraction faithfully reproduces a PDF.

## Downstream status and ownership

Each workflow owns only its own workflow summary entry. Any skill may also enrich
missing shared metadata or persist explicit user edits under the
[metadata update rules](manuscript-metadata.md#editability-provenance-and-updates);
this does not authorize changing another workflow's state or approval records.

- `status`: `not_started`, `in_progress`, `awaiting_approval`, `blocked`,
  `completed`, or `stale`.
- `basis_revision`: the prepared source revision used for that operation.
- `scope`: whole work or selected chapter IDs.
- `operation`: the actual operation, such as `line-edit`, `chapter-translation`,
  `static-query-package`, or `docx-edition`.
- `state_locator`: the real path or artifact locator of its authoritative
  workflow records. It is a pointer, not permission to access unrelated files.
- `updated_at`: timestamp of the status update.

Set `in_progress` when the operation starts, `awaiting_approval` at its existing
human gate, and `blocked` for a concrete blocker. Set `completed` only after that
operation's own completion/verification gate passes. Never infer these transitions
from file existence or from another skill's status.

An active/completed operation must refer to the current ready preparation.
Preparation readiness is not approval, completion of another workflow, or
permission to alter a manuscript. `completed` applies only to the stated
operation and scope; it does not mean every editorial service or every chapter
has finished. Detailed passage, proposal, translation, and approval state remains
in the owning workflow's existing records.

`basis_revision` identifies the prepared-source dependency, not every derived
input. A workflow's own records must also bind translated deliverables, edited
drafts, or other designated inputs by identity/hash. A change to a translated
chapter can invalidate its formatted edition even when the original prepared
revision is unchanged. Record the affected workflow as stale without falsely
marking the unchanged original preparation stale.

Reread `work.json` before updating it. Merge only the fields owned by the operation,
preserve the other workflow records, increment `record_revision`, and update the
timestamp. Do not overwrite another workflow's newer state.
The approval-sheet helper does not own a separate manuscript progress record.

If the shared record is read-only, preserve the proposed status update in the
owning workflow's artifacts and report that shared-metadata synchronization is
pending. Do not bypass permissions or claim the work record was updated.

## Refresh and legacy projects

Reuse a current verified package. On a source or extraction change, preserve the
old revision, mark preparation stale, and mark previously started dependent
workflows stale while retaining their old `basis_revision` and state locators.
Create a new revision, re-extract or copy verified unchanged units, verify its
coverage, and publish it before resuming affected work. Only the owning workflow
may revalidate its decisions and move its status out of stale.

Reassess source-bound metadata against the new revision and mark old inferences
and counts stale until refreshed. Metadata-only edits increment the work record
revision but do not create a source revision; consumers check the metadata fields
they actually used and refresh affected outputs under the shared metadata contract.

For an older project containing `original_chinese/`, `original_<language>/`,
or `manuscript/chapters/`, verify those files against the designated original.
Copy only verified source-equivalent text into the standard prepared package and
record the original provenance. Do not rename or delete user files, discard
glossary/voice records, overwrite editorial working changes, or reset approvals.
Never promote an edited working copy to an original-language source merely to
avoid locating the original. Existing translated deliverable names remain stable.

Editing copies selected prepared chapters into its own `manuscript/chapters/`
working area and retains its two-location/Git-or-artifact rules. Translation reads
the prepared source revision and keeps `glossary.md`, `voice.md`, and
`translated_english/` in its translation project. Formatting can use the ordered
chapter/asset map. Querying may consume a neutral prepared package only when it
and its underlying original are explicitly designated as query inputs; editorial
reports and edited workspace manuscripts remain prohibited query evidence.
