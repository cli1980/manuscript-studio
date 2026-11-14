# SC-03 - Workflow dashboard

**Current routes:** `#/runs`, `#/runs/new/:workId`

**Flows:** UF-05, UF-15

**Implementation:** [Runs.tsx](../../../studio/frontend/src/views/Runs.tsx)

## Current contract

- Global navigation labels this surface Workflows.
- A start form chooses an existing work and a non-derived workflow template.
  A work can be preselected by the route; busy work options are disabled.
- The selected template explains its stage sequence or editing pass selection.
  Successful launch opens the workflow's landing page.
- The run list shows run/template/work, status, stage/chapter, progress, Needs,
  and creation time. Review links route to the appropriate decision surface.
- Empty runs, load failures, launch errors, and submitting state are visible.
- Live-change notifications refresh the list without a new run per refresh.

## Target boundary

Workflow/status/needs-me filters belong to the
[workflow-explorer design](../designs/studio-interface.md); none is current.
The form does not expose work-details passage-size controls, profile selection,
model choice, token statistics, users, or role filters in this baseline.

## Validation

Source-mapped; no new browser session is claimed.
See [API/case tests](../../../studio/tests/test_cases.py) and
[live feed implementation](../../../studio/frontend/src/live.ts).
