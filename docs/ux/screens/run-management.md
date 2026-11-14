# SC-04 - Run management / inspector

**Current route:** `#/runs/:runId`

**Flows:** UF-09, UF-10, UF-15, UF-16, UF-17, UF-18

**Implementation:** [RunView.tsx](../../../studio/frontend/src/views/RunView.tsx)

## Current contract

- Show template/run identity, work link, status/worker state, stage/chapter,
  chapter and whole-book progress, pass history, turn count, and passage size.
- Show engine-mismatch/finalization/replacement-run banners, agent/worker
  errors, and local export/document paths where available.
- Controls follow available_actions: pause after turn/resume, retry, refresh
  review, restart chapter/consistency/stage/workflow, and stop. Confirmations
  and scope/reason prompts apply; unavailable actions expose reasons.
- The expandable timeline is an incremental event list.
- Editing/translation decisions redirect or link to the chapter viewer.
  Formatting retains its gates here. Finalized chapter runs can start derived
  formatting through the Word-default shortcut.
- Completed formatting links to the newly handed-off work.

## Target boundary

A form-free inspector and readable receipt/decision history are
[targets](../designs/studio-interface.md), not fully implemented.
Do not claim that every decision already leaves this page. No global token or
execution-profile panel exists in the main-derived baseline.

## Validation

Source-mapped. Existing [browser tests](../../../studio/tests/test_cases.py)
include `test_run_page_follows_the_change_feed_instead_of_polling`.
Control confirmation usability is not newly verified by this mapping.
