# Shared manuscript metadata

Read this contract whenever creating, inferring, editing, or reusing manuscript
metadata. It applies to preparation, editing, translation, querying, and formatting.
The canonical values live in `work.json.metadata`; local workflow records may
snapshot consumed values but must not establish competing shared authorities.
The schema is [manuscript-metadata.schema.json](../schemas/manuscript-metadata.schema.json).
New work records use `schema_version: 2`. Revision manifests remain version 1.

## Common fields

| Field | Meaning |
| --- | --- |
| `title`, `subtitle` | The designated manuscript's title and subtitle, when known. |
| `contributors` | People credited on this manuscript: stable local `id`, credited `name`, and one or more roles: author, translator, editor, illustrator, contributor. A credited name may be a pen name; do not infer a legal identity. |
| `original_language` | Original work's language, when explicitly established. |
| `manuscript_language` | Language of the actual designated manuscript. A translation can differ from the original language. |
| `work_type` | Broad type: fiction, memoir, nonfiction, poetry, drama, mixed. |
| `form` | Novel, novella, short_story, collection, essay, poem, play, screenplay, book, mixed, other. A collection's contents may be described in keywords. |
| `genres` | Ordered genre/subgenre terms, primary first. Use recognizable terms; no universal publishing taxonomy is imposed. |
| `audience` | Adult, young_adult, middle_grade, children, general, academic, professional. This is a positioning hypothesis until confirmed. |
| `keywords` | Concise topical descriptors supported by the text. |
| `description` | Short factual description; not a replacement for an approved story ledger, synopsis, or editorial assessment. |
| `edition.label`, `edition.status` | Supplied edition label and draft, complete_draft, revised, or final status. Preparation readiness does not establish finality. |
| `series.name`, `series.position`, `series.relationship` | Series name, numeric position, and standalone, series_potential, or part_of_series relationship. |
| `extent` | Word count, non-whitespace character count, unit count, counting method, source revision, and exact scope. Counts describe that manuscript revision, not every translation or edition. |

Use null for unknown scalar values and empty lists for unknown contributors,
genres, and keywords. Keep all schema keys. `extent` may be null. Names and
classifications are Unicode text; language tags use forms such as `zh`, `zh-Hans`,
or `en-US`. There is one contributor entry per credited person; combine roles
and preserve their stable local ID when changing a name.

## Fill missing values from the text

Studio intake requires only the manuscript. Do not ask users to complete a
metadata form before extraction. Produce draft metadata alongside the verified
text; users correct or complete it at the existing Overview audit. Optional
unknowns do not block preparation. Later corrections use the same editor.

Preparation includes descriptive metadata analysis, not literary-quality review.
After source verification, read the available prepared text and automatically
deduce missing descriptive fields. Do not send a questionnaire for facts already
provided or inferable from that text.

1. Reuse supplied values and existing edits. Inspect `metadata_provenance` before
   proposing anything; a deliberately cleared value is also an edit to preserve.
2. Extract explicit title/subtitle, bylines, contributor roles, edition statements,
   original-language statements, or series declarations when actually present.
   Use their real textual evidence, not filenames or document-creator properties.
3. Infer manuscript language, broad type, form, genres, keywords and a short
   description where the manuscript supports
   them. Use the full verified scope, not keyword matching or one isolated scene.
   A selected-chapter sample cannot establish whole-work form or resolution.
   Keep uncertain classifications provisional and explain alternatives.
4. Do not infer authorship from narrator identity, original language from the
   current language, publication/rights status from content, or an actual title,
   series name/position, or edition-finality claim without explicit evidence.
   Leave unsupported fields unknown; do not fabricate values to complete the form.
5. Write an evidence-bound proposal array and apply it through the helper below.
   Every extracted/inferred value remains `proposed` until the user confirms it.
   Record confidence and a rationale; confidence is not approval.
6. Compute extent with the helper. Its method includes all prepared units and
   rendered Markdown text/code but excludes markup, link destinations and image
   alt text. It leaves word count null for scripts needing language-specific
   segmentation instead of reporting Chinese character counts as English words.
   A different verified counting method or an author-supplied count can be saved
   explicitly with its method and scope.

Keep preparation `in_progress` while enriching an otherwise verified revision.
Then run the preparation validator and mark it ready when the source checks pass.
Unconfirmed genre/audience and unknown optional metadata do not block extraction
readiness. A title present in the source must populate metadata before ready,
unless the user explicitly cleared it; a generated `supplied_title` for an
untitled source is not evidence of an actual title. Manuscript language is required.
Present the resulting values together, identifying inferred, unknown, and stale
fields, and invite corrections without adding a mandatory metadata approval gate.
Existing workflow-specific approval gates still apply. Intake may leave language
null. Infer it from the prepared text through the evidence-bound enrichment step;
if the language is uncertain or multilingual without a clear primary language,
keep preparation blocked and request clarification rather than choosing a default.

## Audit fields and evidence

Every metadata field belongs to exactly one group; `scripts/prepare_metadata.py`
exposes them as `SUGGESTED` and `COMPUTED`. These are presentation/evidence
categories, not different owners or pre-preparation forms.

| Group | Fields | Who sets them |
|---|---|---|
| Review and complete | All fields other than manuscript language and extent | Preparation may extract explicit source statements, with evidence; supported descriptive inference is limited to work type, form, genres, keywords and description. Users correct or fill values in the post-preparation audit. Unsupported values remain unknown. |
| Computed | `/manuscript_language`, `/extent` | Language may be unknown at intake; preparation infers it from the supplied text with evidence before becoming ready. Extent is measured from the prepared revision. Neither is edited by hand in downstream workflows. |

Title/subtitle proposals require actual quoted source text, not a generated
filename heading. Contributor names must occur in quoted source credits and
roles must reflect explicit bylines/credits; never infer authorship from a
narrator, character, filename or document-creator property. Audience, edition,
series and original-language claims need explicit source statements, not
speculation about the manuscript. Users can supply or correct any audit field
with `set`, including a
title absent from the manuscript. User confirmation is sufficient grounding;
it needs no manuscript quote. Preserve supplied or confirmed values, including
deliberate clearing, before evaluating competing agent proposals.

## Draft output and reviewed shared metadata

In Studio, the preparation agent creates a fresh source-based draft. The host
does not give it a mutable prior-work-record file or require it to merge user
metadata. The shared library remains the single versioned authority.

- **New work:** present extracted/detected values, qualified suggestions and
  unknown fields together at the existing metadata audit. The user may correct
  values, add missing information, or leave optional fields unknown.
- **Re-preparation:** the host reads the immutable shared-library head and
  retains its existing reviewed values/provenance, including deliberately cleared
  values. Missing defaults without provenance can use new draft suggestions.
  Fresh language/extent describe the current prepared revision. Source
  discrepancies are shown at the same audit rather than delegated to an agent
  to resolve or overwrite.
- **Confirmation and later edits:** publish the effective record to the shared
  library. Downstream workflows consume it without another metadata questionnaire.
  Later corrections use the same Overview editor and create new versions;
  already-approved outputs retain their original snapshots.

For standalone use with an existing record explicitly supplied by the caller,
preserve existing values and provenance through the helper, including deliberate
clearing. Only enrich missing defaults. Do not treat source text as permission
to overwrite a user correction.

## Helper and proposal format

Install `requirements.txt` from this skill. Run commands from the skill directory
or use absolute script paths:

```text
python scripts/prepare_metadata.py migrate <work-root>/work.json
python scripts/prepare_metadata.py enrich <work-root>/work.json --proposals <metadata-proposals.json> --by prepare-manuscript
python scripts/prepare_metadata.py set <work-root>/work.json --field /genres --value-file <genres.json> --by user
```

`genres.json` contains a JSON value such as `["Historical fiction", "Literary fiction"]`.
`set` can replace any metadata field, including setting null or an empty list.
For edition/series use leaf paths such as `/edition/label`. Contributors, genres,
keywords, and extent are edited as whole values. Use `--reason` to explain an edit.
Skills may use `set` to persist an explicit user correction or confirmation with
their own actor name; they must not use it to confirm their own deductions.

Example proposal file (use actual revision, chapter, quotation, and evidence):

```json
[
  {
    "field": "/form",
    "value": "short_story",
    "origin": "inferred",
    "confidence": "medium",
    "basis_revision": "r0001",
    "evidence": [
      {
        "chapter_id": "story",
        "locator": "Final paragraph; assessed with the complete standalone unit",
        "quote": "He closed the gate behind him."
      }
    ],
    "rationale": "The complete manuscript develops and resolves one compact narrative arc."
  }
]
```

The preparation agent performs semantic inference; the Python helper does not
pretend to classify literature using keyword heuristics or require a separate
model/API. It verifies the cited revision, chapter, and exact quote, validates
values, computes extent, and fills only absent fields. Evidence matching makes
the deduction auditable; it does not prove the interpretation correct.
Running `enrich` without proposals computes missing extent and reports remaining
missing fields; that alone does not complete the skill's semantic analysis.

## Editability, provenance, and updates

Every metadata value remains editable, including extracted and computed values.
Users can edit `metadata` directly or use `set`. Direct edits are detected on the
next helper operation through value hashes and protected from automatic filling,
including deliberately cleared fields. Their author-confirmation status remains
unknown until explicitly confirmed. The helper never overwrites populated fields,
even inferred ones, during enrichment.

`metadata_provenance` is keyed by the metadata-relative field paths above. Each
entry records origin (`provided`, `extracted`, `inferred`, `computed`, `user_edit`,
or `legacy`), review status, confidence, source revision, textual evidence,
rationale, value hash, timestamp, and actor. An untouched null/empty field needs
no entry. Do not change provenance to claim a user confirmation that did not occur.
Direct edits to a previously empty, untracked value are preserved as provided
information with unknown confirmation history.

Any skill may contribute missing evidence-bound metadata or save explicit user
edits under this contract. Preparation initializes the record; it is not the only
permitted metadata writer. Reread the latest record and preserve all other fields.
The helper serializes its writers, checks for intervening edits, validates before
replacement, increments `record_revision`, and stores the preceding record under
`metadata-history/`. It never changes source files, published revision manifests,
or another workflow's status/approvals. A concurrent-edit error means reread and
retry; never force an older whole-record copy over newer state.

When source revisions change, source-bound metadata becomes stale. Retain the old
value and provenance until reassessed or explicitly corrected; do not silently
replace user decisions. An old extent must not be presented as the current count.
To recalculate it deliberately, remove its value AND provenance entry, then enrich;
ordinary clearing through `set` is protected and is not a request to refill it.

## Reuse by every workflow

Read shared metadata and provenance before asking intake questions or generating
local metadata. Reuse facts, and treat inferred classifications as proposals.
When a workflow's source analysis suggests a different populated value, show the
discrepancy and preserve the current value until the user requests or confirms a
change. Query-specific emphasis, prose voice, detailed plot claims, biographies,
rights, agent research, and workflow approval decisions stay in their owning
records. A description or genre proposal is not approval of a query story claim.

Record the work locator, metadata record revision, prepared revision, and the
metadata fields/values actually used in the workflow's own manifest/state.
Before reuse, compare those consumed values, not a hash of mutable `work.json`.
A metadata-only edit does not change the source revision or invalidate unrelated
source-grounded approvals. Each workflow marks its own dependent artifacts stale
when consumed values change: for example, a new title affects a query/title page;
a language correction must be reconciled with translation configuration.
Refresh only the affected decisions and outputs.

Version-1 records remain valid for reading. Explicit migration preserves title,
author names, source language as manuscript language, type, genre, edition label,
work identity, source revisions, and workflow state. It does not assume original
language or invent confirmation history. Do not migrate archived runs whose
pinned validator only supports version 1; start a current package when needed.
