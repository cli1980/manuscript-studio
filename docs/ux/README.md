# Manuscript Studio UX specification

**Specification version:** 0.1

**Baseline:** `87b7737`, the main-derived code on `feature/ux`, 2026-11-13

**Scope:** the localhost studio web application, not the standalone skills,
evaluation review server, or unmerged runtime-extensibility branch.

This is the version-controlled source of truth for user journeys, screen
contracts, interaction rules, and UX design decisions. The
[roadmap](../../roadmap.md) owns milestone scope, delivery status, priority, and
implementation/test evidence. It links here instead of duplicating designs.

## How to read the specification

- **Current:** mapped to the baseline's source code. This migration does not
  claim a new interactive walkthrough or successful live workflow execution.
- **Recorded decision:** a previously recorded owner decision, with its date
  and implementation qualifications preserved.
- **Target:** a planned design, not an assertion about the current UI.
- **Open question:** a review prompt, not an approved requirement or scheduled task.
- Documentation coverage, design approval, implementation, and validation are
  separate dimensions. Updating a diagram does not change any of the others.

The implemented entry points are Works, work details, Workflows, run management,
and the in-run chapter viewer. The proposed four-interface restructuring is
only partially implemented; see the [design record](designs/studio-interface.md).

## Flow inventory

All 18 current flows are **source-mapped** below. Their browser-validation status
for this specification is **not newly verified**. Evidence links identify existing
tests to consult or extend, not a claim that every path is already covered.
Targets remain governed by the linked design records; no per-flow redesign has
been approved by creating this index.

| ID | Feature / user goal | Current specification | Target / design context |
| --- | --- | --- | --- |
| UF-01 | Works: add manuscript | [Add a manuscript](flows/UF-01-add-manuscript.md) | Works explorer |
| UF-02 | Works: inspect a work | [Browse a work](flows/UF-02-browse-work.md) | Version-oriented explorer |
| UF-03 | Works: access source/artifacts | [Retrieve source and artifacts](flows/UF-03-retrieve-artifacts.md) | Downloads and source preview |
| UF-04 | Metadata: maintain shared facts | [Maintain metadata](flows/UF-04-maintain-metadata.md) | Metadata-version comparison |
| UF-05 | Execution: launch a run | [Start a workflow](flows/UF-05-start-workflow.md) | Shared entry-point behavior |
| UF-06 | Preparation: confirm the input | [Prepare and confirm metadata](flows/UF-06-prepare-and-confirm.md) | Front-matter decision record |
| UF-07 | Translation: produce an accepted translation | [Translate a manuscript](flows/UF-07-translate.md) | Aligned viewer / whole-book reading |
| UF-08 | Editing: select and accept passes | [Edit a manuscript](flows/UF-08-edit.md) | Whole-book reading / editing diffs |
| UF-09 | Formatting: produce a verified DOCX | [Format an accepted version](flows/UF-09-format.md) | [Agent-free formatting](designs/deterministic-formatting.md) |
| UF-10 | Continuation: reuse a formatted edition | [Continue from formatted output](flows/UF-10-continue-formatted-work.md) | Work lineage |
| UF-11 | Review: read and give anchored feedback | [Review chapters and documents](flows/UF-11-review-content.md) | Paragraph alignment |
| UF-12 | Decisions: resolve a human gate | [Resolve an approval gate](flows/UF-12-resolve-gate.md) | Unified decision panel |
| UF-13 | Acceptance: finalize immutable output | [Accept and finalize](flows/UF-13-finalize.md) | Consistent irreversible-action treatment |
| UF-14 | Versioning: publish another version | [Publish the next version](flows/UF-14-next-version.md) | Accepted-version reader |
| UF-15 | Monitoring: understand run state | [Monitor execution](flows/UF-15-monitor.md) | Inspector / workflow filters |
| UF-16 | Controls: suspend automatic work | [Pause and resume](flows/UF-16-pause-resume.md) | No immediate-interrupt UI |
| UF-17 | Recovery: retry or redo scoped work | [Recover or restart](flows/UF-17-recover.md) | Explain scope and retained work |
| UF-18 | Controls: cancel an unfinished run | [Stop a workflow](flows/UF-18-stop.md) | Consistent destructive-action treatment |

## Screen contracts

| ID | Screen / component | Current route or role |
| --- | --- | --- |
| SC-01 | [Works](screens/works.md) | `#/works`; intake and work list |
| SC-02 | [Work details](screens/work-details.md) | `#/works/:workId`; metadata, library, versions, runs |
| SC-03 | [Workflow dashboard](screens/workflows.md) | `#/runs`, `#/runs/new/:workId`; start form and run list |
| SC-04 | [Run management](screens/run-management.md) | `#/runs/:runId`; status, controls, timeline |
| SC-05 | [Chapter viewer](screens/chapter-viewer.md) | `#/runs/:runId/chapters[/:chapterId]`; reading and decisions |
| SC-06 | [Decision panel](screens/decision-panel.md) | Shared component, not a separate route |

## Design and decision records

- [Interaction principles and domain boundaries](principles.md)
- [Studio interface design record](designs/studio-interface.md): migrated
  interface review, owner decisions, phases, gaps, and acceptance criteria.
- [Deterministic formatting target](designs/deterministic-formatting.md):
  proposed settings/page-review flow, not today's agent-backed flow.
- [UXD-001: intake, review, versioning, and control decisions](decisions/UXD-001-interaction-contracts.md)
- [Migration map](migration.md): where former roadmap detail now lives.

Authentication, team roles, literary-agent querying in the studio, accepted-version
reader routes, and runtime-profile/model/token UI are not current flows in this
baseline. Remote mode and runtime work retain their separate roadmap entries.

## Change and review process

1. Assign stable `UF-`, `SC-`, or `UXD-` IDs; do not renumber existing records.
   Start a new flow from the [template](flows/_template.md).
2. Record current behavior from code and, when available, a browser walkthrough.
   Describe user actions, visible responses, and decisions rather than internal
   agent calls. Include empty, invalid, cancelled, failed, and stale-state paths.
3. Keep target diagrams separate from current diagrams. Record who reviewed
   a design and what evidence exists; never infer approval from documentation.
4. Link implementation work in the roadmap to these IDs. Do not create a second
   priority list, milestone tracker, or duplicate implementation backlog here.
5. Implement against observable acceptance checks. Link browser/API tests to flow
   IDs as coverage is actually added; existing test names alone are not coverage.
6. Update the current flow and screen contract in the same change as behavior.
   Preserve replaced design rationale in Git or a dated decision record.

Git records individual revisions. Increment the specification version for a
coherent reviewed baseline, not every spelling correction. No additional review
approval is implied by version 0.1.

## Validation

```text
python scripts/check_ux_spec.py
```

Mermaid source lives in fenced blocks in these Markdown files, not duplicated
`.mmd` files. The editor and GitHub render it. Mermaid CLI can render a Markdown
file's diagrams for review, for example:

```text
mmdc -i docs/ux/flows/UF-01-add-manuscript.md -o .workflow-runs/ux-preview.md
```

Keep generated previews, screenshots, and traces in ignored local output, not as
a competing specification. The checker validates IDs, required flow sections,
screen coverage, and local document links; it does not prove usability or render
Mermaid itself.
