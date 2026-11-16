# Interior-design proposal contract

[Schema](../schemas/interior-design-proposal.schema.json): JSON Schema draft
2020-12, contract interior-design-proposal/4. See the [example](proposal.example.json).
The example is synthetic: its illustrative hashes are not real preparation proof.

## Authority and form groups

Proposal objects are closed; vendor-profile data must match the bundled snapshot
and its canonical hash exactly. Unknown fields, approval receipts, production artifacts
and QA-success claims are rejected. Status is always proposed. This is a
standalone, reviewable design proposal that another tool may consume, not the
effective approved production specification. No workflow/run context is required
or stored in the proposal; callers keep their own execution lineage separately.

| Group | Contents |
| --- | --- |
| basis | Exact preparation/metadata identity and optional artifact references |
| vendor_profile | Exact selected vendor/binding data, provenance and canonical hash, or null; see the [profile contract](vendor-profiles.md) |
| reading | Essence, genre, synopsis, themes, voice/vibe, audience, structure, evidence and uncertainty |
| author_preferences | Supplied imprint/ISBN, revisions, series, liked references and things to avoid |
| edition_brief | Purpose and requested deliverables/vendor/product/trim |
| design_system | Geometry, named font/paragraph styles, hierarchy, navigation and page furniture |
| text_roles | Whole-paragraph semantic roles, narrative function, catalogued occurrences and paragraph-style mapping; may be empty |
| evidence | Stable-ID sources for facts, analysis and recommendations |
| recommendations | Stable-ID rationale/evidence addressing design groups through JSON Pointer |
| questions | Necessary author-input or design-choice questions only; may be empty |

## Units and identities

`edition_brief.purpose` records the supplied intended use: `print-ready`,
`submission`, or `editorial-review`. Use it to guide the design and its rationale;
it is not a content classification or fixed layout preset. `print-ready`
describes the requested edition, not successful production or print validation.

Millimeters express geometry/indentation; points express type/paragraph spacing.
Line spacing has explicit multiple or exact-point mode. Suggested fonts/fallbacks
are not availability, licensing or embedding attestations. Values are not proof
that a producer supports the requested treatment.

basis.preparation binds work.json bytes/record revision, current revision/manifest
bytes, scope/order, language and unit hashes. Its work-record hash includes the
consumed metadata: no second metadata authority is introduced. External references
carry supplied locator/hash or null; never invent a hash for inaccessible data.
The validator does not automatically open these locators or fetch URLs.

### DOCX widow/orphan policy

`widow_lines` and `orphan_lines` accept non-negative integers, including zero.
For DOCX, IDP-C28 explicitly accepts this conversion:

```text
widow_control = bool(widow_lines or orphan_lines)
```

Both zero disables the combined control; either nonzero enables it. Thus `1/1`,
`3/2`, `0/3` and `7/0` all enable the same native DOCX protection. They do not
promise their numeric first/last-line thresholds, and a mixed pair cannot
independently disable just one side. This is an approved backend-specific
normalization policy, not an unsupported-value error or a silent approximation.
The effective native plan must record the boolean and policy identity.

Other backends may have different declared mappings; InDesign's future numeric
behavior is not implemented or promised here. Other unsupported settings still
require explicit diagnostics. The proposal validator checks the input domain,
not native construction, pagination or rendered output.

### Whole-paragraph roles; source-owned inline formatting

Each role occurrence identifies exactly one whole paragraph:

```json
{
  "chapter_id": "chapter-one",
  "chapter_sha256": "<exact unit hash>",
  "paragraph_index": 2,
  "paragraph_sha256": "<hash copied from paragraph catalog>"
}
```

Obtain these values with `validate_proposal.py --work WORK.json --list-paragraphs`.
Catalog contract `interior-design-paragraphs/1` numbers CommonMark
`paragraph_open` and `heading_open` blocks together, one-based in source order
within each unit, including paragraphs inside quotes/lists. Headings are whole
paragraph blocks for structural styles. Blank lines, thematic breaks, HTML
blocks and fenced/indented code blocks are not numbered paragraphs.

The catalog uses `MarkdownIt("commonmark")` without extensions. Its `markdown`
is the block's inline-token content, retaining inline markers, escapes, entities
and internal line breaks after CommonMark's container/line-ending processing.
`paragraph_sha256` hashes that content encoded as UTF-8, not rendered/plain text.
`chapter_sha256` still binds the original, unchanged unit bytes. Copy both hashes
from the helper; do not search by content or count physical lines. A paragraph
can span lines, and identical paragraphs have distinct indices.

A multi-paragraph role lists one occurrence per paragraph. A paragraph may have
only one role assignment, including across roles. Ordinary unassigned paragraphs
use body/structural heading defaults, so no invented special role is necessary.
Byte/character ranges and inline roles are not accepted in `text_roles`.

Inline emphasis and other supported inline constructs come from the original
Markdown syntax, not model-generated role assignments. Preserve those markers;
do not invent wrappers or widen a marked phrase into a paragraph classification.
Native construction must preserve explicit source emphasis and otherwise inherit
the approved paragraph style. This contract does not implement that producer.

`reading.important_excerpts` remain evidence-only zero-based UTF-8 byte ranges:
`start_byte` inclusive, `end_byte` exclusive, with `text_sha256` over exact bytes.
They are not formatting assignments and do not restore inline roles.

Canonical semantic roles belong to preparation, with editing/translation owning
their output mappings. This proposal-v4 contract has local role IDs and paragraph
references only, not canonical annotation references or transfer lineage.
Upstream annotation tooling and downstream propagation require coordinated
schema/workflow changes. Verified identities do not prove a classification correct.

### Explicit headers and footers

`design_system.furniture` replaces the former `running_heads`/`folio_position`
switches with native-capability-based definitions:

- `different_odd_even` is document-wide.
- `default_section` supplies complete section settings: header/footer distances
  in mm, `different_first_page`, and `headers`/`footers`.
- Each group defines `default`, `even` and `first` parts. Default applies to
  odd pages when odd/even differs, otherwise both. First applies to the first
  page of a Word section, not arbitrary source paragraphs or physical blank pages.
- Each part has `link_to_previous` and `paragraphs`. A linked part inherits the
  preceding section's corresponding part and must have no local paragraphs.
  An unlinked empty list deliberately creates a blank part, not inheritance.
  The first effective section cannot link to a previous one.
- Each paragraph names an existing `style_id`, explicit `alignment` and `content`.
  Styles may use the new `header`/`footer` roles. Font/spacing come from that
  named paragraph style; local alignment takes precedence over style alignment.
- Inactive even/first parts must be empty and unlinked. There is no silent
  preservation of requested content in a disabled variant.
- `section_overrides` contains unique, preparation-bound `chapter_id` selectors
  and complete replacement `settings`, not partial merges. A native section
  boundary must exist at the selected unit; do not use final paragraph indices
  or section ordinal guesses. Common defaults apply to units without overrides.

Content is selected explicitly, with no competing raw text on a named preset:

```json
{"style_id": "running-head", "alignment": "left", "content": {"preset": "book-title"}}
```

| `content.preset` | Effective template |
| --- | --- |
| `book-title` | `{work_title}` |
| `chapter-name` | `{chapter_title}` |
| `author` | `{author}` |
| `page-number` | `{page}` |
| `page-x-of-y` | `Page {page} of {page_count}` |
| `custom` | Required `content.template` |

The schema's `furniture_content.x-preset-templates` is the canonical expansion
table shared by review and formatter. A named preset must not carry `template`.
Custom templates must be nonblank and safe. None means
`{"link_to_previous": false, "paragraphs": []}`, not an empty paragraph, a
`none` paragraph preset or inherited content. Selecting content does not set an
automatic book-layout, font or numbering policy; those settings stay explicit.

Proposal `/4` replaces `/3` paragraph `text` with `content`. Older proposals
need regeneration and review, not a guessed migration. Preset expansion happens
before metadata, unnumbered-front-matter and field checks. Missing consumed
metadata still fails. The exact selected content and resolved template enter
the authorized formatter plan.

Text is literal, not Markdown. The only custom-template placeholders are:

| Token | Binding |
| --- | --- |
| `{work_title}` | Exact prepared metadata title |
| `{chapter_title}` | Selected prepared unit's title |
| `{author}` | Prepared contributors with role `author`, names in source order joined with `, ` |
| `{page}` | DOCX `PAGE` field instruction |
| `{page_count}` | DOCX `NUMPAGES` field instruction, total document pages |

Doubled braces escape literals: `{{page}}` prints `{page}`. No positional names,
attribute/index access, conversions, format specifiers, tabs or control characters
are allowed. Use multiple paragraph objects for multiple lines. Missing consumed
metadata fails validation with `--work`; an inherited part keeps the predecessor's
content rather than rebinding it to the new chapter.

`front_matter_numbering` and `body_numbering_start` remain sequence settings.
For `none`, front-matter parts must not display `{page}`: author an explicit
blank/text-only override rather than silently remove a field. Roman/Arabic
definitions and body restarts are written as DOCX settings, not verified numbers.
Distances must be non-negative and less than page height; those checks do not
prove that rendered furniture fits or does not overlap body text.

The POC constructs definitions only. It does not refresh fields, paginate, render
PDF or certify suppression on renderer-generated blank pages. This contract does
not support arbitrary positioned objects, images, tables or executable fields.
Contracts `/1` and `/2` require regenerated proposals; no compatibility aliases
or conversion of the old coarse switches are provided.

Prepared-text evidence uses the manifest-relative unit locator, for example
revisions/r0001/chapters/0002.md, and its complete unit hash. Metadata evidence
uses a /metadata/... JSON Pointer and the work.json hash. --work checks these
references too; other external evidence still requires host verification.

Evidence/style IDs are unique and references resolve. Body style is singular;
heading levels are unique. Recommendation pointers address existing design_system
groups; questions may address another proposal field or null for a general issue.
Alternative choices are explanatory text, not unvalidated production settings.

## Supplied facts versus analysis

Nonempty author preferences must cite author or metadata evidence. Unknown facts
remain null/empty; agent interpretations belong in reading/recommendations.
Reading records source, confidence, uncertainty and evidence. Citations establish
traceability, not automatic truth: the intake host verifies facts and resolves
external references within authorized storage boundaries.

Vendor IDs, formats and bindings describe requests, not implemented capabilities.
IngramSpark profile resolution belongs to intake. Unsupported ebook/audio or
special-form intentions must be surfaced, not silently enabled or discarded.
An ordinary PDF/DOCX is not certified print-ready by this form. Page count is an
observed output after rendering, never permission to omit or compress literary text.

## Validation boundary

Install requirements.txt in the active environment. The helper rejects schema
errors, duplicate JSON keys/IDs, dangling references/pointers, inconsistent
heading/TOC/paragraph settings and duplicate paragraph assignments. --work also runs
the sibling preparation validator with local source verification, requires ready
preparation and checks exact basis/unit bytes, paragraph identities/bounds and
reading-excerpt bytes without writing inputs. Remote
sources require host/provider verification outside this local helper.

Shape validation is not source validation. Source validation is not approval,
font verification, vendor compliance or production QA. The GUI rechecks freshness
and constraints before accepting an effective design. Changed text/metadata
requires rebinding/review; regenerated proposals never overwrite author choices.
New production builds require their own human page approval.
