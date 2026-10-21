---
name: literary-editing
description: Review and edit book-length literary manuscripts through professional assessment, developmental review, line editing, copyediting, specialist review, proofreading, and final QA. Use when Codex needs to initialize or resume an editorial project with separate source and workspace locations; select dual-repository Git or artifact-workspace operation; route a whole manuscript or selected chapters to the right service; produce verdicts and scoped 1-5 editorial-acceptance scores; propose diffs without changing the source; present or quick-check interactive approval sheets and editable decision tables; apply only explicitly approved proposals; preserve voice and editorial state; commit approved workspace and source updates when Git is available; or produce a verified updated-source export for manual application when Git is unavailable.
---

# Literary Editing

Route each request to the appropriate professional editorial service. Keep the source and workspace separate, review first, and change nothing until the user explicitly approves identified proposals.

## Governing Contract

Follow these rules in every service:

1. Treat the author or authorized user as the creative decision-maker.
2. Treat the source location and workspace as separate managed locations. Never use the source location as the workspace.
3. Preserve the received source baseline. Delegate source discovery, extraction, and preparation verification to `prepare-manuscript`; do not perform editorial changes during intake.
4. Use the same workspace structure in every environment. Select `dual-repository-git` or `artifact-workspace` during setup.
5. In Git mode, use two separate local repositories: one for the workspace and one for the source draft. Never nest them.
6. Bind every verdict and proposal to the exact workspace review identity and the source identity from which it was imported: commit SHAs in Git mode or durable fingerprints in artifact mode.
7. Do not edit manuscript text while reviewing, diagnosing, writing a verdict, or generating proposals.
8. Apply only proposal IDs the user explicitly accepts or modifies. General approval, discussion, questions, or "continue" do not authorize edits.
9. Permit partial approval. Leave rejected, deferred, and pending proposals unapplied.
10. Revalidate approved proposals against the recorded review identity and exact current text. Mark invalid proposals `stale`; never guess how to rebase them.
11. In Git mode, commit each approved workspace batch, then update and commit the source draft separately after source revalidation.
12. In artifact mode, never modify the source location. Create a verified updated-source export and ask the user to apply it manually.
13. Keep each service within scope. Flag other editorial levels separately instead of silently performing them.
14. Do not claim whole-book completion from chapter passes without the required manuscript-wide synthesis or consistency check.
15. Give every verdict an editorial-acceptance score from 1 to 5, scoped to the requested service and reviewed material. Do not present it as a publication, sales, or market forecast.
16. Treat the interactive approval sheet and editable decision table as synchronized review interfaces, not manuscript-change authorization. The proposal ledger remains authoritative, quick-checking validates decisions only, and application still requires a separate explicit user instruction.
17. Treat paragraph breaks as a first-class line-edit dimension. Presume existing paragraphing is intentional until reader-effect and manuscript-pattern evidence supports a change. Make every boundary change an explicit approval-controlled operation.

## Initialize or Resume the Project

For every new project, read [references/workspace-and-source.md](references/workspace-and-source.md), [references/manuscript-intake.md](references/manuscript-intake.md), and [references/git-versioning.md](references/git-versioning.md) in full.

First identify:

- the author-controlled source location and exact draft;
- a distinct workspace destination;
- whether the environment supports two safe local Git repositories;
- the requested service and scope.

Use the sibling [prepare-manuscript skill](../prepare-manuscript/SKILL.md) to obtain a verified chapter-Markdown package from the designated source location. Create the invariant editorial workspace in either a local repository or the environment-provided task artifact area, then copy the selected prepared chapters into `manuscript/chapters/` without editorial changes. Keep that editable workspace separate from both the original and the neutral prepared package.

Record the shared `work.json` locator, prepared revision, chapter mapping, and source/workspace identities in the editorial manifest and project state. Maintain only `workflows.literary-editing` under the [shared status contract](../prepare-manuscript/references/preparation-contract.md#downstream-status-and-ownership). Preparation readiness does not replace any editorial approval or source-sync gate.

Read and reuse the [shared manuscript metadata](../prepare-manuscript/references/manuscript-metadata.md)
before intake. Preserve supplied values and edits; treat inferred genre, form,
audience, and description as proposals. Save explicit user corrections to the
shared record under that contract and track the fields consumed by the editorial
operation. Editorial judgments, style sheets, and proposals remain local.

For an existing project, read [references/editorial-state.md](references/editorial-state.md) in full. Verify operating mode, both location identities, current review base, manuscript paths, active job, verdicts, proposals, approvals, exports, source-sync state, and shared records before resuming.

If the necessary scope cannot be found, ask the user to provide it. A synopsis or sample cannot support a conclusive whole-manuscript verdict.

## Route the User's Intent

Infer the service when the prompt is clear. Ask only when ambiguity would materially change the level, scope, authority, or deliverable. Do not force every stage.

| Intent | Service | Required scope |
|---|---|---|
| Determine what the manuscript needs | Manuscript assessment | Complete manuscript |
| Evaluate plot, character, structure, pacing, theme, POV architecture, or narrative coherence | Developmental/structural review | Complete manuscript for a final verdict |
| Improve voice, cadence, diction, dialogue, clarity, flow, paragraph breaks, or paragraph-level effect | Line/stylistic review | Chapter or coherent passage with relevant context |
| Correct grammar, usage, punctuation, spelling, factual consistency, and house style | Copyedit review | Chapter or batch; global pass for whole-book completion |
| Evaluate representation, authenticity, permissions, factual claims, or legal-risk signals | Specialist review | Scope depends on the issue |
| Check a final formatted artifact | Proofreading | Formatted proof; whole publication for completion |
| "Edit my novel" with no usable level | Manuscript assessment | Complete manuscript |

Read only the selected service reference:

- assessment: [references/manuscript-assessment.md](references/manuscript-assessment.md)
- developmental: [references/developmental-edit.md](references/developmental-edit.md)
- line: [references/line-edit.md](references/line-edit.md)
- copyedit: [references/copyedit.md](references/copyedit.md)
- specialist: [references/specialist-reviews.md](references/specialist-reviews.md)
- proofreading and final QA: [references/proofreading.md](references/proofreading.md)

Read [references/style-and-continuity.md](references/style-and-continuity.md) whenever work uses or updates shared style or continuity state.

## Classify Readiness

Record one status before reviewing:

- `ready`: the artifact and context support the requested professional verdict.
- `ready-with-limitations`: proceed, but identify missing context, unsettled upstream work, or likely rework.
- `provisional`: the supplied scope permits only a limited finding.
- `blocked`: the necessary artifact is absent, unreadable, incomplete, or not in the required production state.

Honor a clear service request even when an earlier stage was skipped. Explain the risk without silently rerouting. Do not call an unformatted manuscript a professional proofread.

## Run the Verdict-First Lifecycle

Use [references/editorial-state.md](references/editorial-state.md) for exact schemas and persistence.

### 1. Freeze the review input

Record the job ID, operating mode, service, scope, workspace review identity, source identity, manuscript paths, brief, shared records, and limitations. Keep both source and workspace manuscript paths unchanged during review.

### 2. Analyze without editing

Build an evidence ledger. Distinguish objective defects, supported concerns, defensible choices, unresolved intent, out-of-scope observations, and downstream risks. Preserve strengths and intentional nonstandard usage.

### 3. Save and present the verdict

Include service and scope, both review identities, readiness, overall verdict, editorial-acceptance score, score rationale, strengths, prioritized evidenced findings, next actions, and proposal status. Use `ready`, `ready-with-reservations`, `revision-needed`, `not-ready-for-requested-stage`, `provisional`, or `blocked`.

The score may change after editorial conversation clarifies intent, context, audience, or an apparent inconsistency. Preserve the earlier score, issue a revised score with its reason and conversation basis, and state whether the manuscript content changed.

### 4. Save proposals when applicable

For line editing, copyediting, and proofreading, produce source-ordered before/after proposals. For developmental work, produce recommendation records rather than rewritten prose by default. Give each proposal a stable ID, review identity, exact location and current text, proposed operation or replacement, rationale, effect, dependencies, and status.

The proposal file is a reviewable diff, not an applied edit. Keep the source and workspace manuscript unchanged.

When proposals require author disposition, read [references/decision-tables.md](references/decision-tables.md) and the sibling [review-approval-sheet skill](../review-approval-sheet/SKILL.md) in full. Create the authoritative compact `decision-table.md` and synchronized `decision-table.json` interface state. Keep detailed before/after text in the proposal ledger. Validate and render the shared interactive approval sheet by default; accept direct ID responses or Markdown editing when the user prefers them or interactive rendering is unavailable.

### 5. Stop at the approval gate

Present the verdict before asking whether to apply proposals. Accept all, selected IDs, modified wording, rejection, or deferral.

Parse interactive responses against the saved JSON revision, apply the editorial decision semantics to the authoritative decision table, synchronize both review files, and quick-check allowed values, complete modification wording, dependencies, conflicts, and stale text. After review ends and the quick check succeeds, summarize the decisions and explicitly ask whether the user wants to apply the valid accepted changes now. This question is not authorization: wait for a clear affirmative apply instruction. Submitting, quick-checking, editing, or discussing either interface does not authorize manuscript changes. Persist the selected dispositions to `approvals.md` only after the separate apply instruction and before applying anything.

### 6. Revalidate and apply to the workspace

Only after explicit approval:

1. confirm the proposal's workspace and source review identities;
2. confirm the reviewed workspace manuscript has not changed;
3. confirm the exact current text still exists;
4. detect overlaps and dependencies;
5. mark invalid proposals `stale`;
6. apply only accepted or accepted-with-modification proposals to a new workspace revision;
7. update shared records only for approved decisions;
8. verify the approved-only diff and manuscript integrity.

If implementation exposes a new creative choice, stop and create a new proposal.

### 7. Deliver according to operating mode

In `dual-repository-git` mode, commit the workspace batch, revalidate the source repository, apply only the same approved changes to the source draft, verify equivalence, and create a separate source commit. If source synchronization cannot complete safely, preserve the workspace commit and produce a manual-update export.

In `artifact-workspace` mode, preserve the earlier workspace revision, generate a complete verified updated source under `exports/<job-id>/`, and ask the user to apply it manually. Never modify the source location.

### 8. Verify and report

Verify that every change maps to approval, no unapproved proposal was applied, and no text or paragraph boundary was lost, duplicated, reordered, or changed without approval. Record the resulting workspace identity, source commit or manual-update status, export identity when applicable, and cascade tasks.

## Scope and Completion Rules

- Complete assessment and developmental review only after reading the complete manuscript.
- Permit developmental chapter observations only as evidence toward a whole-book verdict.
- Permit line and copyedit work chapter by chapter with relevant context and shared state.
- Require a final manuscript-wide consistency pass before declaring the whole novel line-edited or copyedited.
- Permit proof batches, but require the complete formatted publication and final global check for completion.
- Limit specialist conclusions to the supplied and qualified scope.
- Treat major upstream changes as invalidating affected downstream verdicts and proposals.
- Distinguish workspace intervention completion from source synchronization completion.

## Operating Rules

- Diagnose against intended form, audience, genre, and reader effect; do not impose a universal beat sheet or prose norm.
- Prefer high-impact evidence over exhaustive nitpicking.
- Preserve ambiguity, voice, dialect, rhythm, fragments, repetition, and rule-breaking when intentional.
- Separate objective correctness from discretionary style.
- Query intent when alternatives create materially different effects.
- Do not promise legal, cultural, or factual certainty outside editorial competence.
- Never stage unrelated files, use broad Git staging, add a remote, or push manuscript content without explicit authorization.
