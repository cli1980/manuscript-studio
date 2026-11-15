# Deterministic DOCX formatting: requirement and gap analysis

**Date:** 2026-11-13

**Code baseline:** `87b7737` on `feature/deterministic-docx-formatting`.

**Status:** analysis, not an approved implementation design. No application
behavior has changed. Scope, priority, and delivery progress remain in the
[roadmap](../../../roadmap.md#deterministic-docx-formatting-in-the-studio).

## Requirement revision after this baseline analysis

The owner subsequently split the feature into an interior-design skill, a
vendor-aware native intake GUI, and a deterministic producer, and clarified that
formatting always consumes manuscript-preparation results inside editing or
translation. See the [new high-level design](interior-design-and-production.md).

This document preserves the earlier code audit, not the revised target contract.
Its standalone derived-run, accepted-publication input, and zero-agent-for-the-whole-
workflow assumptions are superseded. Design may use an agent; production remains
agent-free. Native gates, immutable approvals, renderer/QA gaps, and provenance
findings remain useful, while an empty-agent standalone template is no longer
a requirement.

The later IDP-C12 direction also removed the obsolete formatter engine/template
and adapter skill discussed in this baseline. Code references below describe
that historical baseline, not an available execution path.

For the current contract and retained builder, see the
[approved-proposal-to-DOCX gap assessment](proposal-to-docx-gap-analysis.md)
(2026-11-15). It separates current construction gaps, contract ambiguities and
production-delivery work without reviving the retired route.

## 1. Requirement interpretation

The requirement is an agent-free formatting workflow, not a new DOCX renderer.
The host already builds and renders documents deterministically. What must
change is who supplies settings, controls the lifecycle, and approves the pages.

The two distinct authorizations are:

1. Approve exact validated settings for the selected accepted publication.
2. Approve the actual rendered build before export/publication and hand-off.

A changed setting or rebuilt candidate must not inherit an older build's page
approval. Rendering a candidate for private review is not publication.
Automated QA supports, but does not replace, the human decision.

"Deterministic" means repeatable text, structure, and pagination checks for the
same accepted input, settings, builder, renderer/version, and font environment.
It does not promise byte-identical DOCX/PDF files or identical pagination between
Word and LibreOffice. ZIP/document metadata can differ without changing layout.

## 2. Existing reusable foundations

- `FormattingEngine` (retired `workflow/src/formatting.py`) checked the accepted publication and
  chapter hashes, snapshots input, validates settings bindings, uses distinct
  build directories, checks generated hashes, audits DOCX text/order/headings,
  exports completed output, and supplies provenance for hand-off.
- [document_adapters.py](../../../workflow/src/document_adapters.py) already provides settings
  validation, deterministic construction, isolated Word automation, an isolated
  LibreOffice profile, renderer preflight, TOC pagination convergence, rendered
  TOC-entry checks, and rasterization of every PDF page.
- [Engine](../../../workflow/src/engine.py) and [storage](../../../workflow/src/storage.py) provide durable
  state, run locks, gate revisions, receipts, saved artifact hashes, and recovery.
- [WorkflowService](../../../workflow/src/service.py) provides derived-run creation, the
  one-unfinished-run rule, output lineage, and automatic DOCX-to-new-work hand-off.
- The studio already selects accepted publications and renderer, renders shared
  decision bodies, runs work in background threads, and refreshes through the
  existing live change feed.

These foundations should be reused, not replaced with a second document pipeline.

## 3. Requirement-to-implementation gaps

| Area | Present implementation | Required delta |
| --- | --- | --- |
| No agent dependency | Template declares one agent stage and four skill bundles. The host builds between agent turns; the agent proposes settings and later attests QA. | Native settings, build, review, and completion transitions. Formatting must finish with no runtime calls, model requirement, or skill attestation. |
| Native settings and presets | Strict settings validator and one DEFAULT_SETTINGS object; three profile names are accepted. Settings are agent-authored JSON. | Real preset definitions, explicit metadata-derived defaults, editable draft/settings schema, and server-validated settings approval. |
| Settings receipts | Existing human format-sheet closure binds proposal/settings hashes, but the agent updates domain records. | Preserve binding/provenance while making the host own settings submission, revision, approval, and receipt generation. |
| Background build | A native advance override already builds, with a UUID build directory, under the run lock. | A job lifecycle that enters human page review instead of returning to the agent; distinguish queued/build/render/QA/review state and retries. |
| Renderer serialization | One worker thread per run. Word uses DispatchEx and LibreOffice uses separate profiles. | Queue/lock at the renderer scope across runs, not only per-run locking. Isolation does not meet the requirement of one renderer instance at a time. |
| Human page review | QA starts with pending flags; an agent is instructed to inspect PNGs and update qa.json. No human rendered-page gate exists. | A native page-review gate, approve/revise actions, and a human receipt bound to the exact candidate and immutable evidence. |
| Automated layout QA | Font presence is checked before construction; heading keep-with-next is set; pages and TOC are checked/counted. | Inspect fonts actually used in the rendered PDF; detect blank content pages and stranded headings. Layout preferences are not post-render checks. |
| API and UI | FormatPanel chooses version/renderer; GatePanel renders a generic agent approval sheet. The artifact API serves text; run UI reports local output paths. | Capability/font discovery, native settings/review payloads, safe candidate-image serving, settings form, QA/page gallery, and native job wording. |
| Edition identity | Identity includes input, purpose, model, adapter skill hash, and backend, but not approved settings. | Separate draft/request reuse from settings-bound build identity. Exclude model/skills from the native edition identity; bind relevant builder/renderer/font provenance. |
| Publication and hand-off | Export and hand-off happen after agent completion and QA validation. | Invoke completion only after current settings and build receipts plus machine checks. Verify duplicate approval, retry, export failure, and hand-off recovery. |
| Tests | Existing tests cover agent-era approvals/audits, the builder, and mocked renderer behavior. | End-to-end native lifecycle with a runtime that fails on any call; valid stand-in PDF renderer exercising layout/rasterization; new API/browser, QA, concurrency, and stale-build tests. |

## 4. Less obvious implementation constraints

### Native execution requires a real lifecycle boundary

The [registry](../../../workflow/src/registry.py) requires at least one agent and allows custom
declared gates only on agent stages. Engine.advance handles metadata/select/
acceptance/export natively, but otherwise calls runtime.run. Merely deleting
the formatting prompt will not create an agent-free workflow.

The [worker](../../../studio/server/worker.py) constructs a runtime for every step,
including the existing native build. This does not itself launch an agent
process, but native steps should not require runtime configuration at all.
The run UI also describes active work as "agent working"; native job phases
must not be reported as agent turns.

Recommendation: add the smallest host-stage/review extension needed by the shared
engine, with formatting-specific behavior owned by FormattingEngine. Do not use
a fake runtime, keep a dummy agent in the template, or build a general-purpose
distributed job framework.

### Settings availability is not preset support

DEFAULT_SETTINGS is a reader-facing configuration, not three complete presets.
Changing its profile string does not implement submission or editorial-review
designs. Define explicit, reviewable defaults and preset-reset behavior.

The accepted chapter manifest does not carry a complete formatting metadata
snapshot, and create_derived currently receives no separate metadata snapshot.
Decide whether defaults use current shared metadata or the accepted version's
metadata, then pin the chosen revision/hash. Later metadata changes must not
silently change approved settings or add manuscript text.

The validator accepts fallback_font, but the builder does not apply it.
Inline code also uses hard-coded Consolas. Either support these choices
explicitly in the effective font policy or remove/refuse them; do not present
ineffective controls. Installed body-font validation alone does not establish
what the renderer used, including styled faces and glyph fallback.

### Existing deduplication can prevent a new design

WorkflowService.create_derived_run returns an existing noncancelled run with the
same edition identity, including completed runs. Approved settings are not in
that identity. Consequently, asking for another edition with the same input/
purpose/renderer can reopen the completed edition before new settings are chosen.

The CLI exposes new_edition, but the studio create endpoint does not forward it.
Resolve this deliberately: a new design needs a new draft/request or explicit
new-edition action, while repeat submissions should remain idempotent.
Do not use model changes as an edition-creation workaround.

Distinguish a canonical build-request key from the actual immutable artifact
manifest hash. A settings-equivalent rebuild with different artifact bytes is
still not automatically approved by a previous receipt.

### Page approval must be over immutable evidence

Use a host-owned build manifest that binds accepted input, approved settings,
builder/renderer provenance, DOCX/PDF hashes, ordered page hashes/count, and
machine-QA policy/results. Keep the human receipt separate and bound to that
manifest. Do not have the browser edit QA success booleans in qa.json.

On revision/rebuild, invalidate the page gate and any older page approval.
Validate the gate ID, build ID/hash, and current status under the run lock.
Publication must independently recheck the bindings, not trust a disabled button.
A UI acknowledgement records the person's attestation; it cannot prove they
actually read each page.

Existing generated-artifact checks and receipts are useful foundations, but
their agent-era adapter_skill_sha256 and mutable QA flags need replacing in the
native path, not relabeling as a human review.

### Define QA policies before treating findings as hard failures

- Font matching needs normalization for subset prefixes and bold/italic names,
  plus a policy for permitted fallback/inline fonts.
- A page containing only a folio is not necessarily a meaningful content page.
  Define blank-page handling separately from a naive empty-text/white-pixel test.
- Define stranded headings and legitimate title/front-matter exceptions before
  enforcing a PDF text-position rule.
- Preserve current manuscript fidelity, semantic heading, TOC, and folio checks.
  Unsupported structure should still fail explicitly.

These are policy definitions needed to implement existing requirements, not
approval to expand content/language support.

### Serve review assets without exposing the workspace

There is no current PNG/PDF candidate-preview API. Use run/build/page identifiers
resolved through the verified manifest, safe paths, explicit media types, and
existing localhost/owner boundaries; never accept an arbitrary filesystem path.
Immutable asset identity also prevents a browser showing stale pages for a new
build. PNG viewing fits the current same-origin image CSP without widening it.

The completed handed-off work already offers its DOCX through the source-download
route. A direct final-edition download may improve convenience, but should not be
confused with the missing prepublication page-review capability.

## 5. Decisions to settle before implementation

Recommendations below are not recorded owner approvals:

| Decision | Recommended initial boundary |
| --- | --- |
| Review location | Keep native settings/gallery on run management in the existing decision frame; do not block this work on a chapter-viewer rewrite. |
| Optional agent suggestions | Exclude from the first native path; otherwise the zero-agent contract becomes ambiguous. |
| External Documents path | Keep the standalone plugin skill independent; explicitly decide whether the old CLI external-adapter path remains. Do not retain agent machinery inside the native path just for compatibility. |
| Content/language expansion | Keep recorded English/navigation and supported-content limits for this first delivery unless the owner explicitly changes scope. |
| Metadata defaults | Choose current metadata versus accepted-version metadata and pin that choice. Avoid implicitly inserting author/copyright/other prose. |
| Review semantics | Decide per-page acknowledgements versus one explicit all-pages acknowledgement; both must bind the same complete candidate evidence. |
| Native CLI access | Decide the minimal settings-file/review commands, if any; shared service changes must not accidentally force Codex use for native work. |

The detailed UX baseline is on `feature/ux` at `ba0b892`, not an ancestor of this
branch. Integrate or port those documents explicitly before updating their target
design; do not recreate the UX backlog in the roadmap. No branch merge is made
by this analysis.

## 6. Suggested implementation sequence

This is dependency order, not a new milestone schedule:

1. Establish native lifecycle/receipt contracts and settings/build identity.
   Keep renderer dependencies injectable and agent configuration absent.
2. Implement presets, metadata pinning, settings validation/approval, and the
   native build/review transition. Reuse the current builder and artifact checks.
3. Add renderer serialization, machine QA policies/checks, and immutable review
   manifests. Exercise retries, process failure, and stale-build protection.
4. Expose safe capabilities/settings/page-review APIs and the existing-frame
   form/gallery; use current live refresh, not another polling loop.
5. Gate export/hand-off on current human approval. Test duplicate/recovery paths
   so a completed run and handed-off work are not produced prematurely or twice.
6. Run the native workflow with a failing-on-call runtime and a valid stand-in
   renderer, then verify the UI and finally a real installed renderer.

No production implementation or new QA policy has been approved by this ordering.
Pre-release compatibility rules favor clean native schemas over legacy shims.

## 7. Baseline verification and missing evidence

Ran 15 existing tests: eight formatting/native-settings WorkflowTests, three
DocumentAdapterTests, and all four studio WebApiTests. All passed.

The native lifecycle test mocks the whole build_and_render function and uses a
synthetic PDF placeholder; the LibreOffice test mocks subprocess execution.
These tests do not demonstrate actual renderer availability, rendered font/layout
QA, renderer queuing, a human page-review UI, or a zero-agent formatting workflow.
No real Word/LibreOffice job or new browser test was run for this analysis.

Reproduce the selected existing baseline with:

```text
.venv-workflow/Scripts/python.exe -B -m unittest workflow.tests.test_workflow.WorkflowTests -k formatter -v
.venv-workflow/Scripts/python.exe -B -m unittest workflow.tests.test_workflow.WorkflowTests.test_native_settings_are_revision_bound_and_renderer_switch_creates_an_edition workflow.tests.test_workflow.DocumentAdapterTests studio.tests.test_web.WebApiTests -v
```

Required new evidence includes zero runtime calls, both exact-bound receipts,
revise/rebuild invalidation, duplicate/stale/tampered approvals, actual pipeline
execution with a valid fake renderer, QA findings, serialization across works,
renderer timeouts/retry, publication/hand-off recovery, and browser form/gallery
completion. A valid fake PDF fixture should exercise TOC convergence and page
generation instead of bypassing the entire native pipeline.
