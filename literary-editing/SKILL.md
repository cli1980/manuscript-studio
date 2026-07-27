---
name: literary-editing
description: Review and edit book-length literary manuscripts through professional assessment, developmental review, line editing, copyediting, specialist review, proofreading, and final QA. Use when Codex needs to initialize a fiction, memoir, or narrative nonfiction editing project; route a whole manuscript or selected chapters to the right service; produce verdicts with scoped 1-5 editorial-acceptance scores; revise scores after author clarification without requiring manuscript changes; propose diffs without changing the draft; run first-class paragraph-break checks during line editing; present and quick-check editable proposal decision tables; apply only explicitly approved proposals; preserve voice and editorial state; manage approved revisions through local Git; redirect no-Git setup outputs to task artifacts; or fall back safely when table writing is unavailable.
---

# Literary Editing

Route each request to the appropriate professional editorial service. Review first, produce a verdict, and keep the manuscript unchanged until the user explicitly approves identified proposals.

## Governing Contract

Follow these rules in every service:

1. Treat the author or authorized user as the creative decision-maker.
2. Preserve the received source artifact. Normalize extraction errors only when the artifact makes the intended text objectively clear.
3. Use one canonical Markdown chapter set under local Git rather than duplicated draft directories when Git is available.
4. Bind every verdict and proposal to the exact reviewed commit SHA. If Git is unavailable or setup fails, use the verdict-and-score-only fallback below.
5. Do not edit manuscript text while reviewing, diagnosing, writing a verdict, or generating proposals.
6. Apply only proposal IDs the user explicitly accepts or modifies. General approval, discussion, questions, or “continue” do not authorize edits.
7. Permit partial approval. Leave rejected, deferred, and pending proposals unapplied.
8. Revalidate approved proposals against the reviewed commit and current text. Mark invalid proposals `stale`; never guess how to rebase them.
9. Create a new commit for each approved edit batch. Do not amend, rewrite, reset, or otherwise alter earlier manuscript history.
10. Keep each service within scope. Flag other editorial levels separately instead of silently performing them.
11. Do not claim whole-book completion from chapter passes without the required manuscript-wide synthesis or consistency check.
12. Give every verdict an editorial-acceptance score from 1 to 5, scoped to the requested service and reviewed material. Do not present it as a publication, sales, or market forecast.
13. Treat an editable decision table as a review interface, not manuscript-change authorization. A quick check validates decisions only; application still requires a separate explicit user instruction.
14. If Git is unusable during project setup, stop writing generated outputs into the manuscript project. Redirect all permitted fallback outputs to the current task's artifact area and remain `verdict-score-only`.
15. Treat paragraph breaks as a first-class line-edit dimension. Presume existing paragraphing is intentional until reader-effect and manuscript-pattern evidence supports a change. Review boundary placement separately from wording, and make every proposed boundary change an explicit approval-controlled operation.

## Initialize or Resume the Project

For a new project, an unsplit artifact, or missing normalized chapters, manifest, editorial state, or local Git, read [references/manuscript-intake.md](references/manuscript-intake.md), [references/git-versioning.md](references/git-versioning.md), and [references/task-artifact-fallback.md](references/task-artifact-fallback.md) in full. Complete initialization before editorial review when Git works. If Git is unavailable or setup fails, enter `verdict-score-only` mode and redirect all generated setup and review outputs to the task artifact area. Do not create project-local proposals, apply edits, or modify the manuscript.

For an existing project, read [references/editorial-state.md](references/editorial-state.md) in full. Verify the repository root, current commit, manuscript paths, active job, verdicts, proposals, approvals, and shared records before resuming.

If the necessary scope cannot be found, ask the user to provide it. A synopsis or sample cannot support a conclusive whole-manuscript verdict.

## Route the User’s Intent

Infer the service when the prompt is clear. Ask only when ambiguity would materially change the level, scope, authority, or deliverable. Do not force every stage.

| Intent | Service | Required scope |
|---|---|---|
| Determine what the manuscript needs | Manuscript assessment | Complete manuscript |
| Evaluate plot, character, structure, pacing, theme, POV architecture, or narrative coherence | Developmental/structural review | Complete manuscript for a final verdict |
| Improve voice, cadence, diction, dialogue, clarity, flow, paragraph breaks, or paragraph-level effect | Line/stylistic review | Chapter or coherent passage with relevant context |
| Correct grammar, usage, punctuation, spelling, factual consistency, and house style | Copyedit review | Chapter or batch; global pass for whole-book completion |
| Evaluate representation, authenticity, permissions, factual claims, or legal-risk signals | Specialist review | Scope depends on the issue |
| Check a final formatted artifact | Proofreading | Formatted proof; whole publication for completion |
| “Edit my novel” with no usable level | Manuscript assessment | Complete manuscript |

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

Record the job ID, service, scope, reviewed commit SHA, manuscript paths, brief, shared records, and limitations. In `verdict-score-only` mode, record a stable artifact fingerprint or precise file identity instead of a commit SHA and persist it only in the task artifact area. Keep manuscript paths unchanged during review.

### 2. Analyze without editing

Build an evidence ledger. Distinguish objective defects, supported concerns, defensible choices, unresolved intent, out-of-scope observations, and downstream risks. Preserve strengths and intentional nonstandard usage.

### 3. Save and present the verdict

Include service and scope, reviewed SHA or fallback artifact identity, readiness, overall verdict, editorial-acceptance score, score rationale, strengths, prioritized evidenced findings, next actions, and proposal status. Use `ready`, `ready-with-reservations`, `revision-needed`, `not-ready-for-requested-stage`, `provisional`, or `blocked`.

In `verdict-score-only` mode, save every generated verdict, score revision, diagnostic, manifest, or normalized review artifact to the task artifact area described in [references/task-artifact-fallback.md](references/task-artifact-fallback.md), never to the manuscript project.

The score may change after editorial conversation clarifies intent, context, audience, or an apparent inconsistency. A manuscript edit is not required. Preserve the earlier score, issue a revised score with its reason and conversation basis, and state whether the manuscript content changed. Clarification may improve, reduce, or leave the score unchanged; never raise it merely to reward agreement.

### 4. Save proposals when applicable

For line editing, copyediting, and proofreading, produce source-ordered before/after proposals. For developmental work, produce recommendation records rather than rewritten prose by default. Give each proposal a stable ID, reviewed SHA, exact location and current text, proposed operation or replacement, rationale, effect, dependencies, and status.

The proposal file is a reviewable diff, not an applied edit. Keep manuscript files unchanged.

When proposals require author disposition, read [references/decision-tables.md](references/decision-tables.md) in full. Create a compact editable `decision-table.md` when the project is writable, unless the user prefers direct ID responses. Keep detailed before/after text in the proposal ledger.

Skip this and all later intervention steps in `verdict-score-only` mode.

### 5. Stop at the approval gate

Present the verdict before asking whether to apply proposals. Accept all, selected IDs, modified wording, rejection, or deferral.

If the decision-table path is used, quick-check the edited table for allowed values, complete modification wording, dependencies, conflicts, and stale text. Update its agent-check fields when writable. Quick-checking, editing, or discussing the table does not authorize manuscript changes. Require a separate explicit apply instruction, then persist the selected dispositions to `approvals.md` before applying anything.

If table creation or update fails because of permissions, sandboxing, or format restrictions, use the chat or structured-block fallback in [references/decision-tables.md](references/decision-tables.md). Do not apply when approval provenance itself cannot be saved.

### 6. Revalidate and apply

Only after explicit approval:

1. confirm the proposal’s reviewed SHA;
2. confirm no manuscript path changed since that commit;
3. confirm the exact current text still exists;
4. detect overlaps and dependencies;
5. mark invalid proposals `stale`;
6. apply only accepted or accepted-with-modification proposals;
7. update shared records only for approved decisions;
8. commit the approved batch with its approval and application records.

If implementation exposes a new creative choice, stop and create a new proposal.

### 7. Verify

Compare the resulting commit with the reviewed commit. Verify that every manuscript change maps to approval, no unapproved proposal was applied, and no text or paragraph boundary was lost, duplicated, reordered, or changed without approval. Record the resulting SHA and cascade tasks.

## Scope and Completion Rules

- Complete assessment and developmental review only after reading the complete manuscript.
- Permit developmental chapter observations only as evidence toward a whole-book verdict.
- Permit line and copyedit work chapter by chapter with relevant context and shared state.
- Require a final manuscript-wide consistency pass before declaring the whole novel line-edited or copyedited.
- Permit proof batches, but require the complete formatted publication and final global check for completion.
- Limit specialist conclusions to the supplied and qualified scope.
- Treat major upstream changes as invalidating affected downstream verdicts and proposals.

## Operating Rules

- Diagnose against intended form, audience, genre, and reader effect; do not impose a universal beat sheet or prose norm.
- Prefer high-impact evidence over exhaustive nitpicking.
- Preserve ambiguity, voice, dialect, rhythm, fragments, repetition, and rule-breaking when intentional.
- Separate objective correctness from discretionary style.
- Query intent when alternatives create materially different effects.
- Do not promise legal, cultural, or factual certainty outside editorial competence.
- Never stage unrelated files, use broad Git staging, add a remote, or push manuscript content without explicit authorization.
