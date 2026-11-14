# Manuscript Studio roadmap

This is the shared roadmap and development progress record for humans and agents.

The current goal is a usable web frontend for managing manuscripts and their
workflows, starting with literary translation, followed by a Literary Edit
workflow supported in both the CLI and the web GUI.

## Conventions

- Milestones are outcome-based and ordered by priority. They have no target dates.
- Every milestone is owned by the project owner, `cli1980`, unless stated otherwise.
- The roadmap file stays at `roadmap.md`, which is where [AGENTS.md](AGENTS.md) points.
- Milestones, delivery scope, priorities, and implementation progress live in
  `roadmap.md`. Detailed user flows, screen contracts, interaction rules, and
  UX design decisions live in the versioned [UX specification](docs/ux/README.md).
  Link to stable flow/screen IDs instead of duplicating their design here.
  The GitHub Project
  [Manuscript Studio Requirements](https://github.com/users/cli1980/projects/2) is
  used only to collect and triage external requirements (New, Triage, Accepted,
  Declined, Moved to roadmap). Accepted requirements are added to `roadmap.md`,
  which then tracks them.

## Cross-cutting decisions

Agreed in the 2026-10-26 planning session:

- **Licensing** (owner decision, 2026-10-27; applies from the next commit). The
  copyright holder is Crossborder Art & Media LLC. Skills (`plugins/`) and
  `evals/` stay MIT. `workflow/` and `studio/` are licensed under PolyForm
  Noncommercial 1.0.0; commercial use requires a separate license negotiated
  with the copyright holder. Already-published MIT versions of `workflow/` stay
  MIT. `fixtures/` keep the terms recorded with each fixture.
- **Interaction contracts:** intake, reading/decision placement, versioned
  metadata, and confirmation behavior are specified in
  [UX principles](docs/ux/principles.md) and
  [UXD-001](docs/ux/decisions/UXD-001-interaction-contracts.md), preserving the
  original owner decisions and dates.
- **Manuscripts are immutable.** Manuscript text changes only through workflow
  stages and their human gates. The GUI presents the original upload, prepared
  chapters, and workflow outputs read-only.
- **Metadata is editable and versioned.** Shared `work.json` metadata can be edited
  from the GUI. Every change is versioned and attributable.
- **DOCX first.** DOCX and Markdown/text intake come first; PDF comes later.
- **Generalize before expanding.** The engine must be generalized before any
  workflow other than literary translation is added.
- **Users.** Support a single user initially while keeping the architecture
  compatible with multiple users (fewer than 10). Remote deployment,
  multi-user management, and role-based access are a standalone milestone
  (owner decision, 2026-11-12), not part of M3.

Agreed in the 2026-10-26 M1 design review (details in
[workflow/docs/m1-design.md](workflow/docs/m1-design.md)):

- **Works and runs.** Uploading a manuscript always creates a new work with a
  new ID, even for an identical file. Another workflow on an existing work is
  started by selecting the work, not by uploading. A work has at most one
  unfinished run at a time.
- **Per-work artifact library.** Artifacts that outlive a run (sources,
  shared metadata, accepted outputs) are shared across workflows through an
  engine-owned library per work. Git versioning is a future consideration.
  Published preparation is not reused in M1; every run prepares again (decided
  in the 2026-10-27 gap review).
- **Metadata review.** A required human gate after preparation lets users
  inspect and edit metadata. Later edits are recorded in history only.
- **Recovery without rollback.** Users can retry the current step, restart a
  chapter, restart a stage, or restart an unfinished workflow. Restarts reuse
  the glossary and voice of the last completed chapter; completed chapters are
  not changed unless restarted.
- **Finalization.** Final acceptance makes that run immutable. A new run on the
  same work can publish the next version (owner correction, 2026-10-28).
  See [UF-13](docs/ux/flows/UF-13-finalize.md) and
  [UF-14](docs/ux/flows/UF-14-next-version.md) for the user-facing contract and
  [UXD-001](docs/ux/decisions/UXD-001-interaction-contracts.md) for the superseded
  new-upload-only wording.
- **Engine updates.** An unfinished run must be restarted after an engine code
  update.

## Milestones

### Plugin listing readiness fix

- **Status:** `in_progress`; local changes prepared on `fix/plugin-listing-metadata`.
- Shorten the subtitle to 29 characters, retain three focused starter prompts
  for editing, translation, and formatting, and package square SVG logo/composer
  assets with manifest references.
- Add privacy and support documentation and explicit listing URLs. Support uses
  the existing public GitHub issue tracker; no private mailbox is invented.
- Document capability-dependent environments, blocked formatting without the
  Documents skill/rendering/inspection tools, and revision-bound text approvals
  when the specific inline visualization surface is absent.
- **Publication boundary:** the privacy file's main-branch URL must be publicly
  reachable before submission. Local files do not constitute publication.
  Publication/merge has not been performed; local main is ahead of its remote,
  so unrelated existing commits must not be pushed implicitly.
- **Local verification:** 3 listing/asset checks passed; installer suite ran
  30 tests with 3 platform-dependent skips; all 28 approval tests passed,
  including text dispositions, stale revisions, required notes, separate
  closure, and generated JavaScript syntax. SVG branding was rendered and
  visually inspected. The declared public privacy URL currently returns 404:
  publication remains blocked until the policy is merged and published.
  Formatting fallback is documented; no new Documents/rendering execution is
  claimed by this metadata fix.

When adding milestones, record their intended outcomes, acceptance criteria,
status, owner, and relevant issue or implementation links. Use these statuses:
`planned`, `in_progress`, `blocked`, `in_review`, and `done`.

### M1 — Generalized workflow engine

- **Status:** `done` (marked done by the owner on 2026-10-27)
- **Owner:** `cli1980`
- **Design:** [workflow/docs/m1-design.md](workflow/docs/m1-design.md)
  (owner-reviewed 2026-10-26; gap-review decisions 2026-10-27 in its section 13)
- **Outcome:** Workflows are pluggable templates, the CLI and the web
  application share one engine service layer, and artifacts are shared per work
  across workflows.
- **Scope:**
  - A workflow registry and per-template definition schema replace the
    hard-coded translation-only definition check in `workflow/src/engine.py`.
    Templates combine JSON declarations with Python engine classes; derived
    engines such as formatting are reusable across workflows.
  - Generic stage kinds: agent stage (with per-chapter repeated instances),
    metadata review, artifact acceptance, and export.
  - One service API for creating a run from a chosen workflow and either an
    uploaded file (new work) or an existing work, stepping, replying to gates,
    accepting, retrying, restarting a chapter, stage, or unfinished workflow,
    stopping, reading events, and editing metadata. The CLI becomes a thin
    client of this API and takes the server root as an argument. Pause and
    resume move to M3.
  - A server-level run and work index with an owner on every record, alongside
    the existing per-run state.
  - A per-work artifact library with checkout and publish, an append-only
    publication log, one unfinished run per work (formatting runs included),
    and accepted output published as immutable versions (`<workflow>/vNNN/`); a completed run never blocks a new run (owner correction, 2026-10-28). Shared
    metadata can also be edited at the work level while no run is unfinished.
  - A required metadata review gate after preparation. Versioned metadata edits:
    each change increments `record_revision`, retains a snapshot, and records an
    event. Edits are refused while an agent turn is running, fields the run
    depends on (such as `manuscript_language`) are locked once the run exists,
    and edits after confirmation are recorded in history only.
  - Final acceptance is irreversible and reported through
    `available_actions`; an engine update requires restarting unfinished runs.
  - `source_language` is unified as `manuscript_language`.
- **Acceptance criteria:**
  - Literary translation runs through the registry with unchanged gate behavior,
    apart from the new required metadata review; the existing workflow test
    suite passes after updates for that step and for the CLI/naming changes.
  - A test-only template can be registered and executed without engine changes.
  - Metadata history can be listed and each version inspected.
  - Formatting runs as a derived template on an accepted-output publication and
    uses that output's manuscript language.
  - A second run on an existing work reuses the published metadata (it prepares
    again); creating a run on a work with an unfinished run is refused.
  - Restarting a chapter archives its work, restores glossary and voice from the
    last completed chapter, and translates only that chapter again; restarting a
    stage or an unfinished workflow keeps receipts and events.
  - After final acceptance, the run's own chapters/stages cannot be restarted;
    new runs on the work publish the next version. After an engine update,
    unfinished runs allow only reading and restarting the workflow.
- **Progress:** the metadata review gate was implemented first (2026-10-26).
  On 2026-10-27 the remaining scope was implemented: the template registry and
  `template.json` files, the split into
  `Engine` / `PreparedManuscriptEngine` / `TranslationEngine`, template-declared
  gates, per-chapter iterations, retry and chapter/stage/workflow restarts, the
  engine-update check, the work library, the service API and index, the thin
  CLI with `--server-root`, formatting as a derived template, work-level
  metadata edits, import, and the test-only template. Each acceptance criterion
  has a deterministic test (`workflow.tests.test_workflow`: 51 passed). A live
  《刺秦》 E2E run (Codex 0.163.0, `--auto-approve-recommended --format-docx
  --renderer word`) completed on 2026-10-27 through the service: preparation
  of the DOCX into ten sections, delegated metadata confirmation published to
  the work library, ten chapters each in its own agent thread (56 delegated
  decisions), finalization that published the accepted output and made
  translation read-only on the work, and a derived formatting run that produced
  a verified 38-page Word DOCX. All automated checks passed. The human-only
  evidence checks and literary quality remain unreviewed (launcher exit 2,
  as designed). The owner marked M1 done on 2026-10-27 after these results; no
  separate line-by-line code review is recorded.

### M2 — DOCX manuscript intake

- **Status:** `done` (marked by the owner on 2026-11-05)
- **Owner:** `cli1980`
- **Outcome:** Preparation accepts DOCX uploads through an extraction adapter with
  source comparison.
- **Acceptance criteria:**
  - A DOCX manuscript produces a verified chapter package, and
    `validate_preparation.py --check-sources` succeeds. Met in live runs:
    《房客》, 黑松石, and 《刺秦》 were prepared from DOCX, and the E2E
    preparation-validation check (that validator with local source checks)
    passed.
  - ~~Unsupported DOCX content blocks preparation instead of being silently dropped.~~
    Removed from the criteria by the owner on 2026-11-05; not demonstrated by a
    test or run.
- **Out of scope:** PDF intake (later).

### M3 — Web MVP for literary translation

- **Status:** `done` (closed by the owner on 2026-11-12; started 2026-10-27
  at the owner's direction, before M2)
- **Owner:** `cli1980`
- **Progress (2026-11-12, committed locally):**
  - Built:
    - A FastAPI backend (`studio/server/`) over the M1 service. It is
      localhost-only, with an explicit loopback preview-origin option.
    - A background worker that runs turns until a human is needed, with
      pause-after-turn and resume.
    - A React/TypeScript (Vite) frontend (`studio/frontend/`) with three
      views:
      - Works: manuscript intake, the work list, library, metadata,
        publication log, and derived formatting.
      - Workflows: the dashboard, starting a workflow on a work, and the
        run view with `available_actions` controls, native gate forms,
        irreversible final acceptance, and a timeline.
      - The in-run chapter viewer, where translation decisions are made.
  - Live change feed (owner request, 2026-11-10): pages follow server-sent
    change fingerprints instead of polling, with a snapshot fallback.
  - Download of the original upload from the work page (owner decision,
    2026-11-10), under its uploaded name.
  - Remote deployment, login, and the unauthenticated-access acceptance
    criterion moved to the standalone remote-mode milestone with multi-user
    and role support (owner decision, 2026-11-12). M3 is localhost-only.
  - Closure: the owner directed M3 to be closed on 2026-11-12 after the scope
    changes and acceptance-evidence discussion. Translation run `dcc6b1e2`
    completed and finalized on 2026-11-07 with 26 human-attributed gate
    receipts, human final acceptance, a completed live-model whole-book
    consistency pass, and an export.
  - Verification limits retained at closure: the run history does not
    independently distinguish browser decisions from CLI decisions. The live
    consistency review was confirmed clean and proposed no fixes; applying
    approved consistency fixes is covered by deterministic tests, not that
    live run. Closure does not claim additional human quality review or
    testing beyond the recorded evidence.
- **Depends on:** M1, M2
- **Outcome:** A user can run a complete literary-translation workflow from the
  browser.
- **Scope:**
  - FastAPI backend and React/TypeScript frontend built on the M1 service API.
  - Add a DOCX or Markdown manuscript on the Works page (creating a new work);
    start a workflow on an existing work from the workflow page.
  - A background worker runs agent turns automatically until the run needs a
    human (gate, acceptance, blocker, or failure); replies resume it.
  - A dashboard, run controls, live progress/history, read-only chapter review,
    versioned metadata, native gates, and irreversible final acceptance.
    Detailed interaction contracts are maintained in
    [UF-03 through UF-18](docs/ux/README.md#flow-inventory), the
    [screen contracts](docs/ux/README.md#screen-contracts), and
    [dated decisions](docs/ux/decisions/UXD-001-interaction-contracts.md).
  - Whole-book translation consistency (owner addition 2026-10-28; implemented
    2026-11-06; closed with M3 on 2026-11-12 subject to the recorded limits).
    Objective fixes require receipt-backed decisions, separate closure, and
    exact-fix/content verification before acceptance. Coverage and proposals
    bind source/output hashes; promotion validates candidate copies, and
    `run.json` retains per-chapter applied fixes.
    [UF-07](docs/ux/flows/UF-07-translate.md) owns the review/recovery interaction.
  - Localhost-only deployment, with the explicit loopback preview-origin option.
    Codex credentials are configured server-wide. Remote deployment and login
    belong to the standalone remote-mode milestone.
- **Acceptance criteria:**
  - A DOCX manuscript can be taken from upload through every translation gate to
    acceptance and export entirely in the browser.
  - The user can tell from the GUI what a run is doing and what it needs from them,
    and can pause, resume, retry, restart, and stop it. Only controls valid for
    the current state are offered, and no control bypasses a human gate or loses
    saved state other than the chapter or stage being explicitly restarted.
  - Final acceptance cannot be submitted without confirming the finalization
    notice, and finalized runs clearly show that they are read-only.
  - Final acceptance is offered only after the whole-book consistency pass is
    closed, and every applied consistency fix is recorded against the chapter
    it changed.
- **Review decisions:** the 2026-10-28 implied-closure decision and its
  chapter-approval exceptions are preserved in
  [UXD-001](docs/ux/decisions/UXD-001-interaction-contracts.md). The domain
  validators remain authoritative; the UX migration does not change them.
- **Out of scope:** DOCX formatting in the web application, PDF intake, user
  management and roles, remote deployment, real-time collaboration, non-English
  targets, and manual manuscript text editing.

### M4 — Literary Edit workflow

- **Status:** `in_progress` (CLI template started ahead of M2/M3 at the owner's
  direction on 2026-10-27; web support still depends on M3)
- **Owner:** `cli1980`
- **Depends on:** M1; M3 for web support
- **Outcome:** A Literary Edit workflow is available in both the CLI and the web
  GUI.
- **Scope:** template `literary-editing-v1`, shared preparation/metadata,
  developmental recommendations (including `DEV-###` whole-book findings;
  report-only), line/copy editing with shared editorial state, required
  review/application gates, final acceptance/export, and derived formatting.
  The original 2026-10-27 fixed stage sequence was superseded on 2026-11-05.
- **UX contract:** [UF-08](docs/ux/flows/UF-08-edit.md) and
  [UXD-001](docs/ux/decisions/UXD-001-interaction-contracts.md) define repeatable
  user-selected passes, pass acceptance, and implied editorial closure with
  separate application authorization. The original pass-choice change had
  deterministic and browser checks but no live-run evidence.
  - Engine design: a generic `select` stage kind. Its options are
    stages that run only when chosen and return to the selection when done;
    the engine owns the pass-acceptance and pass-choice decisions and records
    a pass history. Templates declare the options and their titles, so the
    studio renders the choice without per-workflow code. `optional` stages
    and `skip_stages` are removed. Current page behavior and remaining viewer
    work are documented in the UX specification, rather than freezing the
    historical run-page-only placement as the present design.
- **Deferred to the remaining M4 work:** developmental-stage details,
  restarting a completed editorial chapter, linking an edited translation to
  its source work, and web support.
- **Progress:** first CLI implementation (local, uncommitted): optional stages
  (`--skip-stage`), several chapter stages per template with a concluding
  whole-book step, template-declared gate commands, the `EditingEngine`, and a
  deterministic test of line and copy editing with developmental skipped
  (`workflow.tests.test_workflow`: 52 passed). A live E2E on the translated
  《刺秦》 text (uploaded as a new en-US work, developmental skipped,
  `--auto-approve-recommended --format-docx --renderer word`) completed on
  2026-10-27: preparation into a title unit plus ten sections, line and copy
  editing of all 11 units plus both whole-book passes (24 jobs, 25 delegated
  decisions), final acceptance published to the work library, and a derived
  38-page Word DOCX. All automated checks passed; human evidence checks remain
  unreviewed. The agent proposed no changes in any job (all verdicts ready, 5/5),
  so the live run did not exercise the proposal, closure, and apply path; only
  the deterministic test covers it. During the run the launcher's delegated-mode
  prompt was fixed: completed editing turns lacked guidance for the required
  recommendation field, which made the model stall until the turn timeout.

### Remote mode — multi-user and role support

- **Status:** `planned` (requested by the owner on 2026-11-12)
- **Owner:** `cli1980`
- **Priority and implementation order:** not yet decided.
- **Depends on:** M3 studio and the shared engine service layer.
- **Outcome:** A small team (fewer than 10 users) can use a remotely deployed
  studio with individual identities and role-based access to works, runs, and
  human decisions.
- **Scope:**
  - Document and configure a remote deployment with login and a configured
    HTTPS origin when not bound to loopback. Preserve localhost-only use.
  - Manage individual users, account deactivation, login/logout, and session
    revocation. Select the authentication mechanism during design.
  - Define roles and their permission matrix for administration, browsing and
    downloads, manuscript intake, metadata editing, workflow controls, gate
    decisions, and irreversible final acceptance. Decide whether access is
    shared across the team or assigned per work before implementation.
  - Enforce permissions server-side for every API, artifact download, and live
    event stream; hide or explain unavailable actions in the GUI. Role checks
    must not bypass the existing gate validation or finalization rules.
  - Attribute uploads, metadata changes, workflow controls, and human decisions
    to the authenticated user in durable history. Define trusted local CLI
    access explicitly so it cannot impersonate remote users.
  - Handle concurrent users safely: stale or duplicate decisions cannot apply
    twice, and concurrent requests cannot start conflicting runs on one work.
  - Keep runtime credentials server-side and unavailable to unauthorized users.
    Decide whether execution credentials remain shared or are user-specific.
- **Acceptance criteria:**
  - Remote mode refuses unauthenticated access to manuscript data, run state,
    downloads, live streams, and mutations; invalid remote configuration fails
    clearly rather than starting an exposed unauthenticated service.
  - Tests cover the agreed permission matrix, including direct API requests
    denied despite bypassing the GUI, and no unauthorized data in live events.
  - Account deactivation and session revocation remove access, including active
    streams; users cannot grant themselves additional permissions.
  - Two users can work on authorized works concurrently without losing history,
    duplicating a decision, or bypassing a human gate or finalization.
  - Recorded human actions identify their authenticated actor; neither history
    nor client responses expose runtime credentials.
  - A documented HTTPS deployment is verified with separate user accounts and
    different roles; localhost-only operation remains usable.
- **Open design choices:** authentication provider, exact roles and permission
  matrix, work ownership/sharing, initial administrator setup, session policy,
  CLI authorization, and shared versus per-user execution credentials.
- **Out of scope:** simultaneous manuscript text editing and real-time
  collaborative editing.

### UX enhancement — studio interface structure

- **Status:** `in_progress` for UX specification and source mapping (owner
  direction, 2026-11-13); remaining interface redesign is not implemented by
  this documentation change. Original design review recorded 2026-10-28.
- **Owner:** `cli1980`
- **Depends on:** M3 studio and existing workflow/approval contracts.
- **Outcome:** versioned, reviewable user flows and coherent work exploration,
  run inspection, reading, and decision surfaces without changing domain gates.
- **UX specification:** [index and 18 current flows](docs/ux/README.md),
  [screen contracts](docs/ux/README.md#screen-contracts), and
  [studio design/owner-decision record](docs/ux/designs/studio-interface.md).
  Detailed interface findings, phases, placement, front matter, samples,
  passage-size controls, and formatted-work hand-off are maintained there.
- **Remaining implementation scope:** selectable whole-book reading, completion
  of generic workflow presentation, version-oriented exploration/downloads,
  paragraph-aligned/accepted-version reading, and later formatted preview.
  Detailed design acceptance boundaries live in the specification, not here.
- **Progress:** initial source-mapped specification and migration prepared on
  `feature/ux`, including separate current/target behavior and a migration map.
  Mapping does not claim new browser tests, usability review, or design approval.
- **Documentation verification:** the checker validates 18 flows, six screen
  contracts, and local links across 31 Markdown documents. All 19 Mermaid
  diagrams rendered successfully with CLI 12.2.0; a representative translation
  diagram was visually inspected. Generated previews remain in ignored output.

### Translation judge improvement — sentence-level fidelity

- **Status:** `planned` (recorded by the owner on 2026-11-03 after a trial)
- **Owner:** `cli1980`
- **Depends on:** the evals judge runner (`evals/run_judge.py`) and the
  local-only case `zh-en-fangke-001`
- **Outcome:** The translation judge detects clause-level fidelity shifts that
  fluent English hides, so evals can catch the drift the owner found in the
  literary-translation workflow's output.
- **Findings (2026-11-03):**
  - In the workflow's translation of 《房客》 (run `b625857d`), the owner found
    meaning shifts in paragraph 1: 来 rendered as "go" (the narrator writes from
    inside K), the concessive and causal chain 固然…而又…便…于是 split into
    unconnected statements, 这种 rendered as "a", 空 omitted, and "seeming"
    added to 做从容. The literal Path A draft of the same run kept most of these.
  - Case `zh-en-fangke-001` (local-only; authorship and usage rights pending)
    holds the source and two candidates: the workflow's final English and its
    Path A draft.
  - With rubric v1, `azure/openai/gpt-4.1` scored both candidates 5/5 on every
    dimension.
  - A trial added a sentence-by-sentence fidelity check (point of view and
    deixis, connectives, omissions, additions, certainty) to rubric v1 and the
    judge skill, with fidelity caps. `gpt-4.1` still gave 5/5 and claimed the
    check without quoting evidence; `azure/openai/gpt-5.5` quoted minor issues
    in Path A but still found no shifts in the final English. The trial was
    reverted; rubric v1 and the judge skill are unchanged.
  - Conclusion: one call over a whole story does not perform a real
    sentence-level check, whatever the rubric says.
- **Scope (candidate approaches, not yet chosen):**
  1. **Segmented judging:** the runner splits source and candidate into aligned
     paragraph groups, judges each with a sentence-level fidelity procedure,
     and combines the findings and score caps for the whole text.
  2. **Known-issue checks:** cases record expected findings (source span and
     kind of shift); the eval checks whether the judge reports them, measuring
     the judge directly on known problems.
  3. A rubric version with the sentence-level criterion, shared with human
     reviewers, once an approach is shown to work.
- **Acceptance criteria:**
  - On `zh-en-fangke-001`, the judge reports the five known paragraph-1 shifts
    in the workflow's final English and scores its fidelity below 5.
  - The judge does not report natural restructuring that preserves viewpoint,
    logic, qualifiers, and certainty as a shift.
  - Any rubric change gets a new rubric version, and the judge skill's embedded
    copy matches it.

### Runtime extensibility — harnesses and inference endpoints

- **Status:** `planned` (requested by the owner on 2026-11-06)
- **Owner:** `cli1980`
- **Priority and milestone assignment:** not yet decided.
- **Outcome:** Users can switch from the current Codex App Server to another
  supported agent harness and inference endpoint through configuration, while
  retaining the same workflows, skills, review interfaces, and saved work.
  Adding a provider does not require rewriting the workflow engine.
- **Starting point:** [workflow/src/runtime.py](workflow/src/runtime.py) defines
  a small `Runtime` protocol and the current `CodexRuntime` adapter. Extend this
  boundary rather than spreading provider-specific behavior into templates,
  the service, or the studio.
- **Scope:**
  - Separate the **agent harness** (tool execution, workspace access, skill
    loading, session lifecycle, and agent turns) from the **inference endpoint**
    (model service, model selection, authentication, and request configuration).
    A harness may support several endpoints; supported combinations are
    declared explicitly rather than assuming every harness works with every
    endpoint.
  - Define extensible adapter contracts and registration for harnesses and
    endpoints. Keep workflow results, events, errors, usage reporting, and
    cancellation/recovery behavior consistent at the engine boundary.
  - Introduce named execution profiles selecting a harness, endpoint, model,
    and relevant options. Use the same profile configuration in the CLI and
    studio; retain Codex App Server as one supported adapter.
  - Declare and validate capabilities, including tools, workspace access,
    structured output, session resume, and cancellation. An incompatible
    profile must explain the missing capability before execution starts.
  - Support switching profiles for new runs and unfinished runs at a saved
    turn boundary, without losing artifacts, human decisions, or completed
    work. Provider-specific sessions are not assumed portable: when needed,
    start a fresh session from durable workflow state and resume the pending
    step. A switch must not bypass a gate, replay an approved operation, or
    require retranslating completed chapters.
  - Keep credentials in server-side configuration or secret references.
    Record the effective harness, endpoint identity, model, and configuration
    revision per execution attempt so work remains attributable after a
    switch; exclude secret values from events and exported records.
- **Acceptance criteria:**
  - The existing Codex App Server and at least one alternative harness can
    execute the same workflow through the common runtime contract.
  - At least one harness can use two supported inference endpoints selected
    through configuration, without engine or workflow-template changes.
  - A run can switch a supported harness or endpoint at a saved boundary and
    continue with its artifacts and approvals intact, including when the new
    harness needs a fresh session.
  - The CLI and studio expose the effective execution profile consistently;
    the chapter viewer and human gate behavior remain the same across profiles.
  - Shared adapter tests cover structured results, tool/workspace requirements,
    event and error handling, cancellation, retry, and state recovery.
    Integration checks exercise each supported combination; unsupported
    combinations fail with an actionable explanation.
- **First tryout — Pi** (selected by the owner on 2026-11-06; `planned`):
  - Build a small `PiRuntime` adapter using Pi's subprocess
    [RPC interface](https://pi.dev/docs/latest/rpc), alongside `CodexRuntime`.
    Pin the tested Pi version and verify native Windows operation, workspace
    and skill loading, session recovery, events, and cancellation.
  - Prove the structured result contract with a schema-validated workflow-result
    tool or equivalent extension. Pi's JSON event stream alone does not
    constrain the final model response; the engine's validation remains
    authoritative.
  - Compare Codex and Pi using the same model and endpoint where both support
    them, recording any differences that prevent a controlled comparison.
    Then exercise Pi with two inference endpoints selected through profiles.
  - Run a small literary-translation case through preparation, chapter review,
    whole-book consistency with approved and rejected fixes, and final
    acceptance/export. Exercise interruption, retry, and switching profiles
    at a saved boundary, including recovery through a fresh harness session.
  - **Exit criteria:** artifacts, receipts, and completed chapters survive
    switching; human gates and exact-fix validation cannot be bypassed;
    malformed results fail clearly; CLI and studio retain the same workflow
    behavior. Record correctness, model quality, latency, usage where available,
    and integration limitations before deciding whether to adopt Pi.
  - **Status boundary:** Pi is selected for evaluation, not yet implemented,
    validated, or selected as the default harness.
- **Open design choices:** the initial inference endpoints and models,
  concrete adapter interfaces, profile storage and selection UI, and the
  capability matrix. No implementation schedule has been selected.

### Deterministic DOCX formatting in the studio

- **Status:** `planned` (requested by the owner on 2026-11-08 after a
  feasibility review)
- **Owner:** `cli1980`
- **Priority and milestone assignment:** not yet decided.
- **Outcome:** Formatting an accepted version in the studio needs no agent.
  The user sets the design in a form, the host builds and renders the DOCX, and
  the user approves the rendered pages before publication and hand-off.
- **Starting point:** the built-in path is already mostly deterministic.
  [workflow/src/document_adapters.py](workflow/src/document_adapters.py)
  validates the settings, checks fonts, builds the DOCX, renders it with Word or
  LibreOffice, converges TOC page numbers, and rasterizes every page;
  [workflow/src/formatting.py](workflow/src/formatting.py) audits text, order,
  and heading styles, then publishes and hands off. The agent only proposes the
  settings as an approval sheet, records receipts, and attests a visual review
  of every page.
- **Scope:**
  - Replace agent proposals/attestation with host-owned settings and exact-build
    page-review receipts. The [target UX flow and screen contract](docs/ux/designs/deterministic-formatting.md)
    own the presets, settings form, review gallery, and revision interaction.
  - The build runs as a worker job, one renderer instance at a time; revised
    settings rebuild into a new build directory.
  - Automated checks support that review: fonts in the rendered PDF match the
    settings, no blank pages, no stranded headings, and the page count.
  - Remove the agent stage, its prompts, and the attestation checks from the
    built-in path; edition identity no longer depends on a model or skill hash.
    The `format-manuscript` skill remains for plugin use outside the studio.
- **Acceptance criteria:**
  - An accepted version is formatted entirely in the browser without an agent
    turn; identical settings and renderer produce identical text, structure,
    and pagination checks.
  - No DOCX is published without a receipt-bound settings approval and a
    page-review approval of that exact build.
  - Existing content, heading, TOC, and page-number checks still pass; the new
    automated checks fail clearly.
  - Formatter tests run with a stand-in renderer, without Word or LibreOffice.
- **Known limits (existing in both paths):** English output only (the Contents
  label is hard-coded); scene-break rules (`***`, `---`), lists, images, code,
  and special forms such as poetry are refused; Word rendering requires a
  Windows server, otherwise LibreOffice, whose pagination can differ.
- **Open decisions:** interaction options and review location are recorded in
  the [formatting target](docs/ux/designs/deterministic-formatting.md).
  Supporting scene breaks/non-English output and retaining the external
  Documents-skill path remain unresolved scope decisions.

### Later (unordered)

- DOCX formatting from the web application
- PDF manuscript intake
- Additional workflows, such as literary-agent querying
- Immediate pause by interrupting the current agent turn (removed from M3 on
  2026-11-10). Worth revisiting if turns get much longer. App Server's
  `turn/interrupt` and the engine's existing `PAUSED` handling for an
  interrupted turn cover most of it; the runtime needs a cancel signal and the
  worker a handle on each run's current turn.
