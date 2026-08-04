# Editable Decision Tables

Use an editable decision table to make proposal review efficient without weakening the approval gate. The detailed proposal ledger remains authoritative for source text, proposed wording, rationale, and dependencies. The table is a compact decision interface.

## Durable artifact

When proposals require author disposition and the project is writable, create two synchronized review files:

```text
editorial/reports/<job-id>/decision-table.md
editorial/reports/<job-id>/decision-table.json
```

`decision-table.md` is the authoritative compact editorial disposition record. `decision-table.json` is the revision-bound interface state consumed by the shared renderer and parser. Bind both to the same job ID, workspace review identity, source import identity, proposal-ledger identity, and interface revision. Keep rows in proposal order and synchronize IDs, statuses, user responses, and quick-check results after every submission. Never let the interface JSON silently override the proposal ledger or Markdown table.

Read the sibling [review-approval-sheet skill](../../review-approval-sheet/SKILL.md) in full before creating or processing the JSON. Use its editing adapter: `accept`, `accept with modification`, `reject`, `defer`, and `revise proposal`. A modification or revision requires a note; `revise proposal` reopens the item and is not acceptance.

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

## Interactive review

Map each proposal to one shared-interface item. Put the short description in `summary`; put exact current text, proposed text or operation, rationale, effect, priority, dependencies, and source location in labeled `details`. Validate the JSON, then render the interactive sheet by default. It may show all proposals with compact navigation and submit any explicitly decided subset; unresolved items remain pending.

Parse the returned revision-bound envelope before changing records. Apply this editing skill's dependency, overlap, identity, and staleness rules; then update the Markdown table, JSON state, and quick-check fields and increment the interface revision. A request to revise a proposal changes the proposal ledger, reopens that proposal and affected dependents, and requires a new disposition. It does not accept the replacement.

After the final proposal is answered, quick-check the completed decisions and summarize the result. If one or more accepted or accepted-with-modification rows are valid, explicitly ask whether the user wants to apply those changes now. Do not stop silently, and do not treat the question itself as authorization. If the user asks to postpone review, preserve the unresolved files and stop at the approval gate.

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

A quick check does not authorize manuscript changes. Do not create `approvals.md`, apply text, or treat “quick-check,” “review this table,” an interactive-sheet submission, or the user's act of editing the table as an application command.

After a successful quick check, prompt for a separate explicit instruction, for example: `Would you like me to apply all valid accepted rows now?` A clear affirmative response to that prompt may authorize the stated scope; otherwise require an instruction such as `Apply all rows marked valid` or `Apply valid rows LE-001 through LE-010`. At that point, translate the selected table decisions into `approvals.md`, faithfully preserving comments and exact modified wording, then run normal revalidation and application.

## Fallback when the table cannot be written

If filesystem permissions, sandboxing, format limitations, missing shared-skill support, or the working environment prevent creation or update of either review interface:

1. do not weaken or skip the approval gate;
2. prefer the remaining durable interface; otherwise present the same compact rows in chat when a Markdown table remains usable;
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
