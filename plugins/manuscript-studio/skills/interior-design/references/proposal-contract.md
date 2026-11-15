# Interior-design proposal contract

[Schema](../schemas/interior-design-proposal.schema.json): JSON Schema draft
2020-12, contract interior-design-proposal/1. See the [example](proposal.example.json).
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
| text_roles | Semantic roles, narrative function, exact prepared occurrences and proposed style mapping |
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

Occurrences use zero-based UTF-8 byte offsets into exact chapter Markdown:
start_byte inclusive, end_byte exclusive, both at character boundaries.
text_sha256 hashes the span; chapter_sha256 binds the whole unit. This is a
proposal-side locator, not an extension to preparation manifests. Valid ranges
still do not prove that a semantic classification is correct.

Canonical semantic roles belong to preparation, with editing/translation owning
their output mappings. This proposal-v1 contract currently has local role IDs
and ranges only, not canonical annotation references or transfer lineage.
Upstream annotation tooling and downstream propagation require coordinated
schema/workflow changes. Do not claim they are implemented by span validation.

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
An ordinary PDF/DOCX is not certified print-ready by this form. Page count is a
preference until rendering, never permission to omit or compress literary text.

## Validation boundary

Install requirements.txt in the active environment. The helper rejects schema
errors, duplicate JSON keys/IDs, dangling references/pointers, inconsistent
heading/TOC/paragraph settings and invalid span relationships. --work also runs
the sibling preparation validator with local source verification, requires ready
preparation and checks exact basis/span bytes without writing inputs. Remote
sources require host/provider verification outside this local helper.

Shape validation is not source validation. Source validation is not approval,
font verification, vendor compliance or production QA. The GUI rechecks freshness
and constraints before accepting an effective design. Changed text/metadata
requires rebinding/review; regenerated proposals never overwrite author choices.
New production builds require their own human page approval.
