# Manuscript Studio roadmap

This is the shared roadmap and development progress record for humans and agents.

The highest-priority current focus is
[deterministic DOCX formatting in the studio](#deterministic-docx-formatting-in-the-studio),
as directed by the owner on 2026-11-13. It takes precedence over other planned
or unfinished work. Literary translation and editing remain supported workflows;
their remaining work is not removed by this priority change.

## Conventions

- Milestones are outcome-based and ordered by priority. They have no target dates.
- Every milestone is owned by the project owner, `cli1980`, unless stated otherwise.
- The roadmap file stays at `roadmap.md`, which is where [AGENTS.md](AGENTS.md) points.
- All planned work, milestones, scope, and progress live only in `roadmap.md`.
  The GitHub Project
  [Manuscript Studio Requirements](https://github.com/users/cli1980/projects/2) is
  used only to collect and triage external requirements (New, Triage, Accepted,
  Declined, Moved to roadmap). Accepted requirements are added to `roadmap.md`,
  which then tracks them.

## Cross-cutting decisions

- **Outdated-run cancellation unblock (2026-11-15):** engine changes no longer
  disable Stop on unfinished, unfinalized, idle runs. Execution with outdated
  code remains refused, while cancellation retains artifacts/history and releases
  the work for a new run. The work page explains the unfinished-run blocker and
  links directly to it. Verified 76 workflow/API tests, including outdated-run
  stop/new-run regressions, and the frontend build. Restarted Studio on the same
  data root; confirmed the remaining waiting run now exposes Stop. No live run
  was cancelled automatically; the user must confirm that irreversible action.

Agreed in the 2026-10-26 planning session:

- **Licensing** (owner decision, 2026-10-27; applies from the next commit). The
  copyright holder is Crossborder Art & Media LLC. Skills (`plugins/`) and
  `evals/` stay MIT. `workflow/` and `studio/` are licensed under PolyForm
  Noncommercial 1.0.0; commercial use requires a separate license negotiated
  with the copyright holder. Already-published MIT versions of `workflow/` stay
  MIT. `fixtures/` keep the terms recorded with each fixture.
- **Intake on the Works page** (revised by the owner on 2026-10-27; originally
  "workflow first, then upload"). Manuscripts are added on the Works page, each
  upload creating a new work, and the Works page is the standard place for
  workflow intake and outcomes. Workflows are started from the workflow page on
  an existing work; preparation remains each run's first stage.
- **Manuscripts are immutable.** Manuscript text changes only through workflow
  stages and their human gates. The GUI presents the original upload, prepared
  chapters, and workflow outputs read-only.
- **Metadata is editable and versioned.** Shared `work.json` metadata can be edited
  from the GUI. Every change is versioned and attributable.
- **User-confirmed metadata is grounded** (owner clarification, 2026-11-15).
  Title/subtitle remain editable in the initial manuscript form. Source-evidence
  requirements constrain agent proposals, not the user's chosen title. Confirmed
  or supplied values, including deliberate clearing, take precedence over agent
  proposals; inference field groups must not remove manual entry.
  Verified: 76 workflow/API tests, 30 preparation tests and a browser regression
  saving a user-chosen title absent from the manuscript pass, as does the build.
- **Language may be unknown at intake** (owner clarification, 2026-11-15).
  There is no Chinese default or mandatory language entry. Preparation infers the
  language from manuscript text and must establish it before becoming ready;
  uncertain cases request clarification. Downstream settings use that result.
  Implemented in intake, the preparation hand-off and translation settings:
  75 workflow/API tests, 26 preparation-contract tests and two browser checks
  pass; typecheck/build and LF checks pass. Detection hand-off uses scripted
  preparation in tests, not a new live-model accuracy evaluation.
- **Source-supported title extraction** (owner correction, 2026-11-15).
  Preparation can propose missing title/subtitle from quoted manuscript text;
  supplied values and deliberate clearing remain protected. Ready preparation
  cannot silently omit a source title, while generated headings for untitled
  sources do not establish an actual title. Work names/languages read published
  metadata rather than treating the intake filename as another authority.
  Verified with 76 workflow/API tests, 29 preparation tests, two browser checks
  and frontend build. A read-only isolated-copy recheck of the owner's novel
  rejects the original missing-title record, accepts the extracted source title
  and retains the already inferred `en`; no approved records were rewritten.
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
- **Finalization.** Final acceptance is irreversible: the workflow becomes
  read-only on that work and nothing in the run can be restarted. Changes
  require adding the manuscript again as a new work. The GUI must notify users
  prominently before and after acceptance.
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
    depends on are locked for downstream execution; `manuscript_language` may
    start unknown and is established by verified preparation,
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
  - After final acceptance, the run's own chapters and stages cannot be restarted (new runs on the work publish the next version), and
    are refused; after an engine update, unfinished runs allow reading, stopping
    and restarting the workflow, but not resuming outdated stage execution.
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
  - An intuitive workflow dashboard and run view for inspecting status: overall
    state, current stage and chapter, progress, the pending human action, the
    reason for any blocker or failure, and a timeline with a live event stream.
  - Workflow controls with clear availability and confirmation:
    - **Pause:** stop automatic execution after the current agent turn,
      preserving saved state. Immediate pause by interrupting the turn was
      removed from M3 (owner decision, 2026-11-10): across 121 measured turns
      the median was 1.4–1.9 minutes and the longest 7, so waiting for the turn
      costs little, while interrupting discards its work. See Later.
    - **Resume:** continue automatic execution from the saved state.
    - **Retry:** retry the current step from saved state with a fresh agent
      thread after a failure, block, or pause.
    - **Restart chapter / stage / workflow:** discard and redo one chapter, one
      stage, or an unfinished workflow, as defined in the M1 design. There is
      no checkpoint rollback.
    - **Stop:** cancel the run permanently, retaining its artifacts and history.
  - A prominent notice before final acceptance that accepting finalizes the run
    and makes the workflow read-only on the work, with explicit confirmation;
    a persistent banner on finalized runs; and a notice listing runs that must
    be restarted after an engine update.
  - Download of the original upload, and read-only views of prepared chapters
    and workflow outputs. A download replaces viewing the original upload
    (owner decision, 2026-11-10): the chapter viewer already shows its
    verified prepared text, and the file itself opens faithfully in Word.
  - Metadata editing with version history.
  - All translation gates as native forms driven by the approval-sheet JSON and
    submitted through the existing validator and parser; final acceptance with
    source and English side by side. The Markdown export download was removed
    from M3 (owner decision, 2026-11-10); downloads of accepted versions are
    planned in the UX enhancement's works explorer.
  - Whole-book translation consistency (added by the owner on 2026-10-28;
    implemented locally on 2026-11-06; closed with M3 on 2026-11-12, subject
    to the verification limits recorded above). Chapters carry continuity through shared files
    (`glossary.md`, `voice.md`, completed English chapters, and the chapter
    brief). After the last
    chapter and before final acceptance, the translation workflow runs one
    whole-book consistency pass over all English chapters against the source and
    continuity files: names and terminology, forms of address, voice drift per
    character or narrator, and cross-chapter references. It proposes only fixes
    for objective inconsistencies, as one approval sheet decided in a single
    submission with separate closure; it does not retranslate or restyle.
    Approved fixes are applied and the affected chapters re-verified before
    acceptance. The literary-translation skill defines the pass, and the
    template adds it as a concluding whole-book step.
    - Completion of all saved chapters automatically starts a distinct
      whole-book job. Its review and final acceptance stay in the chapter
      viewer, with chapter links on findings and separate whole-book progress.
    - The engine binds coverage and proposals to source/output hashes, requires
      receipt-backed approve/reject decisions and separate closure, and checks
      candidate copies against the exact approved fixes before promoting them
      together. A clean review also requires explicit confirmation.
    - A retry resumes the job; restarting any chapter invalidates its review.
      Applied fixes are recorded per chapter and in the accepted version's
      `run.json`; restarting consistency preserves completed chapter outputs.
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
- **Implied closure for advice-type sheets** (owner decision, 2026-10-28;
  implemented with the front-matter change in `d9896c5`): the separate closure is redundant where a later step shows the
  full result. For translation advice and map exceptions, a submission that
  decides every item with resolving decisions counts as final closure; a
  discuss or revise decision still produces a new revision of the same sheet.
  Chapter approval keeps its own decision: "Approve chapter" without edits, and,
  when the final check proposes edits, a separate closure presented as approving
  the chapter with those edits, because nothing later shows the final text.
  Changes the approval-sheet and translation skill contracts, the engine's
  closure handling, the translation template, the studio review screen, and
  tests; unfinished runs need a workflow restart.
  - Manuscript text cannot be modified from the GUI outside workflow gates.
  - Metadata edits are versioned and visible in history.
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
- **Scope agreed so far (2026-10-27):** template `literary-editing-v1`:
  preparation (reused) → metadata review → optional developmental editing
  (chapter evidence, then one whole-book verdict and `DEV-###` recommendations
  at a revision/approval gate; report only, no text changes) → line editing →
  copy editing (each chapter by chapter with shared style sheet, continuity
  concordance, and editorial brief; per chapter a decision review with separate
  closure, then an explicit apply authorization; each stage ends with a
  whole-book consistency pass with its own gate) → final acceptance → export.
  Formatting reuses the unchanged derived template after acceptance. Text to
  edit, including a translation, is uploaded as a new work.
- **Editing passes chosen by the user** (owner decision, 2026-11-05; replaces
  the fixed developmental → line → copy sequence and optional stages;
  implemented locally and uncommitted, covered by deterministic tests and a
  browser check of the pass decisions, not yet by a live run):
  1. Preparation and metadata review.
  2. The user picks one pass: developmental, line, or copy editing. When the
     pass completes, the user accepts its output in a separate decision; the
     accepted text and editorial files are the next pass's input. Step 2
     repeats as often as the user wants, in any order, including the same pass
     again. There is no discard: a pass is redone with a stage restart before
     it is accepted.
  3. Final acceptance (irreversible), offered after metadata review and after
     every accepted pass, including with zero passes. After it no further pass
     can run.
  4. Export, automatic after final acceptance, as in every workflow.
  - Design: a generic `select` stage kind in the engine. Its options are
    stages that run only when chosen and return to the selection when done;
    the engine owns the pass-acceptance and pass-choice decisions and records
    a pass history. Templates declare the options and their titles, so the
    studio renders the choice without per-workflow code. `optional` stages
    and `skip_stages` are removed. The studio adds an `EditingWorkflowUI`
    page-behavior class, keeping decisions on the run page until the viewer
    supports editing.
- **Implied closure for editorial reviews** (owner decision, 2026-11-05;
  uncommitted): the separate closure after item decisions is removed, as for
  translation advice. A submission that decides every item with resolving
  decisions closes the editorial review; a reopening decision still produces a
  new revision. The apply authorization stays, because it shows exactly what
  changes before the text is edited. A chapter with proposals now takes two
  decisions instead of three. Changes the template (`"closure": "implied"`),
  the editing engine's instructions to the agent, the E2E launcher, and tests;
  unfinished editing runs need a workflow restart.
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

- **Status:** `planned` (recorded by the owner on 2026-10-28 from a design review)
- **Owner:** `cli1980`
- **Depends on:** M3 studio as implemented locally (`studio/`)
- **Outcome:** The studio is organized as four distinct interfaces: an
  evolving page viewer, a separate run inspector, a separate works explorer,
  and one unified decision GUI for every kind of approval. The workflow engine
  and its gate model do not change.
- **Findings (design review, 2026-10-28):**

  | Perspective | Fit today | Main gaps |
  |---|---|---|
  | Evolving page viewer | Partial | Chapter text is shown as whole blocks without paragraph alignment; the viewer exists only inside a run, not for accepted versions |
  | Separate run inspector | Partial | The run page still hosts the metadata review and final acceptance forms; the timeline is a raw event list |
  | Works explorer | Mostly | The work page mixes browsing with actions; the library is a flat file list rather than workflow → version |
  | Unified approval GUI | No (UI level) | Six different form components for one engine gate model |

- **Scope:**
  1. **Unified decision panel.** The engine already models every decision the
     same way (kind, optional bound text, optional approval sheet, offered
     commands, closure, recorded receipt), but the UI uses six components:
     the item-by-item review (translation advice), the list form (map
     exceptions and other sheets), free replies (questions, continuation), the
     chapter approval panel, the metadata gate, and final acceptance. Replace
     them with one decision panel driven by the gate: a header saying what is
     being decided and why, the conversation so far (the reviewer's feedback
     and the agent's answer), a body by shape (the item-by-item review for every
     sheet, command buttons, a feedback box), one closure pattern, and one
     style for irreversible actions. Metadata review and final acceptance keep
     their own bodies inside the same frame.
  2. **Run inspector.** The run page becomes inspection and control only:
     stage progress, chapter progress, a readable decision history (receipts,
     already summarized in each version's `run.json`), errors, and controls,
     with no forms. Decisions move to the page viewer (see the frontend
     structure decision below).
  3. **Works explorer.** The library is browsed as workflow → version → files,
     using the version preview card from the format panel (`run.json` and
     `manifest.json`). The work page is organized into sections: overview and
     metadata, versions (with formatting and downloads), runs, and library and
     publication log. Add downloads, a preview of the original source
     document, and comparison between metadata versions. Intake stays on the
     Works list.
  4. **Evolving page viewer.** Give the viewer its own document model: the
     prepared paragraphs plus per-stage versions, numbered by paragraph (as the
     passage map already is). The content source is selectable: the run in
     progress or an accepted version (`<workflow>/vNNN`). Split the viewer into
     a reading area and a decision area so new layouts (aligned source and
     target, diffs for line and copy editing, single-language reading,
     highlighting of sheet item locations) do not touch decision logic, and so
     several editing stages and the whole-book pass fit in one view.
- **Metadata review on the front-matter chapter** (owner decision, 2026-10-28;
  implemented after the 黑松石 run completed, in `d9896c5`):
  - Every prepared work starts with exactly one front-matter unit, split
    verbatim from the source: the material before the first chapter, and at
    least the title heading. The prepare-manuscript skill contract and its
    validator enforce it; workflow, studio, skill, and evaluation fixtures are
    updated accordingly.
  - The engine attaches the metadata review gate to that front-matter chapter
    (the metadata record itself stays work-level and shared), so the studio
    shows metadata review in the page viewer beside the prepared front matter,
    through the same routing as every other chapter decision, without a
    special case.
  - Applies to the translation and editing templates; unfinished runs need a
    workflow restart when it lands.
  - A missing title is not a blocker (owner decision, 2026-11-10, replacing
    the earlier "stop and ask the user"; implemented and committed locally). Preparation
    uses every available source of a title, in order: the work's metadata
    title, the source document's own title property, then the file name. It
    writes the title as the front matter's opening heading and records it as
    `supplied_title` (text, basis, evidence). The validator checks that the
    heading matches the record. The metadata review on the front matter, and
    the front-matter page in the chapter viewer, show that the title was
    supplied, so the user approves it there. A corrected title takes effect
    when preparation is restarted.
- **Extensible front-matter reviews; translation brief** (owner decision,
  2026-11-03; implemented and committed locally on 2026-11-03; a live
  end-to-end run on 《房客》 exercised the brief with delegated approval only):
  - The front-matter page is extensible per workflow: besides the shared
    metadata review, a template can declare its own front-matter stages
    (`"front_matter": true`) whose gates present workspace `documents` for
    approval with a declared command. Every such review uses the same
    front-matter page in the chapter viewer.
  - `literary-translation-v1` adds a `brief` stage after metadata review: the
    agent drafts `glossary.md` and `voice.md` from the whole prepared
    manuscript; the user approves them (`approve brief`) or sends corrections
    the agent applies. The approved files are the starting point for every
    chapter. Direct editing of the files in the studio is not included
    (owner choice: feedback only).
  - Tryout samples (owner decision, 2026-11-04; committed locally): the brief
    also translates three randomly picked passages three ways each into
    `brief-samples.md`. A `brief_samples` poll on the front-matter page shows
    each original beside its variants; the user picks one per sample, with
    optional reasons, before approving the brief. The samples carry forward
    like the glossary and voice and guide tone and voice, without binding later
    passages. The brief approval page renders its documents as formatted
    Markdown (`react-markdown`, used across the studio).
  - Changes the template, engine, translation skill contract, studio, and
    tests; unfinished translation runs need a workflow restart.
- **Per-run maximum passage size** (owner decision, 2026-11-03; implemented
  and committed locally): `literary-translation-v1` declares a default
  (1,500 characters for Chinese, Japanese, or Korean; 800 words otherwise).
  A run may choose another value when it starts (the start panel's Advanced
  section, the service, or `--passage-size`); the value is fixed for the run
  and kept on a workflow restart. The engine refuses a passage map with a
  longer passage unless an `oversize` exception for its exact range is
  approved through the existing map-exceptions review. One live run on
  《房客》 divided the story into three passages within the default.
- **Frontend structure** (owner decision, 2026-11-04):
  - Four components: the **work explorer** (works list, intake, work page),
    the **workflow explorer** (the cross-work list of runs, today's
    "Workflows" tab, with filters such as workflow, status, and needs-me), **run
    management** (status, progress, timeline, and controls only), and the
    **chapter viewer** (the run's review page). Shared widgets serve all four:
    the decision panel (approval sheets, sample poll, document review, chapter
    approval, metadata review, final acceptance), the Markdown and document
    viewer, the metadata editor, and status and progress tags.
  - A run can be started from both the work explorer and the workflow explorer.
  - Each workflow defines its page behavior in the frontend (`studio/frontend/src/workflows.ts`: a base
    class keeping everything on the run page, with per-workflow subclasses). Literary translation makes
    every decision in the chapter viewer, and starting a run opens it; formatting keeps its decisions on
    the run page and has no chapter link. Literary editing (owner decision, 2026-11-05; uncommitted) follows
    translation through a shared `ChapterViewerWorkflowUI` base: starting a run and every decision open the
    viewer; pass choices and whole-book decisions show at the end of its content column.
  - Viewer and decision design (owner review, 2026-11-05; uncommitted): the chapter viewer, decision panel,
    and agent feedback widget are generic and hold no workflow-specific text or gate kinds. Each workflow's
    `WorkflowUI` defines what differs: the reading panes (`panes()`: translation shows two, the original and
    the translation, with inline comments on a draft awaiting approval; editing shows one, the text being
    edited), decision wording (`decisionCopy()`: heading, explanation, button labels), chapter statuses
    (`awaitingLabel()`, `stageVerb()`), the notice after a reply (`afterReply()`), and the agent's name.
    The translation-only chapter approval component is replaced by the shared decision slot.
  - One decision placement rule (owner request, 2026-11-08; implemented): every decision follows the reading
    area regardless of its gate kind. A chapter's decision sits under that chapter's text; decisions not tied
    to one chapter (whole-book jobs such as the developmental verdict and consistency reviews, pass choices,
    final acceptance) sit at the end of the content column and are scrolled into view once. Only before
    chapters exist is the decision the page's sole content. This replaces the earlier top placement and its
    translation-consistency exception.
  - Phase 1 (implemented and committed locally, 2026-11-04): starting a run opens the
    viewer; the viewer shows a run status bar with problem banners linking to
    run management, preparation questions before chapters exist, and final
    acceptance; the run page links to the viewer instead of showing decision
    forms for chapter-based runs.
  - Shared agent feedback widget (owner decision, 2026-11-05; uncommitted): every exchange with the agent in any
    workflow (approval sheets, chapter approval, editorial reviews, apply authorizations, questions) uses one
    widget (`AgentFeedback`): the conversation so far, the item-by-item review for every sheet, otherwise the
    offered commands and a feedback box or inline comments. The list-style sheet form and free-reply form are
    removed; the brief's document review, the sample poll, metadata review, pass choices, and final acceptance
    keep their own bodies.
  - Inline comments (owner decision, 2026-11-04; committed locally): feedback on text is given as inline
    comments on the translation (not the original) and on the brief documents, using Recogito's text
    annotator. Drafts stay in the browser until sent; each comment keeps its quote, range, and paragraph
    number so a later source/translation alignment can show it beside the matching original paragraph.
    Comments are sent as ordinary feedback, so the engine is unchanged.
  - Phase 2 (planned): a "Whole book" entry in the viewer for decisions not
    tied to one chapter, such as literary editing's developmental verdict and
    consistency passes. Needs a small web-API addition, because the chapter
    endpoint does not serve the internal whole-book ID (`_whole`); today these
    decisions have no reading page of their own. Needed before the editing
    workflow is used in the studio.
    - The chapter list gains a "Whole book" item after the last chapter,
      selectable and routed like a chapter.
    - The chapter endpoint serves `_whole` with the whole-book job's reading
      material (for example the developmental report, or the consistency
      findings with links to their chapters) and its status per stage.
    - The `WorkflowUI` defines the whole-book panes (`wholeBookPanes()`), so
      the job's material is the reading area and its decision follows it
      through the same placement rule as any chapter.
  - Phase 2b (planned): remove the remaining workflow-specific code from the
    generic chapter viewer (`studio/frontend/src/views/Chapters.tsx`), as the
    viewer and decision design requires. Today it still contains the
    whole-book label check for literary translation, the translation-only
    whole-book consistency banner in the run status bar, and the "Applied
    consistency fixes" panel. Move them into `WorkflowUI` overrides, for
    example `wholeBookLabel()`, `statusNotice(run)`, and
    `extraPanels(chapter)`, with neutral base defaults. Acceptance: the viewer
    references no workflow IDs or gate kinds, and translation and editing runs
    render as before.
  - Phase 3 (planned): formatting decisions (settings sheet, visual check) stay
    on the run page until a formatted-document preview exists, then move into
    the viewer as a "Formatted document" entry that reuses the decision panel.
- **Formatted output becomes a new work** (owner decision, 2026-11-05;
  committed locally; derived metadata uncommitted): formatting stays the optional "Format
  this output" step after a completed translation; when it completes, its DOCX
  automatically becomes a new work in Works, linked to the original work and
  run, with metadata derived from the original rather than copied: the title
  from the translated front matter, language-neutral facts (work type, form,
  audience, series position and relationship, contributors for review), and
  `original_language`; free text in the original's language starts empty for
  the new work's preparation to infer. Ready for further workflows such as
  editing. This also covers M4's open item on
  linking an edited translation to its source work, for formatted output.
- **Suggested order:** 1 (unified decision panel), 2 (run inspector), 3 (works
  explorer by version), 4 (paragraph-aligned page viewer; the largest piece,
  needed before the editing workflow reaches the GUI). All four are frontend
  and web-API changes; runs in progress are unaffected.
- **Acceptance criteria:**
  - Every human decision, of any kind, is presented by the same decision panel
    with a consistent header, conversation, closure, and irreversible-action
    style.
  - The run page contains no decision forms; every decision, including
    metadata review, whole-book decisions, final acceptance, and (once a
    preview exists) formatting decisions, opens in the page viewer.
  - A work's accepted versions can be browsed, previewed, formatted, and
    downloaded from the works explorer.
  - The page viewer shows source and output aligned by paragraph for both a run
    in progress and an accepted version, and highlights the location of each
    sheet item under review.

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

- **Status:** `in_progress` (requested by the owner on 2026-11-06; Pi POC
  implementation started at the owner's direction on 2026-11-12)
- **Owner:** `cli1980`
- **Priority and milestone assignment:** not yet decided.
- **Outcome:** Users can configure the studio to use the current Codex App Server
  or another supported agent harness and inference endpoints at server startup.
  Users can choose the most appropriate supported model when starting a
  workflow, while retaining the same workflows, skills, and review interfaces.
  Adding a provider does not require rewriting the workflow engine.
- **Startup-only profile** (owner decision, 2026-11-12): the server loads one
  execution profile at startup and uses it for all execution during that server
  lifetime. There is no dynamic profile switching, configuration hot reload,
  or per-run profile selection. Changing the active profile requires restarting
  the server. This replaces the earlier saved-boundary switching requirement.
- **Workflow model choice** (owner clarification, 2026-11-12): inference
  endpoints and their configuration belong to the startup profile, but the
  user chooses a compatible model when starting a workflow. Model selection
  does not change the active profile or edit endpoint configuration. The
  selected model and its configured endpoint are recorded for the run; model
  changes while the server is running are out of scope. Continuation after a
  server restart follows the policy below.
- **Continuation after profile changes** (owner decision, 2026-11-12): after
  the server restarts with a different profile, unfinished runs continue at
  the agent-operation level from durable workflow state under the new profile.
  Do not restart the workflow or redo completed agent operations. Start a fresh
  harness session when the previous session is incompatible; conversation
  transfer and continuation of an in-flight tool call are not required.
  Preserve pending gates and receipts, completed outputs, and approvals.
  Validate the effective model and endpoint against the new profile before
  execution and record the effective execution identity for each new attempt.
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
  - Introduce named execution profiles defining a harness, configured inference
    endpoints, available models and defaults, and relevant options. Load the
    active profile once at server startup; CLI invocations load the same
    configuration when they start. Retain Codex App Server as one supported
    adapter.
  - Consolidate an optional user JSON with the project profile at startup.
    The project owns harness/execution policy; the user may define endpoints,
    models, and the default model. Merge endpoints by name and models by key,
    with complete user entries replacing matching project entries. Validate
    the merged configuration and preserve startup-only snapshot semantics.
  - Let users select a model for a new workflow in both the CLI and studio,
    from the models supported by the active profile and applicable to that
    workflow. Resolve the choice to its configured endpoint without requiring
    users to edit endpoint settings or workflow templates. Distinguish models
    with the same name on different endpoints.
  - Declare and validate capabilities, including tools, workspace access,
    structured output, session resume, and cancellation. An incompatible
    profile must explain the missing capability before execution starts.
  - Preserve artifacts, human decisions, and completed work during interruption,
    retry, and recovery, including agent-level continuation after restarting
    the server with a different profile. Recover the pending agent operation
    from saved state, using a fresh session when needed. Recovery must not
    bypass a gate or replay an approved operation. Provider-specific session
    identities must not be resumed under an incompatible profile; incompatible
    execution choices fail clearly without discarding saved progress.
  - Keep credentials in server-side configuration or secret references.
    Record the effective harness, endpoint identity, model, and configuration
    revision per execution attempt so work remains attributable; exclude secret
    values from events and exported records.
- **Acceptance criteria:**
  - The existing Codex App Server and at least one alternative harness can
    execute the same workflow through the common runtime contract.
  - At least one harness can use two supported inference endpoints selected
    through profile configuration, without engine or workflow-template changes.
    Different workflow runs may use different models from the loaded profile;
    this is model selection, not dynamic profile switching.
  - The active profile stays fixed for the server lifetime; editing its
    configuration does not change running or subsequent turns until the server
    restarts. No API or GUI control dynamically switches profiles.
  - Users can start workflows with different compatible models through the CLI
    and studio without restarting the server or editing the profile. Each run
    records the selected model and endpoint; incompatible choices are refused
    with an explanation before execution starts.
  - Retry and recovery under the same effective profile preserve artifacts and
    approvals, including recovery through a fresh harness session.
  - After restarting the server with a different compatible profile, an
    unfinished run continues its pending agent operation without restarting
    the workflow or redoing completed operations. Pending human gates and
    receipts remain valid; a fresh harness session receives the saved context,
    and recovery neither bypasses gates nor applies an approved operation twice.
  - The CLI and studio expose the effective execution profile consistently;
    the chapter viewer and human gate behavior remain the same across profiles.
  - Shared adapter tests cover structured results, tool/workspace requirements,
    event and error handling, cancellation, retry, and state recovery.
    Integration checks exercise each supported combination; unsupported
    combinations fail with an actionable explanation.
- **POC feature brief — Pi Evaluation** (Pi selected by the owner on
  2026-11-06; tryout endpoint and model selected on 2026-11-12):
  - **PR #5 review fixes (2026-11-16):** restart now resolves the default model
    and all carried agent-model choices against the startup profile before
    cancelling the original run, for both ordinary and derived restart paths.
    Missing keys, changed workflow permissions and incompatible defaults leave
    the original state/index unchanged; restoring a compatible profile permits
    restart. Works and Workflows share compatible-model selection and profile
    notices; creation waits for the catalog and requires a compatible choice
    when configured. Workflow changes cannot submit an incompatible prior
    choice; no-profile operation still omits the model key.
    Verified 99 workflow/profile/API tests, both model-selection browser checks
    and frontend typecheck/build. Browser checks use isolated fixtures with no
    inference calls. No live runs or unrelated formatter checkout were changed.
  - **Status:** `in_progress`; implemented locally and uncommitted, automated
    local checks and one live private-endpoint translation case passed; human quality
    review and remaining recovery/isolation evidence pending.
  - **Owner:** `cli1980`
  - **Branch:** `feature/runtime-extensibility-poc`
  - **Implementation progress (2026-11-12, local and uncommitted):**
    - `workflow/src/execution.py` snapshots startup profiles, endpoints,
      allowlisted model choices, and credential environment references for the
      CLI and studio. Model keys are pinned at workflow creation; no hot reload
      or per-run profile switching is exposed.
    - `workflow/src/pi_runtime.py` runs pinned Pi `0.73.1` over RPC with isolated
      runtime configuration and a stage-schema result tool. Every turn starts a
      fresh session from durable context. The Python engine still validates the
      result, artifacts, gates, and receipts before advancing.
    - The studio offers compatible model choices and reports execution identity.
      Profile changes on server restart invalidate old session identity without
      resetting completed work or human gates. Each execution attempt records
      the effective profile revision, harness, model, and endpoint; accepted
      translation run records retain that provenance.
    - Pi and profiled Codex expose normalized lifecycle, tool-boundary, and
      available usage events. Raw Pi provider streams/stderr are not persisted;
      configured credentials are redacted from returned events, results, and
      errors. Tool execution is trusted local execution, not an OS sandbox.
    - Installed Pi `0.73.1` passed a native-Windows RPC check against a local fake
      inference server, including the full model ID and schema-backed result
      extension. This is protocol evidence, not live private-endpoint inference or
      literary-quality evidence.
    - Automated checks: 81 workflow/profile/transport/API tests passed; the
      studio case/browser suite passed 5 tests with the live Codex case skipped.
      Frontend typecheck and production build passed. Recovery tests cover
      preserved completed outputs, pending review identity and receipt,
      incompatible-session reset, failure/retry, and successful receipt
      consumption without repeating a human authorization.
    - An unauthenticated model-list request to the selected endpoint returned
      HTTP 401. The local endpoint's credential variable was not present in the development
      process environment; no other provider credential was substituted.
      The subsequent live evaluation used the already-running Pi server's
      credential without exposing or copying it into the development terminal.
    - **Live Pi translation evidence (2026-11-12):** reused
      `beijing-night-translation-gui-001` on the evaluation server at port 8767.
      Run `da6626a3-bfe6-4417-8960-bd0e7a1c7af7`, work `work-43fa92`, completed
      preparation, samples, brief approval, chapter reviews, consistency,
      acceptance, and export in 10 Pi turns (about 17 minutes), using the
      selected private endpoint and exact model ID. Two prepared units were
      exported; chapter/continuity hashes match their accepted artifacts and
      the export manifest. The eight case steps passed.
    - The first attempt found a browser-runner timing race: the gate frame
      appeared before the sample-poll body. The runner now waits for that body.
      The same run resumed at its existing sample gate; preparation and the
      metadata decision were not repeated. This is browser-driver continuation,
      not server-crash or cross-profile recovery evidence.
    - Seven gate receipts and final acceptance are explicitly attributed to
      `delegated-automation`, not a human. The browser's decision requests were
      intercepted into the shared local engine for that attribution, followed
      by real server worker resumption; therefore this does not establish
      end-to-end browser decision-API transport coverage. The local report is
      `.workflow-runs/pi-translation-browser-report.json`; artifacts are under
      `.workflow-runs/pi-poc/runs/da6626a3-bfe6-4417-8960-bd0e7a1c7af7/export`.
      Human literary-quality review, live approved/rejected consistency-fix
      application, live server/profile-change recovery, and the second endpoint
      remain outstanding. POC and milestone remain `in_progress`.
    - **Shared-runtime refactor (local and uncommitted):** both adapters compose
      `workflow/src/stdio.py` for subprocess/JSONL transport, deadlines,
      malformed-output/EOF handling, stderr draining, and cleanup. Harness
      handshakes, session commands, result extraction, and graceful
      interruption remain adapter-owned. Codex now emits normalized events
      directly, like Pi; profile code no longer translates Codex notifications.
      `workflow/src/harnesses.py` registers factories and configuration
      requirements. Profiles resolve their registration once at startup and
      create adapters without harness-specific construction branches.
      Constructors remain free of subprocess side effects.
    - Refactor checks: 85 workflow/profile/transport/API tests passed, including
      registered-factory extensibility and startup binding, constructor safety,
      EOF/malformed JSON, deadline/callback cleanup, protocol interleaving,
      event normalization, credential redaction, and durable recovery.
      Studio browser/case checks also passed 5 tests with the separate live
      Codex unittest skipped. The reusable profile-bound launcher is
      `python -m studio.tests.run_translation_case`.
    - **Post-refactor live verification:** the same existing
      `beijing-night-translation-gui-001` case passed all eight steps separately
      for Codex and Pi. Codex run `7057c015-0982-4462-b17f-f0ef64b8bdd3`
      used installed Codex CLI `0.163.0` and model `gpt-6-astra`; Pi run
      `763a27f5-3a59-4561-a58c-d66faa05549c` used pinned Pi `0.73.1` and
      the endpoint-qualified model from the local profile. Each completed
      10 agent turns, exported two units, and passed chapter/continuity hash
      checks. Both reports' engine identities match the refactored source.
      Canonical lifecycle, tool-boundary, and usage events were recorded by
      both adapters.
    - Each new live run records seven `delegated-automation` gate receipts and
      delegated final acceptance. The browser-decision interception limitation
      described above still applies; neither run is a human literary-quality
      review. Both consistency reviews closed with `confirm consistency`, not
      a live approved/rejected-fix application scenario. The models/providers
      differ, so these runs demonstrate functional compatibility rather than a
      controlled harness-quality or performance comparison.
      Local reports: `.workflow-runs/refactor-codex-translation-report.json`
      and `.workflow-runs/refactor-pi-translation-report.json`.
    - **Per-run token usage:** the run inspector and chapter viewer now show
      input/output/cached-input/total tokens and reporting-turn coverage.
      Run detail API/CLI reads aggregate persisted usage without changing
      artifacts or adding polling; failed/retried attempts remain included.
      The runs list is unchanged. Cached input is a subset of input, not an
      extra term in total. Missing usage stays unavailable and incomplete
      counters are explicitly partial.
    - Accounting investigation found that Codex `last` is the most recent
      inference request, not the cumulative turn. New normalized events use
      thread-total deltas and versioned accounting; previous normalized Codex
      records are flagged as potentially undercounted. Historical raw Codex
      cumulative telemetry is supported with resume/duplicate handling.
      Existing events and accepted outputs were not rewritten; these figures
      are reported token counts, not billing or controlled cost comparisons.
      Verification: 92 workflow/accounting/transport/API tests passed, including
      resumed-thread baselines, repeated telemetry, shrinking per-request
      counts, retries, missing usage, legacy partial flags, read-only
      aggregation, and exclusion from list responses. Studio/browser checks
      passed 5 tests with the live Codex unittest skipped; the run-page check
      verifies displayed totals and change-feed updates without polling.
      Frontend typecheck and production build passed.
    - **Live token-panel check after restart:** fresh Pi run
      `cb5b29be-3fb9-4287-b469-3254ad9796e0` completed and exported with
      11 reporting turns: 6,688,662 input, 76,417 output, 5,776,385 cached input
      (included in input), and 6,765,079 total tokens. Both run inspector and
      chapter viewer displayed the final values without partial warnings;
      counts reconcile exactly with persisted usage events, and exported
      chapter/continuity hashes passed. Usage was also visible during execution.
      The browser driver hit a stale gate; the same saved run continued through
      delegated local-engine decisions, with a transient HTTP read failure
      during continuation. This is a successful token-display/reconciliation
      check, not a clean uninterrupted browser-case pass. Original failure and
      final verification are preserved in
      `.workflow-runs/pi-token-usage-live-report.json`; final panel screenshot:
      `.workflow-runs/pi-token-usage-final.png`. Decisions remain delegated, not
      human literary-quality review.
    - **Codex matching-model tryout:** the installed App Server catalog exposes
      `gpt-6-sol`, the native advertised-model counterpart to Pi's
      endpoint-qualified model ID from the local profile. An isolated profile/server
      on port 8769 completed all eight Beijing-night case steps in run
      `fa34e2a1-3a74-4f40-a26d-5de6d1d7faae`, with 10 agent turns and
      verified exported chapter/continuity hashes. Native session metadata
      confirms `gpt-6-sol` without fallback; global Codex configuration and
      existing servers were not changed. Seven gate receipts and final
      acceptance remain `delegated-automation`.
    - Codex reported 9,117,907 input, 82,087 output, 8,690,816 cached input
      (included in input), and 9,199,994 total tokens, with complete reporting
      from all 10 turns. These values reconcile with normalized events and
      the final cumulative native token counters of all five Codex threads.
      The run viewer displayed the same totals. Evidence:
      `.workflow-runs/codex-sol-translation-report.json` and
      `.workflow-runs/codex-sol-token-usage.png`.
    - For the clean 10-turn Pi case
      `763a27f5-3a59-4561-a58c-d66faa05549c`, the corresponding figures are
      7,515,818 input, 75,899 output, 6,690,345 cached input, and 7,591,717
      total tokens. Pi reported about 17.5% fewer total tokens in this pair,
      but Codex reported more cached input. This is not a billing comparison
      or evidence of inherent harness efficiency: providers/endpoints, exact
      served model revisions, session strategies, and generated decisions
      were not controlled. Both use the same advertised model name and case,
      not a verified identical model deployment. Human quality review remains
      outstanding.
    - **User profile JSON consolidation:** studio and CLI accept an explicit
      `--user-execution-profile` alongside the project `--execution-profile`.
      User endpoints merge by name and models by key, replacing complete
      matching entries and retaining other project entries. Users may override
      the default model, but not the harness, command, timeout, trust policy,
      or profile name. Thin project policy files may obtain all model/endpoint
      choices from the user file. Relative command paths remain project-relative.
      Both inputs and the final profile are validated; duplicate keys, partial
      endpoint replacements, missing explicit files, and invalid references
      fail without fallback. Files and credentials are snapshotted once, and
      the effective merged configuration determines the provenance revision.
    - User-profile verification: 103 workflow/profile/accounting/transport/API
      tests passed; 5 studio/browser checks passed with the separate live
      Codex unittest skipped. Tests cover extension/replacement, restricted
      fields, secret-reference handling, snapshots, revisions, project-relative
      paths, CLI creation hints, and merged startup model selection without
      inference. `workflow/profiles/user.example.json` documents the shape;
      root `execution-profile.user.json` is gitignored and locally initialized
      with the existing private endpoint/model and environment-variable reference.
    - **Local-only inference choices:** the checked-in Pi evaluation JSON now
      contains harness/command/timeout/trust policy only. The private endpoint,
      model list, and default model live solely in the gitignored
      `execution-profile.user.json`; both profile options are required for
      startup. This relocation preserves the effective merged configuration
      and its revision hash. Twelve focused profile/startup tests passed,
      including validation of the shipped policy-only profile with a user file.
    - **Internal-endpoint residue audit:** runtime code is provider-neutral;
      remaining private URL, credential-variable, and model-binding literals
      were removed from reusable tests and repository documentation. Tests
      use a reserved example-domain endpoint and a synthetic fully qualified
      model ID, retaining coverage for exact identifier preservation. A scan
      of all non-ignored repository text files found no remaining internal
      inference identifiers. Ignored local configuration and original local
      evaluation evidence remain unchanged. All 104 workflow/profile/usage/
      transport/API regression tests passed after the fixture cleanup.
  - **Question:** can Pi execute the existing literary-translation workflow
    through the shared runtime boundary, using the selected inference service,
    without weakening workflow validation, human gates, or recovery?
  - **Tryout configuration:**
    - Harness: Pi, pinned to `@mariozechner/pi-coding-agent@0.73.1`.
    - Inference endpoint and initial model: defined in the gitignored local
      execution profile; exact values remain in local evaluation records.
      Preserve the full configured model identifier; do not infer a different
      provider or strip its prefix.
    - The endpoint and available model are owner-supplied selections, not
      evidence of successful access or Pi compatibility. Authentication method,
      supported API protocol, tool calling, streaming, and model capabilities
      must be verified. Keep credentials in local/server-side secret references,
      never in the brief, committed configuration, traces, or exports.
  - **User flow:** start the server with the Pi evaluation profile; start a
    literary-translation workflow on an existing work and choose the configured
    model; review its normal gates and accept/export through the existing UI.
    The CLI uses the same configuration and model identity. The startup profile
    is immutable during the server lifetime; model selection at run creation
    does not change the profile.
  - **Implementation boundary:** keep Codex available alongside a small Pi
    adapter; put protocol and endpoint specifics behind the runtime boundary,
    not in translation prompts, domain validation, or review components. Use
    the current pinned skill bundles and durable workflow context.
  - Build a small `PiRuntime` adapter using Pi's subprocess
    [RPC interface](https://pi.dev/docs/latest/rpc), alongside `CodexRuntime`.
    Pin the tested Pi version and verify native Windows operation, workspace
    and skill loading, session recovery, events, and cancellation. Verify the
    execution-isolation boundary rather than assuming Pi supplies Codex's
    filesystem and tool-network restrictions.
  - Prove the structured result contract with a schema-validated workflow-result
    tool or equivalent extension. Pi's JSON event stream alone does not
    constrain the final model response; the engine's validation remains
    authoritative.
  - Compare Codex and Pi using the same model and endpoint where both support
    them, recording any differences that prevent a controlled comparison.
    Do not substitute another model silently if the selected combination is
    unavailable.
  - Run a small literary-translation case through preparation, chapter review,
    whole-book consistency with approved and rejected fixes, and final
    acceptance/export. Exercise interruption, retry, and recovery through a
    fresh harness session under the same effective profile. Also restart the
    server with a different compatible profile and demonstrate agent-level
    continuation of an unfinished run with its saved progress and approvals.
  - **Verification and evidence:**
    - Adapter tests cover structured results, interleaved events, provider
      errors, malformed output, timeout, cancellation, and process cleanup.
      Capability checks reject unsupported combinations before agent execution.
    - A live small-manuscript run covers preparation, chapter reviews,
      whole-book consistency, and final acceptance/export with the selected
      endpoint/model. Exercise approved and rejected consistency fixes; if the
      live model proposes none, record that coverage gap rather than claim it
      was exercised. Deterministic tests separately verify exact-fix enforcement.
    - Recovery checks retain artifact hashes, completed operations, pending
      gates, and receipt identities across interruption, retry, fresh sessions,
      and a server restart with a different compatible profile. No completed
      operation is redone and no authorized change is applied twice.
    - CLI and browser checks show the same effective harness, endpoint, and
      model. Secret values are absent from client responses, events, and exports.
    - Record the pinned Pi version, non-secret effective configuration, test/run
      identities, correctness, model-quality observations, latency, usage where
      available, and limitations. Distinguish test-double evidence, live-model
      results, and human quality review.
  - **Exit criteria:** the selected Pi/endpoint/model combination completes the
    workflow through the shared contract; recovery preserves artifacts and
    approvals; gates and exact-fix validation cannot be bypassed; malformed or
    unsupported execution fails clearly. Report failures and missing coverage
    explicitly before deciding whether to adopt Pi.
  - **POC boundary:** this initial evaluation names one endpoint and one model.
    The broader milestone's two-endpoint demonstration remains outstanding
    until a second endpoint is selected and tested; this POC alone does not
    close that milestone. Live profile switching, mid-run model selection,
    conversation transfer, and unrelated workflow/UI redesign are excluded.
  - **Status boundary:** the Pi adapter has passed functional live evaluation
    against the selected private endpoint, but is not adopted as the default
    harness. Isolation, recovery, and human quality-review gaps remain as
    recorded above. See `studio/README.md` for local setup and trust limits.
- **Open design choices:** additional inference endpoints and models beyond the
  selected Pi tryout, authentication and API compatibility for that endpoint,
  concrete adapter interfaces, profile storage and startup selection mechanism,
  model discovery and workflow model-selection UI, whether per-agent model
  overrides are exposed, and the capability matrix. Dynamic profile switching
  is out of scope; agent-level continuation after a server restart with a
  different compatible profile is required. No implementation schedule has
  been selected.

### Deterministic DOCX formatting in the studio

- **Status:** `in_progress` (requested by the owner on 2026-11-08 after a
  feasibility review; prioritized on 2026-11-13; proposal-only skill conversion
  implemented; embedded editing proposal-review form and bounded editable-DOCX
  production/delivery integrated; full vendor-ready intake, translation
  composition and rendered-page/print production remain pending)
- **Owner:** `cli1980`
- **Priority:** highest current priority (owner decision, 2026-11-13);
  takes precedence over other planned or unfinished work.
- **Branch:** `feature/deterministic-docx-formatting`.
- **Milestone assignment:** not yet decided.
- **Analysis (2026-11-13):**
  [requirement and implementation gaps](https://github.com/cli1980/book-formatter/blob/237be7d034b57f7a77fd0b7e9cd0ecb03a27d05c/docs/deterministic-docx-gap-analysis.md)
  traced across the engine, document adapters, service, API, and UI. Fifteen
  existing formatting/builder/API tests pass. Native human page review,
  agent-free lifecycle, rendered-layout QA, and renderer serialization remain
  baseline gaps; no new browser or real-renderer verification is claimed.
  Its fully-agent-free/standalone framing is superseded by the revised direction
  below; production, not necessarily design, is agent-free.
- **Revised direction (owner, 2026-11-13):** three components: convert the
  original formatting skill to interior design; provide a design-intake GUI
  combining its proposed form with a print-vendor profile (IngramSpark first);
  and generate the document deterministically from the approved design.
  Formatting is embedded in editing and translation and always consumes
  manuscript-preparation results, not another formatting result.
- **Skill independence (owner clarification, 2026-11-14):** `interior-design`
  can run standalone against verified preparation or be invoked as a reusable
  component. Its proposal carries no workflow/run IDs. Embedded formatting
  and zero-pass editing routes remain orchestration rules, not skill requirements
  (IDP-R13/IDP-C08 in the design).
- **High-level design:** [interior design and deterministic production](https://github.com/cli1980/book-formatter/blob/237be7d034b57f7a77fd0b7e9cd0ecb03a27d05c/docs/interior-design-and-production.md)
  (draft). Detailed component contracts, cross-component flow, vendor-source
  findings, lifecycle choices, and open questions live there. Its stable
  `IDP-R` requirement IDs distinguish owner-confirmed direction from the open
  `IDP-D` decisions; implementation and validation must be traced explicitly.
- **Skill reference (owner supplied, 2026-11-13):**
  [author-brief mapping and proposed refinements](https://github.com/cli1980/book-formatter/blob/237be7d034b57f7a77fd0b7e9cd0ecb03a27d05c/docs/interior-design-skill-brief-mapping.md)
  captures the reference's author intent, reading, series/preferences, production
  targets, and semantic text-role implications. This is design input, not approval
  of every questionnaire field, service, or new renderer capability.
- **Outcome:** a prepared manuscript is designed, reviewed, and formatted inside
  its parent workflow. AI can propose the interior design; the user approves
  the effective design and rendered pages; production and rebuilds are native.
- **Semantic roles (owner clarification, 2026-11-13):** preparation skill and
  workflow require annotation/modification support, and downstream workflows,
  including translation, must preserve/transfer roles. See
  [upstream ownership and role hand-off](https://github.com/cli1980/book-formatter/blob/237be7d034b57f7a77fd0b7e9cd0ecb03a27d05c/docs/semantic-role-handoff.md)
  and IDP-R10 through IDP-R12. These contracts/tools are not implemented by the
  current proposal-only schema or its byte-range validator.
- **Skill implementation (2026-11-13):** converted `format-manuscript` to
  [interior-design](plugins/manuscript-studio/skills/interior-design/SKILL.md),
  with a closed
  [proposal schema](plugins/manuscript-studio/skills/interior-design/schemas/interior-design-proposal.schema.json),
  synthetic example, and read-only validator. Fourteen proposal tests pass;
  installer/listing checks report 31 passes and three Windows symlink skips;
  15 existing formatter/builder/API checks pass after decoupling the legacy
  generator. These are contract/functional checks, not live-model design-quality,
  new browser-flow, or real-renderer evidence at that checkpoint. Native document
  production remains unimplemented, and no production profile or finalization
  decision is approved; the later proposal-review slice is recorded below.
- **Standalone real-manuscript check (2026-11-14):** direct execution with the
  owner's unchanged short prompt produced a source-bound proposal after preparing
  and reading a complete 69,663-word English novel (22 units). Shape and local
  source validation pass; stale metadata and tampered-span checks reject changes.
  Original/prepared inputs remain unchanged after design. Local, ignored evidence:
  `.workflow-runs/standalone-interior-memory-xfbsy9bu/test-report.md`.
  This is not a blind evaluation, human design approval, or renderer verification.
  It exposed missing canonical role/text-anchor/transfer contracts, inline versus
  block style application and special-form layout controls, edition-purpose
  uncertainty, and conflicting metadata-prefill guidance. These remain gaps;
  no schema/runtime changes were made during the check.
- **Embedded proposal-review slice (2026-11-15):** literary editing offers
  zero or more accepted passes followed by **Review manuscript** and explicit
  manuscript approval. Approval freezes content and metadata and automatically
  starts the final formatting phase with `interior-design` and a native editable
  human form. IDP-C11/IDP-R15 supersede the earlier Format/Interior-design
  shortcut and its display-label override; no early command remains.
  Saves validate and create new revisions/gate IDs; proposal approval
  binds the saved JSON separately from its `proposed` status. Exact accepted edits
  require separate output preparation; source text/metadata remain frozen.
  Focused engine/API tests cover approval ordering, frozen input before the agent,
  zero-pass and edited-output handoff, stale approvals, reopening and design-only
  restarts, human edits, revision feedback, and blocking before production. The
  full workflow/API suite passes (77 tests); Chromium verifies the removed early
  action, explicit manuscript approval and automatic transition, then form
  saving/approval on desktop and 390 px mobile against a scripted skill.
  Targeted CLI checks use the manuscript-approval notice rather than claiming
  final publication. A
  single-snapshot run-detail read fixes the gate-arrival race exposed by that
  check. Typecheck/build pass; no new live-model run or document rendering is
  claimed. See IDP-R14/IDP-C10 and the implemented slice in the
  [design](https://github.com/cli1980/book-formatter/blob/237be7d034b57f7a77fd0b7e9cd0ecb03a27d05c/docs/interior-design-and-production.md).
  Vendor-aware effective-spec compilation, translation composition, production
  and page review remain pending. The separate editing content-only finish is removed; manuscript
  approval is not final publication. Design restarts preserve the approved basis;
  reopening manuscript approval invalidates downstream decisions. IDP-D01 is
  partly resolved and IDP-D02 is resolved for editing.
- **Legacy-route removal (owner direction, 2026-11-15):** IDP-R16/IDP-C12 remove
  the old formatter skill, engine/template, bundled agent adapter and work/run/
  CLI/E2E launch paths. The remaining public path is the parent's final
  formatting phase, not the old six-item `format_spec` review. Existing old runs
  are read-only history with their recorded status/decisions/artifacts preserved;
  they cannot execute or block a new supported workflow. New metadata/workflow
  catalogs omit the retired workflow; historical publications are unchanged.
  Verified: 73 workflow/API tests, 30 preparation tests, 25 preparation-
  evaluation tests and 31 installer checks pass (three platform skips). The
  browser test now starts from the actual work-page workflow launcher and reaches
  the editable form after manuscript approval. Read-only live browser checks
  also verify the user's old sheet and both removed launchers; all three live
  run revisions/state hashes remain unchanged after reloading Studio.
  Typecheck/build and LF/whitespace checks pass. No live model or document
  renderer ran for these checks.
  Translation composition and producer/page-review integration remain pending.
- **IngramSpark profile selection (2026-11-15, IDP-R17/C13/C14):** added one
  [sourced vendor profile](plugins/manuscript-studio/skills/interior-design/profiles/ingramspark.json)
  with paperback/hardcover variants. Choosing IngramSpark loads the variant for
  the selected binding automatically. The proposal carries its exact data,
  source/version and canonical hash; mismatched/substituted profiles or targets
  are rejected. Selection is available at manuscript approval and in the native
  review form. Retargeting requests a revised proposal with the saved draft,
  preserving approved manuscript content and compatible saved choices for review.
  Reviewed custom-trim coverage, safety and bleed warnings are advisory, not
  invented hard rules or complete vendor product support. No renderer,
  PDF/X preflight, product-availability verification or page approval is added.
  Seventeen proposal tests, two focused workflow checks and the real
  work-page-to-design browser check pass; browser coverage includes automatic
  variant loading, both bindings, retargeting and retained font/gutter edits.
  Typecheck/build and installer checks pass (31 checks, three platform skips).
  All 75 workflow/API regression tests pass. A cancelled/outdated run is
  presented read-only without hydrating a newer form against its pinned older
  schema; its records are not migrated or executed.
- **Purpose before design authoring (2026-11-15, IDP-R18/C15/C16):** the
  formatting-entry dropdown defaults to **Print-ready** (renamed from
  reader-facing), alongside Submission and Editorial review. It appears at the
  existing manuscript-approval transition, not an early formatting shortcut.
  The host supplies the selected purpose and rationale guidance before the
  first agent call, and checks that the proposal retains the choice. Later
  purpose changes originally requested a revised proposal through target controls;
  IDP-C17 supersedes that interaction with read-only proposal fields and entry-only selection.
  Print-ready is intent, not a compliance receipt. Verified: 76 workflow/API
  tests, 17 proposal tests, typecheck/build and the native browser flow pass.
  Browser coverage checks the default, a non-default purpose before authoring,
  its proposal binding, a later purpose revision and one purpose dropdown
  rather than a duplicate editable specification field. The browser uses a
  scripted agent; no live-model quality or production validation is implied.
- **Read-only proposal entry choices (2026-11-15, IDP-C17):** removed the
  duplicate purpose/vendor/binding selectors and target-changing action from
  proposal review. The generic production-target editor also renders target ID,
  vendor ID, binding and profile references as read-only outputs, without
  nullable-field clear/set controls. Server checks reject changes through
  advanced JSON/API saves; print target vendor/binding must match the entry
  selection. Reopen manuscript approval to choose a new target; design
  revisions retain the original choices. Layout and typography stay editable.
  Verified: all 76 workflow/API tests, frontend typecheck/build and the native
  browser flow pass. Coverage checks absent duplicate selectors, nested
  read-only outputs, rejected target/profile edits and continued font/gutter
  editing on desktop/mobile. Browser authoring uses a scripted agent.
- **Design-review cleanup (2026-11-15, IDP-C18/C19):** removed technical
  capability/vendor/PDF approval questions at their source, including the rule
  requiring a blocking vendor question. Only genuine author/design decisions
  remain; no acknowledgement is needed when questions are empty. Geometry now
  shows mm with live inch equivalents, and the approval heading is **Approve
  manuscript for formatting**. Removed preferred page count from the proposal
  contract and hid internal IDs, profile references, hashes and raw JSON/debug
  views from the normal UI; validation metadata remains internal and fixed.
  Production/preflight remain pending, not passed by this cleanup. Verified:
  77 workflow/API tests, 18 proposal tests, typecheck/build and the native
  browser flow pass. Coverage includes approval without technical
  acknowledgements, rejected technical-question kinds/page-count preference,
  live inch conversion, the new heading, hidden internal fields and mobile
  layout. Browser authoring is scripted; no live-model or production test ran.
- **Proposal-to-DOCX assessment (2026-11-15, IDP-C20):** completed a
  [current field-level gap analysis](https://github.com/cli1980/book-formatter/blob/237be7d034b57f7a77fd0b7e9cd0ecb03a27d05c/docs/proposal-to-docx-gap-analysis.md)
  before implementation. It distinguishes compiler/capability approval,
  missing DOCX behavior, underspecified role/page/font semantics and native
  build/QA/page-review delivery. A temporary synthetic DOCX probe confirms that
  even the current example loses independent margins/gutter, outside folios and
  heading leading through the old flat builder interface. No real manuscript,
  renderer/PDF, production workflow or application behavior was changed.
  All three retained adapter tests pass (LibreOffice execution is mocked);
  assessment links, LF and whitespace checks pass. Initial delivery subset
  and the proposed order remain recommendations.
- **Formattor package evaluation (2026-11-15, IDP-R19/C21):** owner-confirmed
  structure is proposal intake, an
  implementation-independent format engine, and format implementations with
  DOCX default and potential InDesign. The
  [design evaluation](https://github.com/cli1980/book-formatter/blob/237be7d034b57f7a77fd0b7e9cd0ecb03a27d05c/docs/formattor-package-design.md) maps the gaps
  to component owners, proposes neutral contracts/capability negotiation,
  separates native composition from orchestration, and identifies migration
  of skill-local validation/profile authority without breaking standalone use.
  Word/LibreOffice remain DOCX render strategies, not peer format implementations.
  This is documentation only: no package, code migration, InDesign support or
  production capability is implemented. Output/subset/semantic decisions remain
  explicit pending work. Design links, requirement/decision uniqueness, LF and
  whitespace checks pass; application tests were not rerun for documentation-only changes.
- **Standalone tool and document consolidation (2026-11-15, IDP-C22/C23):**
  after comparing inside-workflow placement with standalone use, the owner
  selected an installable tool with Python API and CLI under `tools/formattor`.
  This supersedes C21's initial `workflow/src/formattor` location without
  changing its three-part architecture or default DOCX implementation.
  All seven related design/gap documents now live under the tool's `docs/`,
  indexed by [the tool README](https://github.com/cli1980/book-formatter/blob/237be7d034b57f7a77fd0b7e9cd0ecb03a27d05c/README.md); instructions and
  cross-references point to the new canonical location. IDP-D09 is resolved.
  Only documentation/project directories are present: no executable package,
  CLI, dependency installation or generator behavior has been implemented.
  Verified all seven relocations and 60 relative document links; no stale
  incoming references remain. LF and whitespace checks pass. No application
  tests or server restart were needed for this documentation-only change.
- **Formatter repository extraction (2026-11-15, IDP-C24):** the owner selected
  [cli1980/book-formatter](https://github.com/cli1980/book-formatter) as the
  standalone repository. The existing README and all seven design/gap documents
  were migrated and published at `237be7d`; `tools/formattor` is now a pinned
  Git submodule instead of parent-tracked files. The tool preserves the source's
  applicable MIT notice and has its own LF/contributor instructions.
  Cross-repository document links use pinned commits, with provenance to host
  baseline `ce7a55e`; host-source permalinks require that parent commit to be
  published. Parent changes remain local. No skill/runtime code, generator
  implementation, package installation or production behavior was moved/added.
  Verified a fresh clone from the published formatter repository, all 27
  internal links without a parent checkout, 33 source references against the
  pinned host commit, and 12 incoming links against the published child commit.
  The parent gitlink is mode 160000; the child is clean. Whitespace checks pass.
- **Standalone language/design research (2026-11-15, IDP-C25):** drafted the
  [research report](tools/formattor/docs/standalone-design-and-language-research.md)
  and primary-source register in the formatter working tree. It compares
  Python, TypeScript, Rust and C++, recommends Python conditionally, and maps
  source/style/page/font/print/job gaps to explicit validation gates. A
  reproducible construction/parser probe passes using installed libraries;
  no real renderer, PDF/X check or performance benchmark ran. Language remains
  open (IDP-D10); earlier Python-API wording is not treated as owner approval.
  Research changes are uncommitted/unpublished; the parent gitlink remains
  pinned to the published migration commit.
- **Paragraph-only design roles (2026-11-15, IDP-C26):** refactored the host
  skill/schema/helper to proposal contract `/2`. Roles reference whole CommonMark
  paragraph/heading blocks by chapter ID/hash and catalog index/hash; inline
  formatting remains the original Markdown markers. Added a standalone catalog
  command, exact-identity/bounds/duplicate checks and workflow authoring guidance.
  Empty role lists use ordinary body/heading defaults. Reading excerpts remain
  byte-bound evidence, not formatting assignments. Updated the review wording
  and standalone design/research records; upstream canonical annotations,
  document generation and language selection remain pending. Old `/1` proposals
  must be regenerated, not silently converted. Verified 23 proposal tests and
  72 workflow/API cases, including a targeted rerun after correcting a new test's
  front-matter assumption. Frontend build, 85 relative links, LF and whitespace
  checks pass. No existing run/proposal has been rewritten or server restarted;
  no formatter production or renderer/PDF verification is implied.
- **Early formatter POC scope (2026-11-15, IDP-C27):** leave a saved minimally
  formatted intermediate DOCX outside the early POC. The intended route is
  verified Markdown + paragraph roles + approved design directly to DOCX, with
  parsing and construction separated in code. Revisit an intermediate only if
  later evidence warrants it, not as a committed follow-on feature. Scope/docs
  only; no producer, new approval gate or deliverable/readiness promise added.
- **DOCX widow/orphan policy (2026-11-15, IDP-C28):** accepted explicit lowering
  `bool(widow_lines or orphan_lines)`, not exact DOCX line thresholds. Both zero
  disables the combined control; either nonzero enables it. The proposal accepts
  non-negative integers including zero, without an artificial four-line cap.
  Updated skill/contract/schema and review guidance; native plans must record the
  resolved boolean/policy. Other unsupported features still need diagnostics.
  Verified 24 proposal tests, a design-review save regression (zero and mixed
  values), six serialized DOCX flag cases, and the frontend build. No generator,
  renderer or InDesign behavior has been implemented or certified.
- **DOCX-only early POC (2026-11-15, IDP-C29):** defer PDF export and all
  renderer-driven pagination, including Word/LibreOffice automation,
  pagination-dependent field/TOC updates, page-count convergence, page images,
  rendered-page checks/review and print preflight. The POC constructs editable
  DOCX and checks input identity, content/structure and native settings; page
  geometry/styles/sections/field definitions do not certify rendered behavior.
  This is not a publication or print-readiness gate waiver. Scope/docs only;
  no producer implemented and no existing run or artifact changed.
- **Paragraph-based POC content boundary (2026-11-15, IDP-C30):** no images,
  ordered/unordered lists or poetry-specific layout. Use paragraphs and the
  agreed structural headings/source inline formatting. Unsupported constructs
  or declared requirements must fail explicitly with source-located diagnostics,
  not be omitted, flattened or accepted as partial success. Full block/inline
  validation is required; cataloguing a paragraph does not establish support for
  its containers/content. No semantic poetry detector is implied. Scope/docs
  only; producer enforcement and its regression fixtures remain unimplemented.
- **Explicit header/footer contract and DOCX map (2026-11-15, IDP-C31/R21):**
  proposal `/3` replaces coarse furniture switches with document odd/even
  behavior, default and unit-bound override section settings, header/footer
  distances, first-page behavior, all six part variants, independent links,
  paragraph styles/alignment and safe metadata/PAGE/NUMPAGES templates.
  Schema/helper and review controls validate/edit these fields; old `/1` and
  `/2` proposals need regeneration. Added the
  [proposal-to-DOCX map](tools/formattor/docs/proposal-to-docx-map.md), separating
  direct APIs, OOXML extensions, rules, open decisions and deferred behavior.
  Verified 28 proposal tests, 74 workflow/API tests, desktop/mobile browser
  editing/save/approval, the frontend build, and DOCX package construction
  including all six furniture variants, distances, links and page fields.
  Coverage checks account for all 92 design-system schema leaf paths; 91 relative
  links, LF and whitespace checks pass. Browser verification also exposed a
  concurrent metadata-import alias race: serialized that temporary global binding
  and added a regression. No production compiler, field refresh, rendering,
  server restart, commit or publication is implied.
- **First standalone formatter POC started (2026-11-15, IDP-C32):**
  restarted the existing Studio server at `http://127.0.0.1:8765` using the same
  `.workflow-runs/studio-clean-20261114-190430` data root; seven runs remain and
  no workers were active at restart. Implemented the provisional Python
  `book-formatter` distribution/CLI and `book_formatter` API in the child repo.
  Includes independent versioned interchange snapshots, exact preparation/source
  and paragraph bindings, immutable effective plan, explicit plan-hash operation
  authorization, direct DOCX construction and reopen checks before no-overwrite
  publication. Headers/footers, sparse source emphasis, geometry/styles,
  section starts and numbering instructions are in the bounded subset.
  The [POC contract](tools/formattor/docs/poc.md) lists all explicit prototype
  policies and unsupported constructs; policies are not additional owner-approved
  product defaults. Verified 17 standalone tests in the project environment and
  all 17 again after wheel installation into a clean temporary environment,
  with copied fixtures/API/CLI execution outside the checkout. Wheel includes
  all four schemas and the vendor profile; five interchange resources match
  the host byte-for-byte. Source/resource LF, Python parsing, 90 child-document
  relative links and whitespace checks pass. Studio still serves all seven runs.
  Studio production wiring, persistent jobs, final artifact approval, full
  resource-authority migration and all renderer/PDF work remain pending.
  No existing run/proposal was rewritten, user artifact published or commit created.
- **Header/footer content presets (2026-11-15, IDP-C33 / R22):**
  proposal `/4` replaces paragraph `text` with structured `content`, selecting
  book title, chapter name, author, page number, Page X of Y, or a custom
  template. The schema's expansion table is shared by proposal validation,
  review selectors and the standalone formatter; named choices cannot carry a
  conflicting template. None is an explicitly blank, unlinked part. Existing
  styles, alignment, section links and first/even-page settings stay separate.
  The authoring skill/coordinator use the new choices; the exact selection,
  resolved template and text/native-field chunks enter the authorized plan.
  Verified 29 proposal tests, 76 workflow/API tests, all 18 formatter tests from
  a clean wheel installation outside the checkout, and desktop/mobile browser
  preset/custom/None save-and-approval checks. Frontend build, schema/fixture
  parity, all 104 field-map leaves, Python/LF and whitespace checks pass.
  Restarted Studio on its existing configuration with no active workers; all
  eight recorded runs are preserved. No existing proposal or approval was
  migrated or rewritten. Older proposals require regeneration/review.
  Page fields remain uncalculated; no PDF, rendering or automatic two-sided
  layout default is added. No commit or publication.
- **Approved-proposal standalone test (2026-11-16 UTC, IDP-C34):**
  verified the human design-approval receipt and exact proposal object, then
  tested the standalone API without workflow integration. The original requested
  DOCX plus print PDF and correctly failed `unsupported_target`. With explicit
  user confirmation, a separate test proposal retained only its existing DOCX
  target and received a distinct test identity; all layout/manuscript choices
  remained unchanged. Native construction and an independent reopen check pass:
  238 source paragraphs match in order across six sections, with five named
  styles, requested blank headers and body PAGE field definitions without
  fabricated cached values. Source/approval hashes and workflow revision/event
  history remain unchanged. Private inputs, effective plan, candidate and audit
  report stay under ignored `.workflow-runs/`, not in the source repository.
  This is a successful DOCX-only construction test, not completion of the
  approved bundle, workflow publication, rendering or print validation.
- **Title-header follow-up test (2026-11-16 UTC, IDP-C35):** regenerated a
  separate private DOCX-only candidate using the book-title preset in all five
  body-section headers. The test uses an explicit centered Georgia 9 pt header
  style copied from existing footer typography; front matter stays blank.
  Reopen checks confirm exact title text, unchanged 238 manuscript paragraphs
  and their styles, six sections, unchanged page geometry and identical footer
  XML. Original approval, previous candidate, workflow state and events remain
  unchanged. Header fit/rendering and print verification are not claimed.
- **Quick Styles for post-generation editing (2026-11-16 UTC, IDP-C36 / R23):**
  the standalone DOCX formatter now marks every generated BF.* paragraph style
  as a Quick Style, including body, heading, special-role, header and footer
  styles. The effective policy/capabilities expose `quick_styles: true`, and
  reopened candidate verification rejects a missing flag before publication.
  Verified all 19 standalone tests locally and again from a rebuilt wheel in a
  clean environment outside the checkout, including API/CLI checks and a
  negative candidate-publication regression. Existing artifacts and workflow
  state stay unchanged. No schema option, rendering claim or automatic sync of
  subsequent Word edits is introduced; Word's gallery preferences still apply.
- **Workflow/Studio editable-DOCX integration (2026-11-16 UTC, IDP-C37 / R24):**
  literary editing's existing approved-design flow now reaches a persisted
  `produce-docx` step consuming only the installed formatter's public API.
  A safe plan-summary gate authorizes the exact plan/prototype policies;
  generation rechecks inputs/runtime and seals the actual verified DOCX and
  build manifest before exposing a candidate. Native steps construct no agent
  runtime or renderer. Explicit final editable acceptance binds the document,
  plan, manifest and approved proposal before versioned library publication
  and export. Studio supports candidate/accepted downloads on run/chapter
  pages and accepted-object downloads from Works; Word edits are not synced.
  New proposals must request only editable DOCX; PDF/mixed bundles are refused,
  not rewritten. Retry owns a new path; changed plans require fresh consent;
  design restarts invalidate stale candidates and retain archived evidence.
  Evidence: [host adapter](workflow/src/production.py),
  [workflow regressions](workflow/tests/test_workflow.py),
  [API/download regressions](studio/tests/test_web.py) and
  [real browser flow](studio/tests/test_cases.py). The 95-case combined suite
  passes with six expected browser/live skips; separate changed-plan and
  no-runtime CLI regressions also pass. All 19 standalone tests and the real
  API/engine browser flow pass, including desktop/390 px layout, candidate hash,
  final acceptance and library download. Frontend typecheck/build passes.
  Restarted the idle Studio server on the same port/data root and verified all
  nine raw run revisions/state hashes unchanged, with no worker auto-start.
  Existing approved bundles/runs are not migrated; outdated execution still
  requires an explicit workflow restart. Translation composition, PDF,
  field refresh, font resolution, rendered pages and print certification remain
  deferred/unimplemented. This does not close the full production milestone.
- **PR #6 rebase/integration verification (2026-11-16 UTC, IDP-C37):**
  rebased the formatter branch onto `origin/main` at `9179818` after runtime
  PR #5 merged. Conflict resolution preserves the shared compatible-model
  picker, pre-cancellation restart validation and execution-profile provenance
  alongside the DOCX approval/delivery flow. Run details retain token-usage
  aggregation while describing one state snapshot; run lists still omit usage.
  Native CLI production constructs neither Codex nor a configured profile
  runtime; the CLI regression exercises both configurations. Verified the
  132-test workflow/profile/API/case suite (nine expected browser/live/optional-
  harness skips), all nine browser/case checks (one expected live skip),
  six usage tests, 20 standalone formatter tests, and the expanded native-CLI
  regression. Frontend typecheck/build pass. Checks used isolated worktree/test
  data; no live run, manuscript or approval was changed. The formatter submodule
  remains pinned to `9288dc7`; no formatter behavior or POC scope changed.
- **PR #6 review fixes (2026-11-16 UTC, IDP-C37 / R24):** design-only stage
  restart restores the exact checkpointed vendor-profile bytes after archiving
  the old design directory. The manuscript approval/profile identity survives
  reopening and proposal generation; restarting manuscript approval still
  invalidates the old profile. The CLI now displays the design proposal/hash
  and author questions and exposes `review-design` save, revision-request and
  approval actions through the existing service. Every action binds the gate
  ID and proposal SHA-256; action-specific UTF-8 files carry spec edits,
  feedback or blocking-question answers. Stale bindings, missing answers,
  malformed JSON and mismatched file options fail without changing the gate.
  Approval without an answers file is allowed only when no questions block.
  Verified the three focused regressions, the 134-test workflow/profile/API/
  case suite (nine expected skips) and the Studio DOCX browser flow. No live
  workflow data, standalone formatter behavior or production scope changed.
- **HTML-free preparation with literal source preservation (2026-11-16 UTC,
  IDP-C38 / R25):** corrected the preparation boundary exposed by a blocked
  DOCX build. Empty DOCX paragraphs use ordinary blank-line spacing, never
  generated `<br />` or placeholder/ornamental content. HTML-looking text
  actually present in the original remains literal through Markdown escaping;
  it is neither interpreted as formatting, stripped nor given invented code
  styling. The shared preparation validator rejects parsed HTML blocks/inline
  tags with chapter/file/block-start-line diagnostics before readiness. Literal
  escaped text, existing code, autolinks and angle comparisons remain valid
  under the general preparation contract; the DOCX POC's narrower content
  limits remain unchanged. Verified 32 preparation, 29 proposal, 25 preparation-
  evaluation and 20 standalone formatter tests, plus two focused workflow
  regressions covering early rejection and successful DOCX delivery. Reopen
  checks confirm original escaped tag/comment characters appear literally in
  DOCX with no HTML styling. No live manuscripts, approved prepared revisions,
  proposals or run records were rewritten. Existing faulty extractions require
  a fresh revision using the updated skill and fresh dependent approval.
  [Preparation contract](plugins/manuscript-studio/skills/prepare-manuscript/references/preparation-contract.md).
- **Retained construction foundations:** the low-level
  [workflow/src/document_adapters.py](workflow/src/document_adapters.py)
  validates the settings, checks fonts, builds the DOCX, renders it with Word or
  LibreOffice, converges TOC page numbers, and rasterizes pages.
  [workflow/src/document_audit.py](workflow/src/document_audit.py) retains
  workflow-independent DOCX inspection. These utilities do not expose a legacy
  formatter or complete the remaining print/translation production integration.
- **Scope:**
  - An interior-design skill takes verified preparation, metadata, and agent
    reading (genre, synopsis, vibe, and related evidence) and emits a proposed
    design form. Construction and visual-QA attestation leave the skill.
  - The standalone tool's intake combines the proposed form, user choices,
    versioned vendor constraints, and real font/producer capabilities into one
    effective specification, exposed through the native GUI for approval.
    Initial print-vendor support targets IngramSpark.
  - The shared formatting phase is composed by literary editing and translation,
    not registered as a separate public workflow. Its preparation package must
    match the actual text being formatted; output preparation cannot overwrite
    the original source package.
  - Literary editing requires manuscript approval before final formatting after preparation and
    metadata review, with zero editing passes or after any accepted pass
    (owner clarification, 2026-11-13). This skips editing, not preparation,
    outstanding pass gates, design approval, or human page review.
  - The build runs as a worker job, one renderer instance at a time; revised
    settings create a new candidate and invalidate previous page approval.
  - Native technical checks and human approval of the exact final page set gate
    publication. Production identity uses effective design/input/profile/tool
    facts, not model/skill hashes. Agent provenance is recorded separately.
  - Editable DOCX/review output and vendor-ready interior PDF are distinguished;
    ordinary PDF export is not proof of IngramSpark/PDF print compliance.
- **Acceptance criteria:**
  - Both parent workflows can drive the phase in the browser from the correct
    ready preparation package. After design approval, production/rebuilds require
    zero agent calls; unchanged inputs/settings/tooling yield repeatable text,
    structure, and pagination checks.
  - No edition is published without receipt-bound effective-design approval and
    human page approval of that exact build.
  - The zero-pass editing route formats the unchanged prepared manuscript
    without invoking editorial passes or claiming it was edited. After accepted
    passes, formatting uses preparation of their exact output.
  - Existing content, heading, TOC, and page-number checks still pass; the new
    automated checks fail clearly. Unintended blanks are distinguished from
    approved layout blanks and vendor-side processing.
  - Vendor-target readiness is claimed only when applicable pinned profile
    checks pass; unsupported print capability is blocked, not silently waived.
  - Producer tests run with a stand-in renderer, without Word/LibreOffice or an
    agent. Design-skill and embedded-workflow checks are separate.
- **Known current limits:** English output only (the Contents
  label is hard-coded); scene-break rules (`***`, `---`), lists, images, code,
  and special forms such as poetry are refused; Word rendering requires a
  Windows server, otherwise LibreOffice, whose pagination can differ.
- **Open decisions:** remaining publication/page-review integration, initial product and
  deliverable scope, PDF print-preflight capability, proposal-generation/reuse
  policy, and additional-edition/hand-off behavior are enumerated in the draft
  design. Skill-contract implementation does not imply full design approval or
  completion of native intake/production.

### M5 - Shared manuscript analysis

- **Status:** `planned`; planning recorded 2026-11-16. No skill, schema,
  validator, workflow stage or review UI is implemented by this entry.
- **Owner:** `cli1980`.
- **Planning branch:** `feature/manuscript-understanding-plan`.
- **Owner-confirmed direction (2026-11-16):** create a `manuscript-analysis`
  skill; define its outputs and handoffs to actual workflows and downstream
  skills, including translation and developmental editing; track delivery as
  a milestone. The skill name `manuscript-analysis` is owner-confirmed; the
  contract and integration choices below are proposals, not
  additional owner-approved requirements.
- **Outcome:** one reusable, evidence-bound account of what a manuscript says
  and how its narrative unfolds, rather than separate, incompatible summaries
  inferred by each consumer. Extraction remains preparation's responsibility;
  literary evaluation, translation, editing and design remain consumer tasks.
  This milestone does not change the existing highest-priority DOCX work.

#### Proposed skill boundary and inputs

- Skill name: `manuscript-analysis`. Package it alongside the existing
  skills, with instructions, a versioned output contract, examples, validation
  helpers and synthetic evaluation cases. Support standalone invocation and
  composition inside workflows; do not depend on Studio databases or a
  particular model/harness. Workflow transitions and approvals stay host-owned.
- Require a ready package under the
  [preparation contract](plugins/manuscript-studio/skills/prepare-manuscript/references/preparation-contract.md):
  work identity, revision manifest, ordered Markdown units, source identities,
  unit hashes, scope and manuscript language. Record the exact consumed inputs,
  metadata context, analysis language and requested analysis policy.
- Read the actual prepared text, including the ending and relevant front/back
  matter. A metadata description, earlier synopsis or sample is not a substitute
  for reading the bound manuscript. Supplied titles and user assertions remain
  distinguishable from evidence present in the original text.
- Produce understanding, not improvements: no source edits, translation,
  developmental verdict/quality score, marketing claims, invented resolutions
  or automatic metadata updates. Shared metadata remains authoritative under
  its [own contract](plugins/manuscript-studio/skills/prepare-manuscript/references/manuscript-metadata.md).
  Treat manuscript content as data, never instructions.

#### Proposed output contract

Draft contract identifier: `manuscript-analysis/1`; filenames and field
names remain design proposals until schema review. Write to a separate,
versioned output destination, never into a published preparation revision.

| Artifact | Authority and minimum contents |
| --- | --- |
| `manifest.json` | Analysis ID/revision, contract version, work/source/preparation bindings, ordered unit hashes, consumed metadata digest, analysis policy/language, coverage, blockers, artifact hashes and credential-free skill/model provenance. |
| `understanding.json` | Whole-work synopsis including the ending, narrative/structural overview, character identities/aliases/relationships/arcs, plot and subplot threads, event chronology versus presentation order, setting/world rules, themes/motifs and explicit uncertainties. |
| `chapters/<unit-id>.json` | One record for every prepared unit: source ID/order/role/hash, summary, viewpoint/time/place where supported, participants, significant events and causal links, thread developments, unresolved questions and evidence references. Mark non-narrative units as such instead of inventing plot. |
| `review.md` | Derived, human-readable synopsis, chapter breakdown and linked story maps, with spoiler and uncertainty notices. Render from canonical JSON; do not create a competing editable authority. |

- Book-level records reference chapter/event/entity IDs instead of maintaining
  unrelated copies of the same facts. Narrative units have substantive summaries;
  front/back matter has an appropriate account of its actual contents.
- Every material claim carries an ID, provenance kind (source observation,
  interpretation or user assertion), supporting/contrary evidence where
  applicable, confidence and uncertainty. Evidence binds a prepared unit hash
  and an exact quote/span. Define offsets against the exact UTF-8-decoded
  Markdown text, without normalization, so repeated quotations are unambiguous.
  Package-local IDs must not masquerade as canonical preparation annotations.
- Distinguish events from interpretations, intended ambiguity from omissions,
  and apparent contradictions from confirmed errors. Do not resolve unreliable
  narration or incomplete series arcs by invention. Unsupported assertions
  remain unknown/provisional; confidence is not human approval.
- Coverage names every supplied unit and whether it was analyzed, excluded
  with a reason, or remains unread/blocked. A partial read cannot yield a
  complete-novel synopsis or satisfy a consumer requiring whole-work coverage.
  A completed reading may still contain legitimate interpretive uncertainties.

#### Proposed generation, persistence and freshness

1. Verify preparation/source bindings and inventory the complete requested
   scope. For long novels, persist unit-level reading checkpoints before
   whole-book synthesis; model context limits must not silently omit chapters
   or redefine chapter boundaries.
2. Read units in source order, collect cited local notes, then synthesize and
   cross-check book-level claims, chronology, entities and unresolved threads.
   Report blocked or partial coverage instead of claiming an unread ending.
3. Validate schemas, IDs, references, unit coverage, quote/span matches and
   artifact hashes. Deterministic checks establish structural/evidence integrity,
   not that an agent truly read every word or interpreted the novel correctly.
   Include semantic review/evaluation separately.
4. Publish an immutable analysis revision through the host's artifact library;
   standalone callers retain the same package contract in their chosen output
   directory. Consumers pin a package hash, not a mutable "latest" path.
5. Reuse only after checking work, ordered content hashes, scope, language,
   consumed metadata and analysis policy/contract compatibility. Record both
   the original preparation binding and each consumer's verified binding.
   Current runs still prepare independently: reuse of reading is not permission
   to skip preparation or silently relabel an analysis for a different manifest.
   Any cross-manifest equivalence check must be explicit and auditable.
6. Changed text/order/scope or relevant context makes affected analysis stale.
   Changed chapter notes require renewed cross-chapter synthesis; unchanged
   notes may be reused only with verified dependencies. Translated or edited
   text is a distinct input, not automatically covered by the original reading.
   Corrections create an attributable revision, never overwrite published data.

#### Proposed workflow and downstream handoffs

Recommended placement is after verified preparation and existing metadata
review, before workflow-specific briefing or editorial jobs. Whether this is
mandatory for every run and whether it needs a separate human gate remain open.
The skill emits data/readiness; the host decides progression and reuse.

| Consumer | Handoff and retained responsibility |
| --- | --- |
| Literary translation | Consume the source synopsis, chapter/character/thread maps and ambiguities when building the glossary, voice guidance and samples. Keep the approved translation brief authoritative for translation choices. Continue checking actual source passages; the analysis neither replaces fidelity review nor proves understanding of the eventual target text. |
| Developmental editing | Start from the shared chapter/event/arc map rather than inventing an incompatible intake synopsis. Still read the complete bound manuscript and assess structure, causality, pacing and character independently; observations are not diagnoses or approved recommendations. Preserve editorial review/application gates. |
| Line/copy editing | Use character, chronology, world-rule and unresolved-thread records as continuity context, not authorization to rewrite text or turn disputed interpretations into facts. Refresh against accepted changes before relying on them. |
| Interior design | Adapt bound synopsis/themes/voice/structure into the existing proposal `reading` fields with provenance. Require fresh or explicitly revalidated reading for changed edited/translated text. No change to formatter approval, production inputs or print-readiness claims is implied. |
| Future querying/other skills | Derive consumer-specific synopses or briefs from the same cited understanding. Query emphasis, spoiler policy, author biography and external claims remain separate concerns; a neutral full synopsis is not automatically a submission-ready pitch. |

- Each handoff names the prepared input identity, analysis revision/package hash,
  required scope, readiness and unresolved limitations. Incompatible/stale
  packages fail explicitly or return to understanding generation; never silently
  use a summary from another work, language or revision.
- Standalone consumers use the same contract checks as workflows. Studio/CLI
  should expose readable coverage, synopsis, chapter summaries, evidence,
  uncertainties and freshness without making raw JSON the only review surface.
  A future human correction/approval receipt must bind the exact package and
  remain distinct from downstream translation/editing/design approval.

#### Delivery sequence and acceptance criteria

- **Contract first:** review the skill boundary, output schema/examples,
  readiness/evidence rules, consumer adapter contracts and explicit open choices.
- **Standalone skill:** implement reading/synthesis instructions and structural
  validators; evaluate against synthetic short works and a whole-novel case with
  independently checked summaries. No private novel enters version control.
- **Host integration:** persist/resume/publish/pin analyses and test stale-input,
  partial-read, metadata-context, interrupted-synthesis and revision handling.
  Integrate translation and developmental editing first, with Studio/CLI review.
- **Other consumers:** add line/copy, design and querying adapters only with
  source-freshness tests; do not claim these integrations from schema presence.
- **Acceptance:** a complete novel yields a source-bound full synopsis,
  per-unit summaries and coherent entity/thread/timeline records with navigable
  evidence; missing units and unsupported claims are visible, not fabricated.
  Cover repeated quotations, reordered/edited chapters, multilingual evidence,
  non-narrative units, ambiguous identities and unresolved endings in evaluation.
- **Acceptance:** translation and developmental editing demonstrably consume
  the same pinned analysis of the same text, retain their independent source
  reading and human gates, and refuse stale/partial packages when complete
  coverage is required. Verify standalone and host behavior, restart/reuse,
  immutable published revisions, and human-readable Studio/CLI access.
- **Acceptance:** preparation/source bytes and confirmed metadata remain
  unchanged; no analysis is treated as source-update permission, semantic-role
  transfer, literary-quality certification or final artifact acceptance.
- **Open choices before implementation:** initial manuscript/language coverage;
  analysis language and summary depth/length presets; mandatory versus optional
  placement/reuse policy for each workflow; human review/correction requirements
  and promotion authority; precise cross-manifest equivalence rules; treatment
  of non-fiction/mixed forms and incremental re-synthesis dependencies.
- **Related contracts:** [shared preparation](plugins/manuscript-studio/skills/prepare-manuscript/references/preparation-contract.md),
  [developmental review](plugins/manuscript-studio/skills/literary-editing/references/developmental-edit.md),
  [translation workflow](workflow/src/translation.py) and
  [design proposal reading](plugins/manuscript-studio/skills/interior-design/references/proposal-contract.md).
  These describe current consumers, not implementation evidence for M5.

### Later (unordered)

- DOCX formatting from the web application
- PDF manuscript intake
- Additional workflows, such as literary-agent querying
- Immediate pause by interrupting the current agent turn (removed from M3 on
  2026-11-10). Worth revisiting if turns get much longer. App Server's
  `turn/interrupt` and the engine's existing `PAUSED` handling for an
  interrupted turn cover most of it; the runtime needs a cancel signal and the
  worker a handle on each run's current turn.
