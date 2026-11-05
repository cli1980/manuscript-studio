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

- **Status:** `planned`
- **Owner:** `cli1980`
- **Outcome:** Preparation accepts DOCX uploads through an extraction adapter with
  source comparison.
- **Acceptance criteria:**
  - A DOCX manuscript produces a verified chapter package, and
    `validate_preparation.py --check-sources` succeeds.
  - Unsupported DOCX content blocks preparation instead of being silently dropped.
- **Out of scope:** PDF intake (later).

### M3 — Web MVP for literary translation

- **Status:** `in_progress` (started 2026-10-27 at the owner's direction, before M2)
- **Owner:** `cli1980`
- **Progress (2026-10-27, local and uncommitted):** FastAPI backend
  (`studio/server/`, localhost-only with an explicit loopback preview-origin
  option) over the M1 service, a background worker that runs turns until a human
  is needed with pause-after-turn and resume, and a React/TypeScript (Vite)
  frontend (`studio/frontend/`) with three views: Works (manuscript intake, work list, library,
  metadata, publication log, derived formatting), Workflows (dashboard, start a
  workflow on a work, run view with `available_actions` controls, native gate
  forms for approval sheets, exact commands, metadata, and irreversible final
  acceptance, plus a timeline), and an in-run chapter browser (prepared chapters
  beside each stage's completed output). Immediate pause by interruption, login
  for remote mode, and a live event stream (the UI polls) remain.
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
    - **Pause:** stop automatic execution, either after the current agent turn or
      immediately by interrupting it, preserving saved state.
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
  - Whole-book translation consistency (added by the owner on 2026-10-28; not yet
    implemented). Chapters already carry continuity through shared files
    (`glossary.md`, `voice.md`, completed English chapters, and the chapter
    brief), but each chapter is checked only against those files. After the last
    chapter and before final acceptance, the translation workflow runs one
    whole-book consistency pass over all English chapters against the source and
    continuity files: names and terminology, forms of address, voice drift per
    character or narrator, and cross-chapter references. It proposes only fixes
    for objective inconsistencies, as one approval sheet decided in a single
    submission with separate closure; it does not retranslate or restyle.
    Approved fixes are applied and the affected chapters re-verified before
    acceptance. The literary-translation skill defines the pass, and the
    template adds it as a concluding whole-book step.
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
  - Decided: when the source has no title or opening material, preparation
    stops and asks the user.
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
  - Every decision of a chapter-based run happens in the chapter viewer, and
    starting a run opens it.
  - Phase 1 (implemented and committed locally, 2026-11-04): starting a run opens the
    viewer; the viewer shows a run status bar with problem banners linking to
    run management, preparation questions before chapters exist, and final
    acceptance; the run page links to the viewer instead of showing decision
    forms for chapter-based runs.
  - Inline comments (owner decision, 2026-11-04; committed locally): feedback on text is given as inline
    comments on the translation (not the original) and on the brief documents, using Recogito's text
    annotator. Drafts stay in the browser until sent; each comment keeps its quote, range, and paragraph
    number so a later source/translation alignment can show it beside the matching original paragraph.
    Comments are sent as ordinary feedback, so the engine is unchanged.
  - Phase 2 (planned): a "Whole book" entry in the viewer for decisions not
    tied to one chapter, such as literary editing's developmental verdict and
    consistency passes. Needs a small web-API addition, because the chapter
    endpoint does not serve the internal whole-book ID; today these decisions
    have no working page. Needed before the editing workflow is used in the
    studio.
  - Phase 3 (planned): formatting decisions (settings sheet, visual check) stay
    on the run page until a formatted-document preview exists, then move into
    the viewer as a "Formatted document" entry that reuses the decision panel.
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

### Later (unordered)

- DOCX formatting from the web application
- PDF manuscript intake
- Additional workflows, such as literary-agent querying
- User management for multiple users

## Progress updates

Each update should include the date, changes being pushed, validation performed,
remaining blockers or human review, and the next step. If no milestone is
affected, state that explicitly and briefly describe the maintenance or
documentation change. Do not mark work complete while required review is pending.

- **2026-10-26** — Push of four local commits ahead of `origin/main`.
  - **Changes:**
    - `ed71c1f` standardizes the editable shared manuscript metadata contract
      (schema, `prepare_metadata.py`, validator updates) across workflows.
    - `610182e` adds blind multi-candidate translation evaluation (opaque
      candidate IDs, candidate generation/anonymization, judge runner and review
      server updates) and removes local-only full-length fixtures from Git.
    - `dc9126f` defines this roadmap: planning decisions and milestones M1–M4.
    - `7097366` adds `AGENTS.md`, requiring a committed roadmap update before
      every push.
  - **Milestones:** M1–M4 defined as `planned`; none started. The two earlier
    commits predate the milestones and are maintenance/evaluation work.
  - **Validation:** with Python 3.12.10 (`.venv-evals`), all existing suites
    passed: installer 30 (3 symlink skips), `test_sample_boundary` 6,
    `test_validate_on_demand` 6, `test_approval_review` 28 (1 Node.js skip),
    `test_validate_preparation` 25, `evals/tests` 73, `evals/server/tests` 55
    (7 browser skips), and `workflow.tests.test_workflow` 37. Live Codex E2E and
    browser tests were not run.
  - **Human review:** the owner reviewed and approved the roadmap requirements
    in the planning session. No separate review is recorded for `ed71c1f` or
    `610182e`.
  - **Blockers:** none.
  - **Next step:** start M1 by designing the workflow registry, definition schema,
    and shared service API.
- **2026-10-26** — M1 design and metadata review gate. The push also includes the
  five earlier local commits described in the previous entry, which had not yet
  been pushed.
  - **Changes:**
    - `8a9c22a` adds a required, engine-owned `metadata_review` gate between
      preparation and translation (`translation.json` now has five stages), a
      `metadata` CLI command for single-field edits through the pinned
      `prepare_metadata.py` helper, confirmation bound to the inspected record
      revision, a locked `manuscript_language`, E2E launcher support, tests, and
      documentation.
    - The roadmap commit adds the owner-reviewed M1 design
      ([workflow/docs/m1-design.md](workflow/docs/m1-design.md)) and updates the
      cross-cutting decisions, M1 scope and acceptance criteria, and M3 controls
      and notifications to match it.
  - **Milestones:** M1 moves to `in_progress`; only the metadata review gate is
    implemented. M3 scope changes (Retry and Restart chapter/stage/workflow
    replace checkpoint Restart; finalization and engine-update notices); M3
    remains `planned`. M2 and M4 are unaffected.
  - **Validation:** with Python 3.12.10 (`.venv-evals`):
    `workflow.tests.test_workflow` 41 passed (37 existing, updated for the new
    gate, plus 4 new), `test_validate_preparation` 25 passed,
    `test_approval_review` 28 passed (1 skip), and `run_e2e.py --check-case`
    passed. Live Codex E2E and the other suites were not run; no code they cover
    changed.
  - **Human review:** the owner reviewed the M1 design in the 2026-10-26 session
    and answered every open question. One interpretation awaits owner
    confirmation: formatting runs count toward the one-unfinished-run-per-work
    limit. No separate code review is recorded for `8a9c22a`.
  - **Notes:** the local E2E case files under
    `workflow/tests/cases/translation-ciqing-001/` (gitignored) were updated
    for the new stage sequence but are not part of this push.
  - **Blockers:** none.
  - **Next step:** implement M1 in the design's order, starting with the
    `manuscript_language` rename and the registry/engine split.
- **2026-10-26** — GitHub Project for external requirements.
  Documentation-only change; no milestone scope or status changes.
  - **Changes:** added a convention that `roadmap.md` is the only record of
    planned work, and that the GitHub Project
    [Manuscript Studio Requirements](https://github.com/users/cli1980/projects/2),
    linked to the repository, is used only to collect and triage external
    requirements. The Project is empty, with intake Status options (New,
    Triage, Accepted, Declined, Moved to roadmap). Repository milestones and
    issues #1–#4 briefly mirrored M1–M4; at the owner's request they were
    permanently deleted, so the repository has no milestones or issues.
  - **Validation:** the empty Project, its Status options and repository link,
    and the absence of issues and milestones were read back through the GitHub
    API. No code changed, so no test suites were run.
  - **Human review:** the owner chose this arrangement in the 2026-10-26
    session. The open M1 question (whether formatting runs count toward the
    one-unfinished-run-per-work limit) still awaits confirmation.
  - **Blockers:** none.
  - **Next step:** continue M1 as planned.
- **2026-10-28** — Studio web MVP progress, shared fixtures, and pre-release cleanup,
  committed locally (not yet pushed).
  - **Changes:** `studio/` (FastAPI server, background worker, React/TypeScript
    frontend: works explorer with intake, typed metadata form and versioned
    format panel; run inspector; chapter viewer with live status, every chapter
    decision, item-by-item review screen); fixtures moved to `fixtures/`
    (北京一夜 added under MIT, Lin Shaw); versioned accepted output with
    `run.json`; implied closure for translation advice and map exceptions;
    internal passage map with engine-checked coverage; mandatory front-matter
    unit carrying the metadata review; metadata field groups and blank record
    at intake; prior-record consolidation; one unfinished run per work with no
    read-only rule; removal of version-1 work records, pre-M1 run shims,
    `import_run`, and legacy evals cases; licensing split (PolyForm
    Noncommercial for `workflow/` and `studio/`, Crossborder Art & Media LLC).
  - **Milestones:** M3 `in_progress`; UX enhancement item `planned`; M1 rules
    corrected (no read-only workflows).
  - **Validation:** workflow, web, and studio case tests 58 passed (1 live case
    skipped); prepare-manuscript skill 24; evals 127 passed (7 skipped);
    browser smoke test through the chapter viewer; live studio runs translated
    北京一夜 and 黑松石 to final acceptance.
  - **Human review:** the owner directed and exercised each change in the
    studio; no line-by-line code review is recorded.
  - **Next step:** UX enhancement item, step 1 (unified decision panel).
- **2026-10-27** — M1 generalized engine and first M4 literary editing
  template, committed locally (not yet pushed).
  - **Changes:** the M1 gap review (decisions recorded in
    [m1-design.md](workflow/docs/m1-design.md) section 13: no reuse of
    published preparation, formatting counts toward the one-run limit,
    work-level metadata edits, import publishes completed translations) and
    the complete M1 implementation: template registry and `template.json`
    files, engine split, template-declared gates, per-chapter iterations,
    retry and chapter/stage/workflow restarts, engine-update check, per-work
    library, service API and index, thin CLI with `--server-root`, formatting
    as a derived template, and the test-only template. M4's first iteration
    adds optional stages, several chapter stages with a concluding whole-book
    step, gate commands, and `literary-editing-v1` with `EditingEngine`. The
    E2E launcher creates runs through the service; its delegated-mode prompt
    now covers editing gates.
  - **Milestones:** M1 moves to `done` at the owner's direction. M4 moves to
    `in_progress` with its agreed scope; the remaining M4 work is listed in
    its section. M2 and M3 are unaffected.
  - **Validation:** with Python 3.12.10: `workflow.tests.test_workflow` 52
    passed, `test_validate_preparation` 25 passed, `test_approval_review` 28
    passed (1 skip), pyflakes clean on the changed workflow modules. Live
    Codex 0.163.0 E2E runs completed: translation of 《刺秦》 with DOCX
    formatting (all automated checks passed), and literary editing of the
    translated text with developmental skipped and DOCX formatting (all
    automated checks passed; no edits were proposed, so the apply path was not
    exercised live). Human-only evidence checks and literary quality were not
    reviewed.
  - **Human review:** the owner answered the M1 and M4 design questions in
    the 2026-10-27 session and marked M1 done. No separate line-by-line code
    review is recorded.
  - **Notes:** local, gitignored E2E cases and fixtures
    (`workflow/tests/cases/*-ciqing-001/`, `workflow/tests/fixtures/`) were
    updated or added and are not committed.
  - **Blockers:** none.
  - **Next step:** define the remaining M4 details (developmental stage,
    completed-chapter restarts, linking an edited translation to its source
    work) and exercise the apply path in a live editing run.
