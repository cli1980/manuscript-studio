---
name: review-approval-sheet
description: Validate, render, present inline, and process revision-bound approval sheets through a reusable interactive review interface with explicit per-item decisions, required notes, batch submission, reopened-item handling, and separate final closure. Use when another workflow has many proposals, claims, translation choices, passage boundaries, diffs, or other stable-ID items that require human disposition; when Markdown editing is cumbersome; or when Codex must re-present corrected, invalidated, stale, or unresolved approval items without weakening the originating workflow's authority rules.
---

# Review Approval Sheet

Provide a common human-review surface without taking ownership of domain meaning or application authority. Treat the originating skill as the authority for item content, dependencies, invalidation, persistence, and downstream changes.

## Core Contract

1. Use structured JSON conforming to [references/approval-sheet-schema.md](references/approval-sheet-schema.md) as the interface state.
2. Preserve the originating workflow's Markdown or other durable audit record. JSON does not replace required domain records.
3. Require one explicit item ID and one allowed decision command for every disposition. Reject blanket approval, unenumerated ranges, silence, and general approval.
4. Bind every rendered interface and generated payload to `sheet_id` and `revision`. Reject a response for a stale or different revision. For a disposition-only text fallback, the originating skill must explicitly bind the response to the active saved revision before parsing it.
5. Require a note when the selected decision declares `requires_note: true`.
6. Treat decisions whose effect is `reopen` as feedback requiring domain propagation, never as approval of the resulting replacement.
7. Do not apply manuscript, translation, ledger, query-package, or source changes. Return validated dispositions to the originating skill.
8. Keep final closure separate. Offer it only from a newly rendered sheet whose saved domain state contains no unresolved items.
9. Present every successfully rendered fragment as an inline Codex visualization. A filesystem path or Markdown link does not count as presenting the review interface.

## Workflow

### 1. Build the sheet

Read [references/approval-sheet-schema.md](references/approval-sheet-schema.md) in full. Have the originating skill map stable items, labeled details, decisions, dependencies, statuses, bindings, and gate state into JSON.

Use [references/domain-adapters.md](references/domain-adapters.md) for the applicable domain. Keep source excerpts, current text, proposed text, evidence, qualifications, and prohibited wording in labeled `details`.

### 2. Validate before presentation

Run:

```text
python scripts/approval_review.py validate <sheet.json>
```

Fix every reported schema or state error. Do not render an invalid sheet.

### 3. Render deterministically

Write a new lowercase-hyphenated HTML fragment into the active thread's visualization directory or another allowed artifact location:

```text
python scripts/approval_review.py render <sheet.json> <output.html>
```

Use the generated fragment as-is. Do not hand-recreate the interface, edit its embedded state, add network requests, or convert it into a standalone webpage.

The renderer supports arbitrary review order, batch submission, item-specific decisions, note requirements, identity binding, reopened-item views, and a distinct final-closure view.

Immediately present the generated fragment in the same response with this directive on its own line:

```text
::codex-inline-vis{file="<basename>.html"}
```

Place the fragment in the active thread visualization directory and use only its basename in the directive. Do not use a Markdown link as the normal presentation path. When the user asks to review, continue, go through the list, or show remaining items, validate and rerender the latest saved revision and emit the inline directive in that response.

### 4. Parse returned dispositions

Save or isolate the user's returned payload, then run:

```text
python scripts/approval_review.py parse <sheet.json> <response.txt>
```

Use `--output <parsed.json>` for a durable machine-readable receipt. Reject unknown or duplicate IDs, disallowed decisions, missing notes, responses for resolved items, altered envelope text, blanket approvals, and revision mismatches.

### 5. Return authority to the domain

Give the validated receipt to the originating skill. That skill must persist the response, interpret qualifications and corrections, update domain content, propagate dependencies, revalidate bindings, determine resolved/reopened state, create the next revision, and authorize downstream application only under its own rules.

Render only resulting unresolved items when incremental follow-up is valid. Never make the user re-review unaffected resolved items.

Present every new revision inline using the same directive contract; do not merely report that a replacement HTML file exists.

### 6. Handle final closure

After the originating skill saves every item as resolved in a new revision, render that revision again. When `gate.closure_required` is true and `gate.final_closure` is `pending`, the renderer presents final closure instead of item controls. The originating skill alone may pass its gate.

## Fallback

Use a text fallback only when the inline visualization surface is unavailable or the inline directive fails. Present a readable table or copyable lines using the same IDs, decisions, notes, identity, and revision. A link to a local HTML file by itself is not a fallback because it does not expose the interaction in conversation. Run the same parser on the response. Interface limitations never weaken the gate.

## Validation

After changing the schema, renderer, parser, or template, run:

```text
python scripts/test_approval_review.py
```

Also run the standard skill validator. Keep generated fragments under 2 MB and verify their JavaScript syntax when Node.js is available.
