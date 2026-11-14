# SC-06 - Shared decision panel

**Role:** shared component, not an independent route

**Flows:** UF-06, UF-07, UF-08, UF-09, UF-11, UF-12, UF-13

**Implementation:** [GatePanel.tsx](../../../studio/frontend/src/views/GatePanel.tsx),
[AgentFeedback.tsx](../../../studio/frontend/src/views/AgentFeedback.tsx),
[SheetReview.tsx](../../../studio/frontend/src/views/SheetReview.tsx)

## Current contract

- Workflow presentation supplies headings, copy, command labels, and placement.
  Chapter-based decisions appear beside/after their evidence in the viewer;
  formatting decisions stay in run management.
- The frame selects bodies for metadata, pass/engine choices, document review,
  sample poll, shared agent feedback/sheets, and final acceptance.
- The agent-feedback widget shows prior feedback/answer, sheet items or offered
  commands, and feedback input. A request to revise is not approval.
- Sheet drafts use run/sheet/revision keys; item notes follow the declared
  decision requirements. Submit composes exact commands for server validation.
- Closure follows the sheet contract, not one universal extra click.
  Pass acceptance, apply authorization, and irreversible final acceptance are
  distinct domain decisions even when they share a frame.
- Final acceptance lists output hashes and requires a finalization
  acknowledgement before submission.

## Target boundary

The [unified-panel design](../designs/studio-interface.md) describes consistent
header/conversation/closure and irreversible styling, not the removal of all
body types or domain-specific commands. Rejected submission/reload draft
durability needs body-specific validation; do not generalize feedback tests.

## Validation

Source-mapped. [Approval parser tests](../../../plugins/manuscript-studio/skills/review-approval-sheet/scripts/test_approval_review.py)
cover parser semantics, not the complete native web presentation.
