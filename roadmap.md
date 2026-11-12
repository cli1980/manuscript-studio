# Manuscript Studio roadmap

This is the shared roadmap and development progress record for humans and agents.

The current goal is a usable web frontend for managing manuscripts and their
workflows, starting with literary translation, followed by a Literary Edit
workflow supported in both the CLI and the web GUI.

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
- **DOCX first.** DOCX and Markdown/text intake come first; PDF comes later.
- **Generalize before expanding.** The engine must be generalized before any
  workflow other than literary translation is added.
- **Users.** Support a single user while keeping the architecture compatible with
  multiple users (fewer than 10).

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
  - After final acceptance, the run's own chapters and stages cannot be restarted (new runs on the work publish the next version), and
    are refused; after an engine update, unfinished runs allow only reading and
    restarting the workflow.
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

- **Status:** `in_progress` (started 2026-10-27 at the owner's direction, before M2)
- **Owner:** `cli1980`
- **Progress (2026-11-10, committed locally):**
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
  - Remaining:
    - Login and a configured HTTPS origin for remote mode.
    - A Markdown export download; the run page shows only the export path.
    - Viewing the original upload. Only text artifacts can be viewed, so a
      DOCX source cannot.
    - The live-model and human quality review of whole-book consistency.
  - No acceptance criterion is recorded as met yet. Translation run
    `dcc6b1e2` was completed and finalized in the studio on 2026-11-07; the
    owner has not yet reviewed it as evidence.
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
  - Read-only views of the original upload, prepared chapters, and workflow
    outputs.
  - Metadata editing with version history.
  - All translation gates as native forms driven by the approval-sheet JSON and
    submitted through the existing validator and parser; final acceptance with
    source and English side by side; Markdown export download.
  - Whole-book translation consistency (added by the owner on 2026-10-28;
    implemented locally on 2026-11-06; live model and human quality review
    pending). Chapters carry continuity through shared files
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
  - Localhost by default. A documented remote deployment requires login and a
    configured HTTPS origin when not bound to loopback. Codex credentials are
    configured server-wide.
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
  - Remote mode refuses unauthenticated access.
- **Out of scope:** DOCX formatting in the web application, PDF intake, user
  management, real-time collaboration, non-English targets, and manual
  manuscript text editing.

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
  - A native settings gate replaces the agent's design proposal: profile
    presets (submission, editorial-review, reader-facing) with defaults from
    the work's metadata, fonts available to the selected renderer, and the
    existing settings validation. The receipt binds the exact settings.
  - The build runs as a worker job, one renderer instance at a time; revised
    settings rebuild into a new build directory.
  - A page-review gate replaces the agent attestation: the user inspects the
    rendered pages, then approves (publish, export, hand off) or revises the
    settings. QA records the human receipt.
  - Automated checks support that review: fonts in the rendered PDF match the
    settings, no blank pages, no stranded headings, and the page count.
  - Studio: a grouped settings form with presets and a rendered-page gallery
    in the shared decision panel.
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
- **Open decisions:** whether an optional agent "suggest settings" action
  remains; whether review happens in the chapter viewer (UX enhancement
  Phase 3) or on the run page; whether scene-break and non-English support are
  part of this feature; whether the external Documents-skill path is kept.

### Later (unordered)

- DOCX formatting from the web application
- PDF manuscript intake
- Additional workflows, such as literary-agent querying
- User management for multiple users
- Immediate pause by interrupting the current agent turn (removed from M3 on
  2026-11-10). Worth revisiting if turns get much longer. App Server's
  `turn/interrupt` and the engine's existing `PAUSED` handling for an
  interrupted turn cover most of it; the runtime needs a cancel signal and the
  worker a handle on each run's current turn.
