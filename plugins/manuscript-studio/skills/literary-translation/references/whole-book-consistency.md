# Whole-book consistency

Run this pass only after all chapters have approved, saved translations. Review
the complete book in source order, including front matter, against the prepared
sources, `glossary.md`, `voice.md`, and approved decisions. Check names and
terminology, forms of address, voice by character or narrator and place,
cross-chapter references, and deliberate echoes. Distinguish intentional changes
in the source from accidental drift. Quote evidence for each objective
inconsistency; do not retranslate, restyle, flatten intentional differences, or
reopen settled stylistic choices.

Keep a saved review narrative recording coverage, evidence, unresolved questions,
and next action. If the book exceeds a single context, examine it in chapter
groups and maintain a shared finding ledger, then reconcile that ledger across
the complete book before presenting the single review. Never claim coverage of
chapters not inspected.

## Workflow engine contract

When `whole_book` is true, use the supplied `consistency` context. Each entry in
`chapters` identifies the prepared source, its SHA-256, the frozen translation
snapshot (path and SHA-256), and a separate `candidate_path`. Preserve every
existing chapter output and continuity file. The pass does not run passage maps,
drafting, or chapter approval again. All paths are workspace-relative.

Save `plan_path` as JSON:

```json
{
  "chapters": {
    "chapter-1": {
      "source_sha256": "<supplied source hash>",
      "translation_sha256": "<supplied translation hash>",
      "evidence": "Concrete account of the terminology, address, voice, and references checked, including cross-chapter comparisons."
    }
  },
  "changes": [
    {
      "id": "C001",
      "chapter_id": "chapter-1",
      "source_quote": "Exact excerpt from this prepared source chapter",
      "before": "Exact English span",
      "after": "Proposed replacement",
      "reason": "Objective inconsistency, with evidence and the related chapter locations."
    }
  ]
}
```

Include every chapter exactly once in `chapters`. Use stable unique `C###` fix
IDs. Each English `before` span must occur exactly once in its frozen chapter;
include enough surrounding text to disambiguate it. Proposed spans must not
overlap; combine overlapping fixes. Both before and after must contain text.
For an insertion or deletion include an unchanged neighboring anchor.

Present all changes as one approval sheet using the shared review skill. Each
item has the same ID as its fix and these exact detail rows: `Chapter`
(`chapter_id`), `Original` (`source_quote`), `Before`, `After`, and `Reason`.
The viewer links each item to its chapter. Required resolving decisions are
`approve` and `reject`, with matching IDs and commands; feedback decisions such
as `revise` or `discuss` reopen the item and require a note. Every item must offer
both approve and reject. Use `closure_required: true` and a pending separate
final closure.

Return `needs_human_input`, gate `translation_consistency`, `binding_path` equal
to `plan_path`, `review_path` pointing to the approval sheet, and `state_path`
pointing to the review narrative. Do not apply edits yet.

The user decides every open item in one submission. Record only receipt-backed
dispositions in a new sheet revision, keeping the bound plan unchanged unless
the user requests a revised proposal. A changed plan requires renewed decisions.
Present the resolved sheet for separate final closure. A request to revise or
discuss is never permission to apply the old proposal.

If there are no findings, save the complete coverage record with `changes: []`,
state **No inconsistencies found**, and request the same gate with
`review_path: null`. The user explicitly closes it with `confirm consistency`.
Do not create a fictitious finding or an empty approval sheet.

## Applying and verifying

Only `consistency.review` authorizes application. It contains the immutable
approved plan, the closure receipt, and `approved_ids`. Read that saved plan.
For each affected chapter, copy the frozen translation into its supplied
`candidate_path` and apply exactly the approved replacements at their original
positions, working from the end of the file backwards. Preserve every other
byte, including line endings. Rejected changes must not appear in candidates.
Existing outputs remain untouched; the engine promotes candidates together only
after successful verification.

Reread every affected candidate against its complete source chapter and the
cross-chapter evidence. Verify that the proposed inconsistency is fixed, source
meaning and voice remain intact, and no text is omitted, duplicated, or changed
outside the approved replacements. Save `report_path` as JSON:

```json
{
  "chapters": {
    "chapter-1": {
      "source_sha256": "<supplied source hash>",
      "output_sha256": "<SHA-256 of candidate bytes>",
      "evidence": "Specific source comparison and cross-chapter checks performed after applying C001."
    }
  }
}
```

Include exactly the chapters with approved fixes. With no approved fixes, save
`{"chapters": {}}`. Do not invent successful checks. If verification finds a
problem, return blocked or request a revised consistency review; do not make
additional edits. Return completed with the saved narrative as `state_path`
and `output_path: null` only when all required checks succeed.

The engine checks coverage and source hashes, receipt-backed decisions, exact
candidate bytes, and verification bindings. It records each promoted fix against
its chapter and publishes those records with accepted output. Literary quality
still depends on the source comparison and human review.

## Recovery

Retry resumes this job using its saved plan, receipts, and candidates without
retranslating a chapter. Restarting any chapter invalidates the consistency
review. Once all chapters finish again, a fresh consistency attempt reviews the
current versions of the whole book. A whole-book restart retains current
completed chapter outputs and discards the pending review, not the chapters.
