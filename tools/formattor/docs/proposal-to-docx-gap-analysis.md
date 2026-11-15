# Approved proposal to DOCX: current gap assessment

**Reviewed:** 2026-11-15, working tree based on `87b7737`, including uncommitted
interior-design changes. The commit alone does not describe this baseline.

**Status:** investigation, not an approved implementation plan. No producer,
workflow, schema, or UI behavior is implemented by this assessment.

The [high-level design](interior-design-and-production.md), including its
requirement traceability and open decisions, remains authoritative. The
[earlier formatter audit](deterministic-docx-gap-analysis.md) describes the
retired route; it is not evidence of a current integrated producer.

## 1. Conclusion and boundaries

Subsequent owner direction IDP-C21 defines intake, an implementation-independent
engine and format implementations, DOCX by default. IDP-C23 selects an installable
tool with API and CLI under `tools/formattor`, superseding the initial
`workflow/src/formattor` location. The [package-design evaluation](formattor-package-design.md) allocates
the gaps below to those components. It does not mark feature gaps implemented
or settle the full initial output/subset.

The reusable builder can construct a narrow Markdown manuscript under its old
flat settings. It cannot faithfully consume the current approved proposal.
Adding a JSON field translator alone would lose approved design information.

There are three separate gaps:

1. **Compilation and contract:** turn an exact approved proposal and preparation
   into a complete, supported, normalized production specification.
2. **Construction:** implement that specification in DOCX without changing
   source text or silently substituting unsupported settings.
3. **Delivery:** orchestrate rendering, checks, immutable builds, page review,
   and eventual publication. A constructed DOCX is not a verified print PDF.

DOCX construction and print delivery should not be conflated. IDP-D04/D05
remain open: the first promised deliverables and print-capable PDF exporter/
preflight are not yet selected. EPUB/audiobook are allowed proposal targets,
not supported outputs of this DOCX component.

## 2. Inspected implementation

- [Proposal schema](../../../plugins/manuscript-studio/skills/interior-design/schemas/interior-design-proposal.schema.json)
  and [semantic validator](../../../plugins/manuscript-studio/skills/interior-design/scripts/validate_proposal.py):
  shape, references, source hashes/ranges, basic geometry, and profile identity.
- [Proposal contract](../../../plugins/manuscript-studio/skills/interior-design/references/proposal-contract.md):
  proposed status, units, provenance, and UTF-8 byte anchors.
- [Phase coordinator](../../../workflow/src/interior.py): frozen manuscript/metadata, profile
  snapshot, revisioned proposal review, and separate design-approval receipt.
- [Editing engine](../../../workflow/src/editing.py): explicitly blocks after design approval;
  it has no production job transition.
- [Document adapters](../../../workflow/src/document_adapters.py): `DEFAULT_SETTINGS`,
  `validate_settings`, `content_blocks`, `PythonDocxBuilder`, renderer adapters,
  font lookup, TOC convergence, and page rasterization.
- [DOCX inspection](../../../workflow/src/document_audit.py): archive checks and paragraph/
  heading/title/TOC/PAGE-field extraction, not a full fidelity/layout audit.
- [Preparation contract](../../../plugins/manuscript-studio/skills/prepare-manuscript/references/preparation-contract.md)
  and [IngramSpark profile](../../../plugins/manuscript-studio/skills/interior-design/profiles/ingramspark.json):
  ordered units/assets and sourced vendor guidance.
- [Existing tests](../../../workflow/tests/test_workflow.py), `DocumentAdapterTests`: simple
  construction, emphasis/headings/PAGE fields, rejection of some unsupported
  content, and mocked isolated LibreOffice execution.

These are useful foundations. They do not include a proposal compiler,
capability-approved effective spec, or an end-to-end proposal-to-DOCX test.

## 3. Field-level capability matrix

Here, **partial** means reusable low-level behavior exists, not that the current
proposal can be passed directly. The old validator requires its exact flat key
set and rejects the proposal as `Incomplete/unknown format settings.`

| Proposal input | Existing behavior | Gap |
| --- | --- | --- |
| `basis.preparation` and approved receipt | Proposal phase verifies exact work/manifest/unit identity; builder receives one Markdown string | Producer must revalidate approval, ordered units, hashes, metadata, scope, and assets before each build |
| `edition_brief.purpose` | Old settings accept the three corresponding profile tokens | No deterministic presets or interpretation are implemented; compile approved values, not another inferred design |
| Production target `format` | DOCX construction and review-PDF primitives exist | No target router/readiness contract; explicitly reject unsupported target types rather than producing DOCX for every format |
| Vendor/binding/paper/ink/profile reference | Profile snapshot is pinned and identity checked; some design warnings exist | No resolved product selection/capability manifest or executable complete product matrix; preserve distinctions between requirements, recommendations, and unknowns |
| Page `trim_mm` | Width/height in inches | Explicit mm-to-DOCX-unit conversion and approved rounding policy; no UI-inch value as a second authority |
| `margins_mm`, `gutter_mm` | One uniform margin; no mirrored-margin/gutter setup | Separate inside/outside/top/bottom, facing-page semantics, gutter placement and single counting of the binding allowance |
| `bleed_mm` | No bleed-aware page model | Trim versus media dimensions, affected edges and artwork placement are absent; a nonzero scalar alone does not define printable bleed |
| `chapter_start`, `blank_policy` | Boolean page break before mapped level-one headings | No recto starts, declared blank insertion/suppression, or source-blank policy |
| Named styles and heading levels | Fixed Normal/Title/Heading 1-3/TOC styles; heading levels are shifted/clamped | No arbitrary style-ID compilation, levels 4-6, or explicit assignment using unit/role structure |
| Per-style font family/fallbacks | Body family assigned to controlled styles; `fallback_font` is validated but not applied | No per-style family/fallback resolution; inline code separately hard-codes Consolas |
| Per-style size/weight/italic/color | Some flat size knobs; styles reset to regular/upright/black | No complete per-style mapping; source emphasis and style defaults need a defined cascade |
| `font.line_spacing` | Body multiple only; other controlled styles commonly use 1 | Exact-point leading and independent style leading are not compiled |
| Paragraph model and indentation | Global body indent/opening-paragraph flag; fixed blockquote indents | No per-style first-line/block/source-controlled semantics or explicit opening/scene-boundary classification |
| Paragraph before/after spacing and alignment | Body spacing zero; selected title/heading/TOC knobs; body left/justify | Per-style spacing/alignment missing; proposal `justified` needs explicit translation to legacy `justify` if that layer is reused |
| `keep_with_next`, widow/orphan counts | Hard-coded heading keeps and boolean body widow control | No per-style keep policy; arbitrary independent 1-4 line counts are not represented by Word's boolean widow-control property |
| TOC inclusion/depth | Static linked TOC and bounded PDF convergence | No proposal-depth mapping up to six, front-matter/body inclusion policy, or arbitrary TOC style mapping |
| Scene-break/ornament rules | CommonMark `hr` is explicitly rejected | No structural scene-break recognition or approved blank-space/ornament insertion |
| Running heads | None generated | Header content, odd/even behavior, section changes, suppression, placement and typography absent |
| Folio position and numbering | Always adds a centered footer PAGE field | No `none`/outside-footer behavior, Roman front matter, body restart, or page-class suppression |
| `text_roles[].style_id` and exact occurrences | Builder sees Markdown headings/blockquote syntax only | No byte-anchor-to-document mapping or semantic role application; proposal roles are ignored by this API |
| Author metadata/imprint/ISBN | DOCX author is blank; title comes from first Markdown heading | No explicit title/front-matter generation, approved metadata placement, or contributor handling |
| Reading/evidence/rationale/questions | Not builder inputs | Keep as provenance/author decisions, not text to print or free-text instructions to reinterpret during deterministic production |

## 4. Contract gaps that precede reliable construction

### 4.1 Structure and style application

The preparation manifest already has ordered unit IDs, roles, titles and source
references. The proposal has exact byte spans. Neither is a complete render
plan; the builder currently discards unit identity and infers structure from
heading positions in one Markdown string.

Missing definitions include:

- Chapter versus book title, part, epilogue, appendix, and front/body boundaries.
  Do not assume every level-one heading is a chapter or the first is a title page.
- Stable mapping from raw Markdown bytes to parsed paragraphs and inline runs.
  Markdown delimiters, UTF-8 characters, escapes, links, and soft/hard line
  breaks change representation. Plain-text searching cannot replace anchors.
- Inline versus whole-block application, including a recording that starts
  after narration inside a paragraph; cross-paragraph spans need explicit rules.
- Overlap/nesting/conflict precedence between roles, paragraph styles, source
  bold/italic, and direct formatting. Valid span hashes do not settle precedence.
- Base-body fallback outside annotated ranges and selection of optional
  title/folio/TOC styles. The schema requires exactly one body style, not every
  style needed by every requested page feature.
- Per-style left/right or hanging indents and tab/whitespace treatment for
  special forms. The paragraph schema cannot express these; the builder's
  fixed blockquote inset is not a substitute for an approved special style.
- Whether body/heading `text_roles` are render assignments or semantic
  annotations. The array requires at least one entry; manuscripts without
  special inserts must not acquire invented special classifications.
- Exact meaning of `source-controlled`, `preserve-source` scene breaks and
  source blanks. Extraction/Markdown may not preserve the original layout facts.

Canonical preparation roles and transfer lineage remain pending under
IDP-R10/R11/R12. Local verified ranges can potentially support a bounded first
producer; requiring the entire upstream annotation project first is not an
established dependency. Any supported local-range route still needs the
mapping and ambiguity rules above.

### 4.2 Geometry, page furniture and missing selectors

Several requested treatments are not fully specified by existing fields:

- Header/footer distances, typography selection when no matching style exists,
  odd/even running-head arrangement, and which page classes suppress furniture.
- Where Roman front matter ends and Arabic body numbering starts; counting
  versus displaying folios on title/opening/blank pages.
- Whether declared blank pages carry headers/folios and how recto insertion
  interacts with restarting numbering.
- Bleed edges/media boxes and the relation between a text-focused DOCX and
  bleeding artwork. The pinned guide has relevant rules but no complete
  construction plan is compiled from them.
- Which style applies where, when multiple styles share non-body roles.

These require schema additions, deterministic Studio defaults exposed in the
effective spec before approval, or explicit unsupported results. They are not
permission for the builder to invent hidden layout decisions.

### 4.3 Capability and approval mismatch

The proposal schema permits more than this builder can represent. Its geometry
checks prove that some text area remains, not usable typography or printable
content. It permits font sizes outside legacy settings ranges and numeric
widow/orphan rules beyond the existing DOCX property.

Today, a human can approve a structurally valid proposal without proving it
compiles. That receipt binds the proposal, not a normalized producer/font plan.
Production therefore needs an explicit normalization/capability boundary:

1. Resolve supported fields, units, defaults, exact faces and output targets.
2. Report conflicts and unsupported fields with JSON paths.
3. Present any effective-value changes before production authorization.
4. Preserve a human receipt over the exact values actually built.

Whether to extend the existing gate or introduce a distinct effective-spec
approval is an implementation-design decision, not resolved by this assessment.
Do not reuse proposal acceptance as approval of silently changed values.

Technical font/vendor/PDF checks were removed from author questionnaires by
IDP-C18. Missing machine capabilities must not return as questions asking an
author to certify software behavior.

## 5. Construction and environment risks

### Content fidelity and supported subset

`content_blocks` uses CommonMark and rejects images, HTML, horizontal rules,
lists and code blocks. It has no semantic asset/table/footnote pipeline. Some
structures, such as pipe-table-looking text without a table parser, can remain
ordinary paragraphs; absence of a parser exception is not proof of support.
Repeated blank lines and source indentation are not reconstructed as layout.

Inline hard breaks, basic emphasis and restricted hyperlinks are useful
existing support. However, `inline()` writes explicit bold/italic booleans
onto runs. Merely adding an italic paragraph style can still leave ordinary
runs explicitly upright. Style inheritance must be fixed as part of role/style
implementation, not assumed to work after setting a style name.

Unsupported content should produce an actionable diagnostic against the exact
unit/span. No prose reflow, deletion, block flattening, invented text, or
agent-assisted repair is an acceptable silent fallback.

### Fonts and rendering

`check_font` tests a body-family name using the Windows registry or `fc-match`.
It does not establish exact font files/versions, all faces, per-character glyph
coverage, licensing/embedding permission, actual substitution or final-PDF
embedding. It does not even check every font the old builder can introduce.

Word and LibreOffice rendering are reusable, with dedicated Word automation
and an isolated LibreOffice profile. Production still lacks a pinned
capability/font manifest, an across-runs renderer-job policy, and confirmation
of the selected environment's actual support. Different renderers are not
pagination-equivalent.

Writing-system support also needs an explicit subset. A prepared language tag
does not configure DOCX language/direction or prove CJK/bidirectional glyph and
layout support. Assigning one family to every OOXML font slot can still trigger
script-dependent substitution; a successful English probe does not establish
multilingual readiness. IDP-D03 remains open rather than silently assuming all
prepared languages can be produced.

Word rendering updates fields and saves the DOCX before export. Hash/seal the
final DOCX after that mutation, not a pre-render file. Any print normalization
must precede final-PDF QA, page images and human approval.

## 6. Integration, validation and delivery gaps

- **Native lifecycle:** approval currently stores `design_approval` and blocks.
  No compile/build/render/check/page-review transitions exist in the embedded
  phase. Add no public legacy formatting workflow as a shortcut.
- **Recoverability:** existing run locks/checkpoints/receipts are reusable, but
  native production needs owned attempt directories, retry/cancellation
  handling, crash recovery, stale-request protection and sealed candidate IDs.
- **Build identity:** bind preparation and consumed metadata, effective spec,
  profile/product, compiler/builder, actual fonts, renderer and QA policy.
  Model/skill identity is provenance, not a reason to regenerate an otherwise
  identical deterministic document.
- **Fidelity QA:** `docx_paragraphs` extracts text and a few structural flags;
  it is not a complete verifier of source order/emphasis/line breaks, special
  span styles, sections, effective formatting, media or tables.
- **Rendered QA:** adapters provide PDF creation, selected TOC checks and page
  images. They do not implement the complete final-page size/font/embedding/
  numbering/blank-page/safety/content-fidelity checks needed by the new plan.
- **Print readiness:** sourced profile data and advisory trim/safety checks
  are not a complete product catalog or independent PDF preflight. Plain
  Word/LibreOffice export does not establish required PDF conformance.
- **Human page review:** no current manifest-bound page viewer/approval gate
  for this phase. Review must identify the exact final PDF and full page set;
  changed builds cannot inherit prior approval.
- **Publication:** no embedded edition-finalization/export/optional hand-off
  route is connected. Preserve approved literary work while production is
  blocked; do not publish an unreviewed candidate.

## 7. Evidence from a bounded construction probe

Executed during this investigation using the repository's current synthetic
example and installed `python-docx`. No real manuscript, Word/LibreOffice, PDF,
network service or production workflow was used. All generated files were in
an automatically removed, investigation-owned temporary directory.

Directly passing the proposal to `validate_settings` raised
`Incomplete/unknown format settings.`

A second probe manually copied only common body/trim settings into old defaults.
This was an experimental input, not a converter or approved effective spec:

| Property | Proposal example | Inspected generated DOCX |
| --- | --- | --- |
| Trim | 152.4 x 228.6 mm | 152.4 x 228.6 mm |
| Body multiple leading | 1.25 | 1.25 |
| Margins | Inside 19, outside 17, top 19, bottom 22 mm | All approximately 19 mm |
| Additional gutter | 3 mm | 0 mm |
| Mirrored margins | Required by selected book-profile guidance when applied | Not enabled |
| Folio position | Outside footer | Center footer |
| Heading multiple leading | 1.1 | 1.0 |

The exact measured uniform margin was 18.997 mm because of DOCX unit rounding;
that tiny quantization is not the reported margin bug. Losing the independent
outside/bottom/gutter values is the substantive gap. The example has no vendor
selected, so the mirror row records a missing capability, not a claim that this
particular unselected example is already vendor-bound.

This confirms that even a simple current example cannot be faithfully produced
by field renaming alone. It is not a rendering or print-compliance test.

## 8. Decisions before implementation and proposed order

The following are recommendations, not newly approved scope or milestones:

1. **Define the initial promise and subset.** An editable literary DOCX with a
   review PDF is smaller than a verified IngramSpark print-interior PDF. Set
   exact languages/content/features supported; reject the rest explicitly.
   Retain both required paperback/hardcover profile variants.
2. **Close interpretation gaps.** Agree source-to-block/run mapping, inline/
   block role scope and overlaps, page classes, numbering/furniture defaults,
   source-preservation rules, fallback policy and representable widow/orphan
   semantics. Avoid expanding the schema for hypothetical unsupported features.
3. **Define the effective-spec and capability boundary.** Classify every
   production field as compiled, explicitly defaulted, not applicable, or
   unsupported. Keep analysis/rationale out of construction values and show
   material changes before approval.
4. **Extend reusable construction primitives.** Implement the agreed subset
   behind the compiled plan, not a second parallel renderer or a lossy adapter
   that stuffs richer intent into the old flat settings.
5. **Connect native jobs and QA before delivery claims.** Build candidates,
   verify fidelity, render under the pinned environment, review the exact pages,
   then finalize. Add independent print preflight before promising print PDFs.

Suggested verification includes real bound multi-unit fixtures; multibyte byte
anchors; mid-paragraph/overlapping spans; source emphasis with italic styles;
inside/outside/gutter and exact leading; no/center/outside folios; front/body
numbering; recto/blank policy; supported scene forms; missing faces/glyphs and
substitution; unsupported content; stale approvals; failed/cancelled/retried
jobs; and exact candidate invalidation after any effective layout change.

Existing proposal/API/browser tests demonstrate design intake, not these
production properties. Renderer-specific real-output tests and human review
remain necessary; this analysis does not claim they have run.

## 9. Investigation verification

The three retained `DocumentAdapterTests` were rerun and pass. The LibreOffice
isolation test mocks its subprocess; it is not a live renderer test. The
construction probe above inspected an actual temporary DOCX package.

Assessment links, LF/ASCII and whitespace checks pass. No application code,
contract, live run, manuscript or server configuration was changed during this
investigation. The full workflow suite was not rerun for documentation edits.
