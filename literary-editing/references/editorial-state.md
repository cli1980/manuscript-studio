# Editorial State and Approval Records

## Contents

1. Durable layout
2. Project state
3. Verdict and score schema
4. Clarification and score revision
5. Proposal and approval schemas
6. Editable decision tables
7. Application and recovery
8. Completion gates

Persist state so a review can stop, resume, and prove which changes were authorized.

## Durable layout

Use:

```text
editorial/
|-- editorial-brief.md
|-- style-sheet.md
|-- continuity-concordance.md
|-- project-state.md
`-- reports/
    `-- <job-id>/
        |-- verdict.md
        |-- proposals.md
        |-- decision-table.md
        |-- approvals.md
        `-- application-report.md
```

Create a stable job ID from service, scope, and sequence, for example `line-ch04-001`. Do not reuse an ID for a different reviewed commit or scope.

## Project state

Record:

- repository root and baseline tag/SHA;
- operating mode: `git-managed` or `verdict-score-only`;
- current manuscript commit SHA;
- active job ID, service, and scope;
- phase: `intake`, `normalizing`, `ready`, `reviewing`, `verdict-presented`, `awaiting-approval`, `applying`, `verifying`, `completed`, `paused`, or `blocked`;
- reviewed commit SHA and manuscript paths;
- fallback artifact identity or fingerprint when no reviewed commit exists;
- verdict, proposal, and decision-table paths;
- decision-table quick-check status or fallback mode when used;
- current proposal batch and unresolved query;
- resulting commit SHA when applied;
- next action;
- stale downstream jobs and cascade tasks.

Update state before each approval request and after every applied batch.

## Verdict schema

Save `verdict.md` before presenting it. Include:

```markdown
# Verdict: <service and scope>

- Job: <job-id>
- Reviewed commit: <full SHA>
- Reviewed artifact: <file identity or fingerprint; use only when Git is unavailable>
- Readiness: ready | ready-with-limitations | provisional | blocked
- Overall verdict: ready | ready-with-reservations | revision-needed | not-ready-for-requested-stage | provisional | blocked
- Editorial-acceptance score: 1 | 2 | 3 | 4 | 5
- Score revision: <sequence number>
- Score basis: manuscript-text | author-clarification | mixed
- Manuscript changed since prior score: yes | no | first-score
- Proposal status: none | pending | partially-resolved | resolved

## Limitations
## Strengths to preserve
## Prioritized findings
## Recommended next actions
```

Omit whichever of `Reviewed commit` or `Reviewed artifact` does not apply.

Interpret the score only within the declared service, scope, and readiness:

- `1 — not accepted`: fundamental problems or insufficient evidence prevent acceptance at this editorial level.
- `2 — major revision`: substantial work is needed before acceptance.
- `3 — conditional acceptance`: the manuscript is viable, with material issues or decisions still unresolved.
- `4 — accepted with limited reservations`: the manuscript substantially meets the requested editorial standard, with bounded remaining work.
- `5 — accepted`: the reviewed scope meets the requested editorial standard without material reservations.

Give each finding a stable ID, location, evidence, effect, priority, and classification. Use `required`, `recommended`, `optional`, or `query` as editorial priority. Derive the acceptance score from the verdict as a whole; do not average finding counts or imply marketability.

## Clarification and score revision

The author may clarify intent, context, audience, factual background, or the purpose of a defensible choice. Reassess only findings affected by that clarification. Manuscript change is not required for a score revision.

Preserve the prior score and append:

```markdown
## Score revision <n>

- Previous score: <1-5>
- Revised score: <1-5>
- Manuscript changed: yes | no
- Clarification basis: <faithful concise record>
- Findings affected: <IDs or none>
- Rationale: <why the score changed or remained>
```

Clarification may improve, reduce, or leave the score unchanged. Do not treat author agreement as evidence, erase an unresolved textual effect, or require a change solely to justify a higher score.

## Proposal schema

Save proposals in source order. For every textual change record:

```markdown
## LE-001 — <short label>

- Status: pending
- Priority: required | recommended | optional | query
- Reviewed commit: <full SHA>
- Location: <chapter file + paragraph/anchor>
- Current: <exact text>
- Proposed: <exact replacement, insertion, deletion, or move>
- Rationale: <why>
- Effect: <reader, voice, correctness, or consistency effect>
- Dependencies: <IDs or none>
```

The exact before/after records constitute the proposed diff. Keep the manuscript unchanged. If alternatives create materially different effects, record them under one query rather than pretending they are equivalent edits.

Allowed statuses are `pending`, `accepted`, `accepted-with-modification`, `rejected`, `deferred`, `withdrawn`, `stale`, `applied`, and `verified`.

## Editable decision tables

Read [decision-tables.md](decision-tables.md) in full when proposals need user disposition. Use `decision-table.md` as an editable checklist linked to the authoritative proposal ledger. The table may collect `accept`, `accept-with-modification`, `reject`, `defer`, or blank decisions plus comments.

A quick check validates IDs, values, modified wording, dependencies, overlaps, and staleness. It does not authorize manuscript changes or replace `approvals.md`. Require a later explicit apply instruction and convert only the selected, valid rows into approval records.

If the table cannot be written, use the defined chat or structured-block fallback. Record the fallback cause. Do not apply if the durable approval record cannot be written.

## Approval schema

Record the user’s disposition before application:

```markdown
## <proposal ID>

- Disposition: accepted | accepted-with-modification | rejected | deferred
- Approved wording or operation: <exact value when modified>
- User instruction: <faithful concise record>
- Recorded at: <timestamp or session marker>
```

Discussion, questions, “continue,” approval of a verdict, or approval of a general direction are not proposal approval. Partial approval is valid. Do not force the user to decide unrelated proposals as one all-or-nothing block.

An edited or quick-checked decision table is not, by itself, an application instruction. When the user explicitly instructs application of validated rows, translate those decisions into this approval schema before revalidation.

## Application and recovery

Before application, revalidate the reviewed SHA, manuscript path diff, exact current text, dependencies, and overlaps. Mark invalid records `stale` and return them for review.

After application, save `application-report.md` with:

- reviewed and resulting SHAs;
- applied proposal IDs and approved wording;
- rejected, deferred, pending, stale, and withdrawn IDs left unapplied;
- style or continuity updates;
- approved-only diff verification;
- integrity verification;
- cascade tasks and invalidated jobs.

On resume, reread project state, the active job’s verdict, proposals, approvals, the relevant shared records, and Git status. Reconstruct from durable state when chat conflicts with files. Never reopen a settled item unless the user explicitly revises it or a later approved change invalidates it.

## Completion gates

A review completes when the required scope was read, the verdict and acceptance score were saved or delivered, applicable proposals were saved, and no manuscript text changed. Approval is not required.

In `verdict-score-only` mode, the verdict and score are the only deliverables. Do not create proposals, approval records, application reports, or manuscript changes. Intervention cannot begin until Git is available, a clean baseline exists, and the manuscript is reviewed again against that commit.

An intervention completes when every manuscript change has approval, the correct base was used, a new commit exists, the approved-only diff and text integrity were verified, shared state was updated, and the result was delivered.

Whole-book completion additionally requires every component exactly once and in order, the service-specific global pass, consistent shared records, no blocking unresolved item, and a final verdict bound to the exact assembled manuscript commit.
