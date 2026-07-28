# Editable Decision Tables

Use an editable decision table to make proposal review efficient without weakening the approval gate. The detailed proposal ledger remains authoritative for source text, proposed wording, rationale, and dependencies. The table is a compact decision interface.

## Durable artifact

When proposals require author disposition and the project is writable, create:

```text
editorial/reports/<job-id>/decision-table.md
```

Bind it to the same job ID, workspace review identity, and source import identity as `proposals.md`. Keep rows in proposal order.

Use:

```markdown
# Decision Table: <service and scope>

- Job: <job-id>
- Workspace review identity: <commit or fingerprinted revision>
- Source import identity: <commit or fingerprint>
- Proposal ledger: <path>
- Quick-check status: unchecked

| ID | Priority | Short description | Decision | Comment or modification reference | Agent check |
|---|---|---|---|---|---|
| LE-001 | recommended | Tighten the opening |  |  | unchecked |
```

Allowed user decisions are:

- blank: undecided;
- `accept`;
- `accept-with-modification`;
- `reject`;
- `defer`.

Reserve the `Agent check` column for the agent. Allowed values are `unchecked`, `valid`, `needs-input`, `stale`, and `conflict`.

Keep comments short enough for a Markdown cell. When exact modified wording is long, multiline, or contains table-breaking characters, place it below the table:

````markdown
## Modification blocks

### LE-004

```text
<exact approved replacement or operation>
```
````

Put `See LE-004 modification block` in that row's comment cell. Do not place the complete before/after proposal in the table.

## Offer interactive review

Immediately after creating the decision table, ask whether the user wants to go through it now or skip the dialogue for later. If the user chooses interactive review, present one unresolved proposal at a time with its current text, proposed change, rationale or effect, and allowed decisions; record each answer before continuing. If the user skips, preserve the unresolved table and stop at the approval gate.

## Quick check

When the user asks to quick-check, validate the decision table without changing the manuscript:

1. confirm the job ID, both review identities, and proposal-ledger path;
2. confirm that every expected proposal ID appears exactly once and no unknown ID appears;
3. accept only the allowed decision values;
4. require deterministic wording or an exact operation for `accept-with-modification`;
5. treat comments on `accept` as notes, not textual modifications;
6. allow comments on `reject` and `defer` without turning them into counterproposals;
7. for a `paragraph-break` proposal, validate an allowed classification, exact left and right anchors, current boundary state, one deterministic operation (`insert-break`, `remove-break`, or `move-break`), reader-effect evidence, and manuscript-pattern evidence; reject `intentional-exception` as a change proposal;
8. detect unresolved queries, missing dependencies, overlapping accepted edits, and decisions made stale by manuscript changes;
9. update `Agent check` for each row and the table's quick-check status when writable;
10. return a concise count of valid, undecided, needs-input, stale, and conflicting rows.

A quick check does not authorize manuscript changes. Do not create `approvals.md`, apply text, or treat “quick-check,” “review this table,” or the user's act of editing the table as an application command.

After a successful quick check, require a separate explicit instruction such as `Apply all rows marked valid` or `Apply valid rows LE-001 through LE-010`. At that point, translate the selected table decisions into `approvals.md`, faithfully preserving comments and exact modified wording, then run normal revalidation and application.

## Fallback when the table cannot be written

If filesystem permissions, sandboxing, format limitations, or the working environment prevent creation or update of `decision-table.md`:

1. do not weaken or skip the approval gate;
2. present the same compact rows in chat when a Markdown table remains usable;
3. otherwise provide a copyable structured block:

```text
LE-001 | decision= | comment=
LE-002 | decision= | comment=
```

4. accept the user's completed rows or ID mappings in chat;
5. perform the same quick-check rules and return the validation summary in chat;
6. if project files are writable, persist selected dispositions to `approvals.md` only after the user explicitly instructs application;
7. if approval provenance cannot be written at all, remain validation-only and do not modify the manuscript.

Record the fallback and its cause in project state or the eventual approval record. A failed table write does not change the operating mode when durable approval and application records remain writable.