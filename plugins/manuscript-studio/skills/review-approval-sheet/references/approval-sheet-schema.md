# Approval Sheet JSON Contract

## Contents

1. Purpose
2. Root object
3. Decision definitions
4. Review items
5. Gate and presentation behavior
6. Submission payloads
7. Invariants
8. Minimal example

## Purpose

Use UTF-8 JSON as the interface contract between a domain skill and the shared review surface. The domain's Markdown ledger, decision table, review state, or approval record remains authoritative.

## Root object

Required fields:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | Exactly `1.0` |
| `sheet_id` | string | Stable ID using letters, numbers, period, underscore, colon, or hyphen |
| `revision` | string | Nonempty immutable revision for this state |
| `title` | string | Human-facing title |
| `bindings` | array | At least one object with string `label` and `value` |
| `decisions` | array | At least two decision definitions |
| `items` | array | At least one unique stable-ID item |
| `gate` | object | Gate status and closure policy |
| `presentation` | object | Display mode and labels |
| `submission` | object | Handoff instruction and rules |

Optional `metadata` may contain domain provenance. The renderer does not interpret it.

## Decision definitions

Each decision contains:

| Field | Type | Rule |
|---|---|---|
| `id` | string | Unique lowercase machine ID |
| `command` | string | Exact command, without colon or newline |
| `label` | string | Button label |
| `requires_note` | boolean | Whether a note is mandatory |
| `effect` | string | `resolve`, `reopen`, or `clear` |

Use `reopen` for corrections or revisions whose replacement must be propagated and reviewed again. Domain sheets normally omit `clear` because the renderer supplies its own Clear action.

## Review items

Each item contains:

| Field | Type | Rule |
|---|---|---|
| `id` | string | Unique stable ID |
| `summary` | string | Atomic proposition or concise proposal |
| `details` | array | One or more string `label`/`value` rows |
| `status` | string | `pending`, `resolved`, or `reopened` |
| `status_label` | string | Domain-facing status |
| `allowed_decisions` | array | One or more root decision IDs |
| `dependencies` | array | Downstream item or domain-record IDs |
| `response` | object or null | Current resolved response |

Optional fields are `section`, `reopened_reason`, and `metadata`. A reopened item requires `reopened_reason`.

A response contains `decision`, `note`, and `date`. A resolved item requires a response using an allowed `resolve` decision and any mandatory note. Pending and reopened items must have `response: null`; preserve history in the domain record or `metadata.history`.

## Gate and presentation behavior

`gate` requires:

- `status`: domain gate status;
- `closure_required`: boolean;
- `final_closure`: `not-required`, `pending`, or `confirmed`;
- `ready_state`: domain readiness label.

`presentation` requires `mode` (`all` or `open-only`), `note_label`, `note_placeholder`, and `submit_label`.

`open-only` displays pending and reopened items. `all` also displays resolved items as locked context.

Final closure appears only when all saved items are resolved, closure is required, and `final_closure` is pending. Browser-local decisions never unlock closure.

## Submission payloads

`submission` requires `instruction`, `rules`, `closure_command`, and `closure_label`.

Item payload:

```text
<instruction>
Approval sheet: <sheet_id>
Revision: <revision>
<rule sentence>

<ITEM-ID> <decision command>
<ITEM-ID> <decision command>: <required note>
```

Closure payload:

```text
<instruction>
Approval sheet: <sheet_id>
Revision: <revision>
<rule sentence>

<closure_command>
```

The parser accepts the generated envelope or disposition-only lines. It rejects unknown prose, altered identity lines, blanket approval, and mixed closure/item payloads.

## Invariants

- Every disposition explicitly enumerates one stable ID.
- Duplicate IDs and commands are invalid.
- A `reopen` decision never resolves its replacement.
- A stale revision is invalid even when item IDs match.
- The shared layer never edits domain content or passes a domain gate.
- Resolved items are not resubmitted.
- Final closure is separate.

## Minimal example

```json
{
  "schema_version": "1.0",
  "sheet_id": "line-chapter-01",
  "revision": "rev-3",
  "title": "Line-edit decisions",
  "bindings": [{"label": "Review base", "value": "abc123"}],
  "decisions": [
    {"id": "accept", "command": "accept", "label": "Accept", "requires_note": false, "effect": "resolve"},
    {"id": "modify", "command": "accept with modification", "label": "Modify", "requires_note": true, "effect": "resolve"},
    {"id": "reject", "command": "reject", "label": "Reject", "requires_note": false, "effect": "resolve"},
    {"id": "revise", "command": "revise proposal", "label": "Revise proposal", "requires_note": true, "effect": "reopen"}
  ],
  "items": [{
    "id": "LE-001",
    "summary": "Tighten the first sentence.",
    "details": [
      {"label": "Current text", "value": "It was a very cold morning."},
      {"label": "Proposed text", "value": "The morning was bitterly cold."}
    ],
    "status": "pending",
    "status_label": "Pending",
    "allowed_decisions": ["accept", "modify", "reject", "revise"],
    "dependencies": [],
    "response": null
  }],
  "gate": {
    "status": "awaiting-approval",
    "closure_required": false,
    "final_closure": "not-required",
    "ready_state": "not-ready"
  },
  "presentation": {
    "mode": "open-only",
    "note_label": "Modification or comment",
    "note_placeholder": "Required for modification or revision",
    "submit_label": "Send reviewed proposals to Codex"
  },
  "submission": {
    "instruction": "Apply these explicit proposal dispositions to the bound decision table.",
    "rules": ["Do not apply manuscript changes until I separately authorize application."],
    "closure_command": "confirm final closure",
    "closure_label": "Confirm final closure"
  }
}
```
