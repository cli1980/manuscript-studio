# Formattor package: architectural evaluation

**Date:** 2026-11-15

**Owner direction:** IDP-R19 / IDP-C21 / IDP-C23 in the
[high-level design](interior-design-and-production.md).

The owner-confirmed location is an installable project under `tools/formattor`,
exposing one core through a Python API and CLI. IDP-C23 supersedes the initial
`workflow/src/formattor` location, not its three-part structure: proposal intake,
an implementation-independent format engine, and format implementations.
DOCX is the default implementation; InDesign is a potential future one.
The spelling `formattor` is retained as requested.

**Status:** tool location, API/CLI exposure and component split are confirmed;
interfaces, detailed ownership and migration remain design recommendations.
Documentation is consolidated here. No executable package, InDesign adapter,
new output capability or production workflow is implemented.

The [placement evaluation](formattor-placement-evaluation.md) records the
comparison and the decision to keep workflow as a client of the installed tool.

## 1. Verdict

The split is appropriate and closes the architectural ownership/dependency gap.
It does not by itself close the
[field-level production gaps](proposal-to-docx-gap-analysis.md).

Two distinctions are essential:

1. The **format engine orchestrates formatting**, but is not a universal
   typesetter. DOCX and InDesign have different composition/pagination systems;
   the selected implementation owns their native layout operations.
2. An **implementation**, a **renderer**, and a **deliverable** are different
   axes. DOCX is the default implementation. Word/LibreOffice are renderer
   strategies within it. A vendor-verified PDF is a delivery claim requiring
   checks, not another name for either of those choices.

The interior-design skill remains an author of proposals. It must not become
the formatter again, and the package must not require an agent to build or
repair production output.

## 2. Proposed package and dependency direction

```text
tools/formattor/
    pyproject.toml              installation/dependencies/API and CLI entry point
    src/formattor/
```

Within the installed `formattor` package:

```text
    __init__.py                 public API; no eager native-tool imports
    cli.py                      thin command-line host over the same core
    contracts.py                shared records and implementation protocol
    intake.py                   proposal/source validation and normalization
    engine.py                   preparation/build/check/seal orchestration
    resources/                  canonical schemas, profiles, versioned policies
    implementations/
        docx/
            __init__.py         implementation entry point
            builder.py          DOCX construction and native style mapping
            rendering.py        Word/LibreOffice strategies
            audit.py            actual DOCX extraction/format-specific checks
```

This is a proposed organization, not a requirement to create every file at
once. Shared checks or source-model helpers can be extracted as their size
justifies it. They remain internal support for the three logical parts.
Do not create empty InDesign modules or pretend to register a usable backend.

Dependencies:

- `intake` uses shared contracts/resources and a preparation-verification
  boundary; it does not import the format engine or native implementations.
- `engine` uses intake and the implementation protocol, not DOCX classes.
- Implementations use shared contracts and their own libraries/tools; they do
  not import the workflow coordinator, Studio, or agent runtimes.
- A small composition root selects the default DOCX implementation lazily.
  A static registry is sufficient initially; dynamic plugin discovery is not
  needed to establish substitutability.
- The parent workflow uses the public package API. No `formattor` core module
  should depend on `workflow.src.engine.Engine`, a run database, Studio, or
  dynamically loaded skill scripts.

The format engine is not a replacement for the application's workflow engine
and must not create a second run/state database or a public formatting workflow.
A standalone CLI is another caller of this library, not a restored Studio
formatting-workflow template. It must not require a workflow run or receipt to
validate inputs or prepare a plan.

## 3. Responsibilities of the three parts

### 3.1 Proposal intake

Intake converts authoring input into a typed, source-bound formatting request.
It does not render, approve, generate prose, or infer a different design.

Inputs:

- Versioned proposal and its exact identity.
- Verified preparation, ordered units/assets, source hashes and frozen metadata.
- Host-authoritative purpose/vendor/binding selections and pinned profile data.
- Requested deliverables and versioned normalization/default policies.

Responsibilities:

- Validate shape, references, source scope/ranges and profile identity.
- Reject attempts to override the entry selections or confirmed metadata.
- Normalize units/representation, not literary text; mm/pt stay authoritative,
  with inches only a UI presentation.
- Build a backend-neutral semantic document with source mapping.
- Separate render values from reading, evidence, rationale, questions and other
  provenance. Free-text author answers are not executable layout instructions.
- Account for every production field and return actionable diagnostics.
- Materialize any backend-resolved values/defaults as an effective spec for
  review, instead of allowing an implementation to invent hidden settings.

The existing vendor/binding resolver is also useful before proposal authoring
to supply the selected profile to the skill. It belongs to this package's shared
intake/resources API, not a separate skill-owned production implementation.

### 3.2 Implementation-independent format engine

The engine coordinates two distinct operations:

1. **Prepare:** run intake, obtain implementation capabilities/environment,
   request a native plan, and expose the complete effective-spec preview plus
   diagnostics. Preparation does not imply human approval.
2. **Produce:** verify the approval-bound request and environment, run the
   selected implementation in an owned workspace, check actual artifacts, and
   seal a candidate manifest or return an explicit failure.

The engine owns generic production invariants: bounded work, input identities,
required-check policy, artifact hashes, build identity, cancellation/progress
contracts, and no publication of an unverified candidate.

It does not:

- Import `python-docx`, automate Word, construct OOXML or call InDesign APIs.
- Assume every implementation emits `manuscript.docx`.
- Calculate final line wraps/page breaks itself or inspect native page objects.
- Silently change backend, fonts, margins or unsupported settings.
- Store human approvals, render approval widgets, or publish parent-workflow
  output. Those authorities remain with the host.

Use the existing host worker/store/locking infrastructure rather than inventing
a parallel scheduler. The package can accept a workspace, cancellation signal
and progress sink; host adapters persist resumable job state and gate receipts.
Native resource requirements, such as serialized application automation, are
declared by the implementation and enforced by the job owner.

### 3.3 Format implementations

An implementation translates the neutral document/spec into native composition
operations and reports its actual capabilities and output evidence.

The default DOCX implementation owns:

- Native paragraph/character styles, sections, margins/gutter, page numbering,
  furniture, source-span application and content construction.
- DOCX-specific unit rounding and representability constraints.
- Word/LibreOffice rendering, field updates and bounded native layout/TOC
  convergence, where required by the requested outputs.
- Native extraction/audits and the final artifact set.

Existing builder/render/audit primitives should be moved/reused here where
sound, then extended for the agreed subset. Their current flat settings are not
the new public contract and must not constrain the entire engine.

Backend-specific composition stays inside the implementation. Shared final-PDF
verification/rasterization can be reused across implementations through output
contracts. Any export/normalization must finish before final checks, images,
hashing and page approval.

## 4. The contracts that make the split work

The following are conceptual interfaces, not new Python code:

| Record/API | Required meaning |
| --- | --- |
| `ProposalBundle` | Versioned authoring input plus verified source/metadata/profile references and trusted entry choices |
| `CanonicalDraft` | Backend-neutral semantic document, normalized design intent, provenance and diagnostics |
| `CapabilitySnapshot` | Implementation/tool identity, output formats, supported features/value constraints, language/font facts and available checks |
| `ImplementationPreparation` | Native plan, explicit resolutions/rounding, field dispositions, environment identity and diagnostics |
| `PreparedFormatting` | Complete effective spec and document/plan references, ready for the host's approval gate |
| `ApprovedFormatting` | Exact prepared identity with the host's current authorization binding, not an `approved` flag inside the proposal |
| `CandidateBuild` | Actual artifacts by role/format, hashes, environment, check results and source/plan/spec identities; not publication |

Minimal implementation operations:

```text
inspect(environment) -> CapabilitySnapshot
prepare(canonical_draft, capabilities) -> ImplementationPreparation
produce(approved_plan, workspace, cancellation) -> ImplementationArtifacts
verify(approved_plan, actual_artifacts) -> CheckResults
```

The engine orchestrates these operations. Intake performs common validation and
normalization; backend preparation resolves only native constraints. Native plans
must be serializable/versioned records or artifact references, not live COM/
application handles leaking into the engine or persisted workflow state.

Every production field must be compiled, explicitly defaulted, not applicable
with a reason, or unsupported with a diagnostic. The same applies to source
constructs. Backend-specific defaults and approximations cannot disappear into
an opaque successful build.

Errors should include stage, field path and, where applicable, unit/source span.
Required checks report failures or unsupported capability explicitly; absent
evidence is not a pass. Checks that depend on a rendered file run after rendering,
not as author certifications at design approval.

## 5. Keep the neutral model out of DOCX terminology

The common model should describe ordered units, paragraphs/inline text, semantic
roles, sections/page classes, styles, geometry, numbering and scene structures.
It should not contain Word style names, `w:pPr` nodes, `Inches` objects or Adobe
application objects.

Before implementation, specify these semantics:

| Gap | Recommended closure at the contract boundary |
| --- | --- |
| Raw Markdown byte anchors versus native text positions | Preserve an exact source map into logical nodes/runs. Define neutral span indexing; implementations translate native indexing rather than searching for matching text |
| Inline versus block role application | Declare scope explicitly; inline application must not silently apply/discard paragraph-only settings |
| Nested/overlapping roles | Define base-body and source-emphasis inheritance; reject conflicting paragraph/character assignments unless precedence is explicit |
| Special forms and source-controlled layout | Express required indents/line/whitespace behavior, or report the requested treatment unsupported; do not use the old fixed blockquote inset as a substitute |
| Page classes and furniture | Use verified front/body/chapter structure and explicit placement/numbering/suppression rules; no first-heading/title heuristic |
| Missing optional style/default values | Resolve versioned Studio defaults into the effective spec before approval; mark unused features not applicable |
| Numeric widow/orphan controls | Declare exact backend constraints; DOCX's boolean property cannot silently approximate arbitrary separate 1-4 line counts |
| Fonts and fallback | Resolve an approved policy to actual faces/glyph coverage and record environment/evidence; unexpected substitution is not a successful fallback |

These are proposed closure rules, not assertions that the current proposal
schema or builder already implements them. Keep uncertainty visible before
approval; do not move these decisions into native export code.

For an initial contract, prefer immutable logical node IDs and Unicode scalar
span positions with an exact map back to prepared UTF-8 bytes. Native character
indices remain an adapter concern, including UTF-16-based APIs. Do not normalize
literary text to simplify that mapping.

For initial style composition, recommend one explicit paragraph-role style per
paragraph and disjoint explicit character-role ranges; conflicting special-role
overlaps fail preparation until an explicit policy exists. Base-body assignment
and source emphasis are not conflicting special-role overlaps. Unmarked source
runs inherit style properties; they do not force `bold=False`/`italic=False`.
Explicit source bold/italic is preserved as an overlay. This avoids reproducing
the existing builder's inheritance bug without inventing a universal cascade.

Backend neutrality does not mean the lowest common denominator, and it does not
promise that every future InDesign feature fits the current contract. Add
versioned, reviewable common semantics when justified; do not use untyped
`backend_options` as an escape hatch around validation and approval.

## 6. DOCX, InDesign, renderers and deliverables

| Axis | Initial/default | Future implication |
| --- | --- | --- |
| Format implementation | `docx` | `indesign` may be added against the same protocol |
| Native editable artifact | DOCX | Native InDesign/IDML delivery needs an explicit target contract if promised |
| Rendering/composition | Selected Word/LibreOffice strategy | InDesign owns its native composition/export; it is not a third DOCX renderer |
| Review output | Requested final review PDF/pages | Same artifact roles/check/page-review contracts, not guaranteed identical pagination |
| Print claim | Only after applicable actual-output checks | Native PDF export alone is not vendor/PDF-standard certification |

An InDesign implementation could support a PDF target without claiming DOCX
delivery. If a request explicitly requires `editable-docx`, an implementation
that cannot produce it must reject the target. Do not silently substitute an
INDD/IDML file or convert through DOCX just to satisfy the engine.

The current proposal target enum does not include native InDesign project
formats. Extend that contract only when such delivery is actually in scope.
Desktop/server deployment, automation transport, licensing, font installation
and native-document packaging remain future implementation decisions.

Adding a backend should principally require a protocol implementation,
capability declaration, composition-root registration and contract tests, not
new branches throughout the common engine. No InDesign runtime/dependency is
needed to implement the DOCX path or test independence using a fake backend.

## 7. Skill, resource and distribution ownership

The actual builder currently lives in `workflow/src/document_adapters.py`, not
in the skill. The remaining coupling is concrete:
`InteriorDesignPhase.interior_validator` dynamically loads the validator from a
pinned skill directory; that validator loads skill-local profile/verification
helpers and resources.

Recommended ownership after migration:

- The package owns canonical executable intake/validation/normalization,
  generation, capability logic and vendor-profile resolution.
- Canonical schemas/profiles/policies live with package resources. Production
  never imports or executes `skills/.../scripts`.
- The interior-design skill keeps proposal-authoring instructions and contract
  references. Generated, versioned data/reference exports may accompany it for
  portable authoring; they are not a second editable source of truth or another
  formatter.
- Standalone skill authoring remains usable without Studio or a workflow run.
  Exact validation uses an installed package/tool entry point, not a hidden
  relative import into a developer's checkout.
- Distribution must provide that tool/resource path before removing the current
  helper path. Test exports/version matching and standalone installation; do not
  keep permanent duplicate validators as a compatibility solution.

Preparation remains an upstream responsibility. Reuse its authoritative
verification through a documented data/verifier boundary rather than copying a
partial preparation validator into the formatter or importing skill scripts in
the core. Both host and standalone tool need a supported verification adapter.

## 8. Host workflow and approval boundary

```text
Host: choose purpose/vendor/binding; supply resolved profile/capabilities
  -> interior-design skill authors proposal
  -> format engine preparation: intake + implementation analysis
  -> host reviews/approves exact effective specification
  -> format engine produces, verifies and seals candidate
  -> host presents the exact final pages for human approval
  -> host finalizes/publishes the parent workflow
```

The Studio form is a presentation client of intake/preparation results; React
components do not move into the Python package. `interior.py` remains the
editing/translation coordination adapter, not a second formatter.

If preparation changes effective values, the user must see those values before
authorizing production. No technical questionnaire replaces machine checks.
Changing implementation/environment requires re-preparation, a new candidate
and page approval; renew effective-spec approval whenever its bound values or
context change. No silent renderer/backend fallback.

The production key includes source/effective spec/profile, implementation and
tool/font/check identities. Skill/model provenance is recorded separately.
This package boundary does not automatically fix the parent workflow's current
engine-version/restart rules; integration must avoid reintroducing agent
identity as a deterministic-build dependency.

## 9. Gap ownership and acceptance

| Prior gap | New owner | What still has to be done |
| --- | --- | --- |
| No approved effective spec/compiler | Intake + engine preparation + host gate | Define/materialize complete supported values and exact approval binding |
| No source-span/structure/style mapping | Intake semantic model; implementations consume it | Resolve scope/overlap/page-class semantics and preserve exact source fidelity |
| Missing DOCX layout features | DOCX implementation | Implement/test the agreed margins/styles/leading/furniture/numbering subset |
| Font/capability ambiguity | Implementation inspection/preparation; engine revalidation | Pin actual environment and reject unsupported requests before approval/build |
| Product/preflight uncertainty | Shared policy/check contracts and output-specific verification | Complete scoped product/check coverage; resolve IDP-D03/D04/D05 |
| Native lifecycle and page approval | Host adapter around the format engine | Connect jobs, recovery, exact candidate review and finalization |
| Skill-dependent validation/resources | Package + distribution integration | Move authority without breaking standalone authoring/verification |
| Potential InDesign support | Future implementation | Prove protocol independence now; do not claim feature parity or ship a stub |

Suggested architectural acceptance checks:

- Core imports and intake tests run without DOCX libraries, Word, InDesign,
  Studio, a model runtime or a run database.
- A fake non-DOCX implementation emits different artifact roles through the
  same engine without adding a DOCX branch.
- Every requested production field/source construct has an explicit disposition;
  unsupported values block the relevant stage rather than disappearing.
- Hand-edited proposals cannot change trusted entry metadata/profile identity.
- Capability/environment drift is caught between preparation and production.
- Reuse/implement real DOCX fidelity tests from the gap assessment; passing
  protocol tests alone does not establish output quality.
- Required output checks and exact-build page approval cannot be bypassed by a
  backend's success return, an author acknowledgement, or a stale receipt.
- Resource exports/standalone validation remain consistent with package contracts.

## 10. Recommended implementation sequence

1. Define the shared records, neutral semantics, capability coverage and exact
   effective-spec/approval boundary for the initial supported DOCX subset.
2. Move intake/resource authority into the package with a tested standalone
   distribution path; replace dynamic production imports from skill snapshots.
3. Establish the engine protocol with a fake implementation and host boundary.
4. Move/reuse and extend the DOCX primitives behind that protocol; preserve
   explicit unsupported results while feature coverage grows.
5. Connect native jobs, actual-artifact QA, final-page review and finalization.
   Add verified print-output capabilities only when their checks are available.

The standalone tool location/API/CLI, default implementation and component split
are owner-confirmed. Specific
deliverables/print readiness (IDP-D04/D05), content/language/product subset
(IDP-D03), annotation semantics (IDP-D08), distribution mechanics and the detailed
interfaces above are not all resolved merely by selecting this architecture.
They remain explicit design/implementation work, not completed production.
