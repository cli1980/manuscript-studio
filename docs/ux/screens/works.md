# SC-01 - Works

**Current route:** `#/works`

**Flows:** UF-01, UF-02

**Implementation:** [Works.tsx](../../../studio/frontend/src/views/Works.tsx)

## Current contract

- Global navigation distinguishes Works from Workflows; the workspace is local.
- Intake offers a `.md`, `.txt`, or `.docx` file, manuscript language, and
  "Add as a new work." It does not start preparation.
- The work list shows title, ID, language, workflow summaries, run count, and
  creation time. Title opens work details; an unfinished-run link opens the run.
- No-works text points to intake. File/language requirements disable submission;
  submitting and server errors are visible.
- The global pending-review notice can route directly to a decision.

## Target boundary

Intake stays here in the [explorer design](../designs/studio-interface.md).
There is no current search/filter, work deletion, bulk intake, or source preview
contract. A proposed wireframe must label such additions as targets.

## Validation

Source-mapped, not newly browser-observed. The
[multiple-intake API case](../../../studio/tests/cases/works-intake-multiple-001/case.json)
is relevant to creation semantics, not evidence of visual usability.
