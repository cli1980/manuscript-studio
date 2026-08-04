# Story Ledger Human Review Gate

Use this protocol after a manuscript-grounded story ledger passes its structural and evidence audit. The ledger remains `awaiting-confirmation` and synopsis readiness remains `not-ready` until the author explicitly disposes every review item and closes the gate.

## Review artifact

Create two synchronized artifacts:

- `query-package/static/story-ledger-review.md`: the authoritative, human-readable audit record and disposition history;
- `query-package/static/story-ledger-review.json`: the revision-bound interaction state consumed by the shared approval-sheet renderer and parser.

Bind both to:

- the ledger revision and checksum;
- the designated manuscript identity and checksum;
- the review-sheet revision;
- the creation and last-response dates.

Both files are durable package state. The Markdown record controls domain meaning and provenance; the JSON controls the current review interface and must never silently override the Markdown record. Keep their item IDs, revision, statuses, decisions, responses, and gate state synchronized. Do not keep approvals only in chat.

Read the sibling [review-approval-sheet skill](../../review-approval-sheet/SKILL.md) in full before creating, validating, rendering, or parsing the JSON interface. Use its schema and query adapter. If the sibling skill is unavailable, preserve the same IDs, revision envelope, item-level semantics, and separate final closure through the fallback in this document.

## Approval units

Convert every story proposition eligible for query or synopsis use into a single atomic approval unit. Do not ask the author to approve an entire paragraph, event record, section, or ledger at once.

Include:

- every synopsis-control-card proposition;
- every event's objective occurrence, causal link, actor objective, consequential choice, and permitted synopsis wording;
- every character-arc interpretation and time-specific relationship state;
- every identity, alias, impersonation, authority transfer, object provenance, knowledge state, and revelation;
- every ending outcome and deliberately open thread;
- every controlled claim, qualification, and prohibited overstatement;
- every `P0`-`P3` proposition selectable by a compression profile.

Exclude checksum, path, formatting, and other mechanical provenance fields unless disputed. Use stable `HG###` IDs. One unit must contain exactly one proposition and link to its ledger IDs and source locators.

## Approval-unit record

Record for every unit:

- **ID and label**
- **Proposition**
- **Originating ledger IDs**
- **Manuscript locator**
- **Claim type and confidence**
- **Permitted wording**
- **Required qualification**
- **Prohibited overstatement**
- **Downstream dependents**
- **Review status**
- **Author response and date**

Review-status values:

- `pending`
- `approved`
- `approved-with-qualification`
- `accepted-as-ambiguous`
- `correction-required`
- `invalidated`

## Present the approval sheet

Map each `HG` record to one shared-interface item. Include the proposition in `summary`; put originating ledger IDs, manuscript locator, claim type and confidence, permitted wording, required qualification, prohibited overstatement, and dependents in labeled `details`; and declare only the four query decisions below. Validate the JSON before presentation and render it as an interactive UI. The UI is the default review surface because it provides navigation, compact status, per-item decisions, required correction text, and a revision-bound batch submission without asking the author to edit Markdown directly.

The author may return dispositions for many units in one response. Each disposition must identify its `HG` ID and one of:

```text
HG001 approve
HG002 qualify: <required wording>
HG003 correct: <correction>
HG004 keep ambiguous
```

A compact response may list multiple IDs only when each ID is explicitly enumerated. Do not accept “approve all,” approval of a range without enumerated IDs, silence, package approval, positioning approval, or general approval of the ledger as disposition of individual units.

Parse returned text against the exact saved JSON revision before applying it. Then update the authoritative Markdown record, propagate domain effects into the story ledger, synchronize the JSON, increment its revision, and return a concise receipt showing each affected ID, its new status, and any invalidations. Never infer approval from UI state that was not submitted. The author may work through the sheet in any order and over any number of turns.

When interactive rendering is unavailable, present the same complete records as a readable table or downloadable artifact. For a long sheet, organize it by section and provide navigation, but do not hide or summarize away individual units. Accept the same explicitly enumerated text commands and revision-bind the response manually.

## Response handling

- `approve`: store the exact proposition and permitted wording as author-confirmed.
- `qualify`: revise the proposition and permitted wording, mark it `approved-with-qualification` only when the author's wording is unambiguous, and preserve the qualification in every dependent compression.
- `correct`: update the originating ledger records, mark affected units `correction-required` during propagation, invalidate downstream approvals, rebuild affected compression selections, and present the corrected units again for explicit disposition. A correction is not approval.
- `keep ambiguous`: retain the ambiguity, record the author's decision as `accepted-as-ambiguous`, and require qualified wording. It passes only when no synopsis profile requires a more definite answer.
- If a response addresses only part of a proposition, split the unit and mark the bundled unit `invalidated`.

Do not reopen the raw manuscript merely because the author corrects an interpretation. Reopen it only through an authorized targeted ledger refresh when the correction creates a manuscript-evidence conflict that cannot be resolved from recorded locators.

## Gate closure

After every unit has an explicit disposition and the synchronized files have been saved, render the shared interface's separate final-closure view with a compact summary containing:

- ledger and manuscript identities;
- total units;
- approved units;
- approved-with-qualification units;
- accepted ambiguities;
- corrected units;
- invalidated or pending units;
- every qualification that must survive compression.

Ask the author for final closure in a separate submission; never include it in the same response as item dispositions. Only the parsed explicit closure response may change:

- ledger status from `awaiting-confirmation` to `approved`;
- synopsis readiness from `not-ready` to `ready` or `ready-with-open-items`;
- human-review gate from `open` to `passed`.

The gate passes only when:

- no unit is `pending`, `correction-required`, or `invalidated`;
- every correction has been propagated and the resulting units explicitly disposed;
- every accepted ambiguity has safe required wording;
- the ledger matches the bound manuscript identity;
- the structural and evidence audit still passes;
- the author gives final closure confirmation.

`ready-with-open-items` is allowed only for non-synopsis optional information. An unresolved item required by a selected synopsis profile keeps that profile `not-ready`.

## Invalidation

Any manuscript-identity change invalidates the whole review. Any material ledger correction invalidates the corrected unit and every listed downstream dependent. A new synopsis profile invalidates only the previously unreviewed propositions it introduces.

When synopsis drafting reveals an unsafe or missing proposition, mark the relevant units and synopsis profile `invalidated` or `correction-required`. Do not repair the synopsis alone. Update and re-present the approval sheet for the affected units, then require final closure again.
