# Editorial State and Approval Records

## Contents

1. Durable layout
2. Project state
3. Review identity
4. Verdict and score schema
5. Proposal and approval schemas
6. Decision tables
7. Application and source delivery
8. Recovery and completion gates

Persist state so a review can stop, resume, and prove which changes were authorized. Use the same schemas in `dual-repository-git` and `artifact-workspace` modes.

## Durable layout

Use:

```text
workspace/
|-- source/
|   |-- source-record.md
|   `-- manuscript-manifest.md
|-- manuscript/
|   `-- chapters/
|-- editorial/
|   |-- editorial-brief.md
|   |-- style-sheet.md
|   |-- continuity-concordance.md
|   |-- project-state.md
|   `-- reports/
|       `-- <job-id>/
|           |-- verdict.md
|           |-- proposals.md
|           |-- decision-table.md
|           |-- decision-table.json
|           |-- approvals.md
|           `-- application-report.md
`-- exports/
    `-- <job-id>/
```

Create a stable job ID from service, scope, and sequence, for example `line-ch04-001`. Do not reuse an ID for a different review identity or scope.

## Project state

Record:

- operating mode: `dual-repository-git` or `artifact-workspace`;
- source location identity and update permissions;
- workspace location identity;
- source repository root, baseline, import commit, and tracked draft paths in Git mode;
- workspace repository root, baseline, and current commit in Git mode;
- source and workspace fingerprints and workspace revision IDs in artifact mode;
- active job ID, service, and scope;
- phase: `intake`, `preparing-source`, `ready`, `reviewing`, `verdict-presented`, `awaiting-approval`, `applying-workspace`, `verifying-workspace`, `syncing-source`, `awaiting-manual-source-update`, `completed`, `paused`, or `blocked`; interpret legacy `normalizing` as `preparing-source`, delegated to the shared preparation skill;
- reviewed source and workspace identities;
- manuscript paths;
- verdict, proposal, decision-table Markdown, decision-table JSON, approval, report, and export paths;
- decision-table interface revision, synchronization status, and quick-check status;
- current proposal batch and unresolved query;
- resulting workspace identity;
- resulting source commit, `source-sync-pending`, or manual-update status;
- next action, stale downstream jobs, and cascade tasks.

Update state before each approval request, after every workspace application, and after source synchronization or export delivery.

## Review identity

Include the shared prepared `work.json` locator, prepared revision, and stable
chapter-ID-to-editorial-file mapping alongside the two identities below.
Do not edit the prepared chapters when applying an editorial decision.

Use one schema with mode-specific values:

```markdown
- Operating mode: dual-repository-git | artifact-workspace
- Workspace review identity: <full commit SHA | revision ID and fingerprint>
- Source import identity: <full commit SHA | artifact identity and fingerprint>
- Workspace manuscript paths: <paths>
- Source draft path or identity: <path or attachment identity>
```

Every verdict and proposal must carry both identities. In artifact mode, include enough size, modification-time, checksum, and chapter-checksum information to detect changes. Do not substitute a chat message for durable identity.

## Verdict schema

Save `verdict.md` before presenting it. Include:

```markdown
# Verdict: <service and scope>

- Job: <job-id>
- Operating mode: dual-repository-git | artifact-workspace
- Workspace review identity: <commit or fingerprinted revision>
- Source import identity: <commit or fingerprint>
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

Interpret the score only within the declared service, scope, and readiness:

- `1 - not accepted`: fundamental problems or insufficient evidence prevent acceptance at this editorial level.
- `2 - major revision`: substantial work is needed before acceptance.
- `3 - conditional acceptance`: the manuscript is viable, with material issues or decisions unresolved.
- `4 - accepted with limited reservations`: the manuscript substantially meets the requested editorial standard, with bounded remaining work.
- `5 - accepted`: the reviewed scope meets the requested editorial standard without material reservations.

Give each finding a stable ID, location, evidence, effect, priority, and classification. Use `required`, `recommended`, `optional`, or `query`. Do not average finding counts or imply marketability.

## Clarification and score revision

The author may clarify intent, context, audience, factual background, or a defensible choice. Reassess only affected findings. Manuscript change is not required.

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

Do not treat agreement as evidence or raise a score merely to reward agreement.

## Proposal schema

Save proposals in source order. For every textual change record:

```markdown
## LE-001 - <short label>

- Status: pending
- Priority: required | recommended | optional | query
- Workspace review identity: <commit or fingerprinted revision>
- Source import identity: <commit or fingerprint>
- Location: <chapter file + paragraph/anchor>
- Current: <exact text>
- Proposed: <exact replacement, insertion, deletion, or move>
- Rationale: <why>
- Effect: <reader, voice, correctness, or consistency effect>
- Dependencies: <IDs or none>
```

The exact before/after records constitute the proposed diff. Keep both the workspace manuscript and source unchanged during review.

For a `paragraph-break` proposal, additionally record classification, operation, left and right anchors, current and proposed boundary states, whether wording is unchanged, reader-effect evidence, and manuscript-pattern evidence. Never rely on invisible whitespace alone.

Allowed statuses are `pending`, `accepted`, `accepted-with-modification`, `rejected`, `deferred`, `withdrawn`, `stale`, `applied-workspace`, `applied-source`, `exported`, and `verified`.

## Decision tables and approvals

Read [decision-tables.md](decision-tables.md) and the sibling [review-approval-sheet skill](../../review-approval-sheet/SKILL.md) in full when proposals need user disposition. Keep `decision-table.md` authoritative for editorial dispositions and `decision-table.json` synchronized as the interactive interface state. Parse responses against the saved interface revision before updating either file. A quick check validates IDs, values, modified wording, dependencies, overlaps, and staleness. It does not authorize changes or replace `approvals.md`.

A submitted modification or proposal revision is not manuscript-change authorization. Application remains a separate explicit instruction, after which the selected valid dispositions are copied to `approvals.md` and revalidated.

Record the user's disposition before application:

```markdown
## <proposal ID>

- Disposition: accepted | accepted-with-modification | rejected | deferred
- Approved wording or operation: <exact value when modified>
- User instruction: <faithful concise record>
- Recorded at: <timestamp or session marker>
```

Discussion, questions, "continue," approval of a verdict, or approval of a general direction are not proposal approval. Partial approval is valid.

## Application and source delivery

Before workspace application, revalidate both review identities, exact current text, dependencies, and overlaps. Mark invalid records `stale`.

After workspace application, save `application-report.md` with:

- source and workspace review identities;
- resulting workspace commit or revision identity;
- applied proposal IDs and approved wording;
- rejected, deferred, pending, stale, and withdrawn IDs left unapplied;
- style or continuity updates;
- approved-only diff and integrity verification;
- operating-mode delivery result;
- source commit and verification in Git mode, or export path and manual-update status in artifact mode;
- cascade tasks and invalidated jobs.

In Git mode, workspace application and source synchronization are separate phases. A job may be `source-sync-pending` after the workspace commit succeeds.

In artifact mode, create a complete verified updated source under `exports/<job-id>/`, preserve the earlier workspace revision, and set `awaiting-manual-source-update`. Never claim the source changed until the user confirms manual application.

## Recovery and completion gates

On resume, reread project state, source record, manifest, active verdict, proposals, approvals, relevant shared records, export state, and both repository statuses or artifact fingerprints. Reconstruct from durable state when chat conflicts with files.

A review completes when the required scope was read, verdict and score were saved, applicable proposals were saved, and neither workspace manuscript nor source changed.

A workspace intervention completes when every workspace change has approval, the correct review base was used, a new workspace commit or preserved artifact revision exists, and the approved-only diff and integrity were verified.

Source delivery completes when either:

- Git mode: the approved source update is verified and committed; or
- artifact mode: a verified updated-source export is delivered and the workflow clearly states that the user must update the source manually.

Whole-book completion additionally requires every component exactly once and in order, the service-specific global pass, consistent shared records, no blocking unresolved item, and a final verdict bound to the exact assembled workspace and source identities. Do not equate source-delivery completion with user confirmation of manual source replacement.
