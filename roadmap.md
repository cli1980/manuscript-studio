# Manuscript Studio roadmap

This is the shared roadmap and development progress record for humans and agents.

The current goal is a usable web frontend for managing manuscripts and their
workflows, starting with literary translation, followed by a Literary Edit
workflow supported in both the CLI and the web GUI.

## Conventions

- Milestones are outcome-based and ordered by priority. They have no target dates.
- Every milestone is owned by the project owner, `cli1980`, unless stated otherwise.
- The roadmap file stays at `roadmap.md`, which is where [AGENTS.md](AGENTS.md) points.

## Cross-cutting decisions

Agreed in the 2026-10-26 planning session:

- **Workflow first.** The user chooses a workflow, then uploads the manuscript
  for that run. Preparation remains the run's first stage.
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
  prepared revisions, shared metadata, accepted outputs) are shared across
  workflows through an engine-owned library per work. Git versioning is a
  future consideration.
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

- **Status:** `in_progress`
- **Owner:** `cli1980`
- **Design:** [workflow/docs/m1-design.md](workflow/docs/m1-design.md)
  (owner-reviewed 2026-10-26)
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
    publication log, one unfinished run per work, and workflows that become
    read-only on a work after finalization.
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
  - A second run on an existing work reuses the published prepared revision and
    metadata; creating a run on a work with an unfinished run is refused.
  - Restarting a chapter archives its work, restores glossary and voice from the
    last completed chapter, and translates only that chapter again; restarting a
    stage or an unfinished workflow keeps receipts and events.
  - After final acceptance, restarts and new runs of that workflow on the work
    are refused; after an engine update, unfinished runs allow only reading and
    restarting the workflow.
- **Progress:** the metadata review gate is implemented in the current engine
  and CLI (2026-10-26). The remaining scope has not started.

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

- **Status:** `planned`
- **Owner:** `cli1980`
- **Depends on:** M1, M2
- **Outcome:** A user can run a complete literary-translation workflow from the
  browser.
- **Scope:**
  - FastAPI backend and React/TypeScript frontend built on the M1 service API.
  - Choose a workflow, then upload a DOCX or Markdown manuscript (creating a new
    work) or select an existing work, and create the run.
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
  - Manuscript text cannot be modified from the GUI outside workflow gates.
  - Metadata edits are versioned and visible in history.
  - Remote mode refuses unauthenticated access.
- **Out of scope:** DOCX formatting in the web application, PDF intake, user
  management, real-time collaboration, non-English targets, and manual
  manuscript text editing.

### M4 — Literary Edit workflow

- **Status:** `planned`
- **Owner:** `cli1980`
- **Depends on:** M1; M3 for web support
- **Outcome:** A Literary Edit workflow is available in both the CLI and the web
  GUI.
- **Scope:** To be defined before work starts. The workflow follows the
  cross-cutting decisions above.

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
