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

## Milestones

When adding milestones, record their intended outcomes, acceptance criteria,
status, owner, and relevant issue or implementation links. Use these statuses:
`planned`, `in_progress`, `blocked`, `in_review`, and `done`.

### M1 — Generalized workflow engine

- **Status:** `planned`
- **Owner:** `cli1980`
- **Outcome:** Workflows are pluggable templates, and the CLI and the web
  application share one engine service layer.
- **Scope:**
  - A workflow registry and per-template definition schema replace the
    hard-coded translation-only definition check in `workflow/src/engine.py`.
  - Generic stage kinds: agent stage, artifact acceptance, and export.
  - One service API for creating a run from a chosen workflow and uploaded file,
    stepping, replying to gates, accepting, pausing, resuming, restarting,
    stopping, reading events, and editing metadata. The CLI becomes a thin
    client of this API.
  - A server-level run index with an owner on every record, alongside the
    existing per-run state.
  - Versioned metadata edits: each change increments `record_revision`, retains
    a snapshot, and records an event. Edits are refused while an agent turn is
    running, and fields the run depends on (such as `manuscript_language`) are
    locked once the run exists.
- **Acceptance criteria:**
  - Literary translation runs through the registry with unchanged behavior, and
    the existing workflow test suite passes.
  - A test-only template can be registered and executed without engine changes.
  - Metadata history can be listed and each version inspected.

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
  - Choose a workflow, upload a DOCX or Markdown manuscript, and create the run.
  - A background worker runs agent turns automatically until the run needs a
    human (gate, acceptance, blocker, or failure); replies resume it.
  - An intuitive workflow dashboard and run view for inspecting status: overall
    state, current stage and chapter, progress, the pending human action, the
    reason for any blocker or failure, and a timeline with a live event stream.
  - Workflow controls with clear availability and confirmation:
    - **Pause:** stop automatic execution, either after the current agent turn or
      immediately by interrupting it, preserving saved state.
    - **Resume:** continue automatic execution from the saved state.
    - **Restart:** retry the current step from its last verified checkpoint after
      a failure, block, or pause.
    - **Stop:** cancel the run permanently, retaining its artifacts and history.
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
    and can pause, resume, restart, and stop it. Only controls valid for the
    current state are offered, and no control bypasses a human gate or loses
    saved state.
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
