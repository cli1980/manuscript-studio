# Copyedit

Use this workflow for correctness, consistency, internal continuity, and editorial queries after the manuscript's structure and prose are reasonably stable.

## Scope and readiness

Copyediting may proceed by chapter or controlled batch. A whole-book completion claim requires a final global pass across the complete manuscript, style sheet, and continuity concordance.

Bind the review to the Git commit SHA and exact manuscript paths. Load the current approved style and continuity records from `style-and-continuity.md`. If structural revision is still active, return `not-ready` or sharply limit the scope.

## Editorial lens

Check:

- grammar, punctuation, spelling, usage, and syntax;
- consistency of capitalization, hyphenation, compounds, numbers, dates, and typography;
- names, titles, terminology, dialogue treatment, and language variety;
- chronology, locations, physical details, character knowledge, and world rules;
- factual claims, plausibility, and items needing verification;
- missing words, duplicated text, internal references, notes, and completeness;
- conformity with the approved project style while preserving intentional exceptions.

Treat dialect, voice-driven grammar, fragments, and purposeful inconsistency as editorial questions, not automatic errors. Never invent a fact to resolve a contradiction.

## Verdict and proposal diff

Return a verdict and pattern summary before proposing changes. Create a source-ordered ledger using `CE-001`, `CE-002`, and so on. Each record must include the exact location, current text, proposed text, classification, priority, rationale or authority, dependencies, and status.

Use `query` when the correction depends on authorial intent or an unverified fact. Even apparently objective corrections remain proposals until approved under this skill's contract. Record proposed additions to the style sheet separately as `proposed`; do not make them project rules before approval.

Do not edit manuscript files during review.

## Approval and application

Accept approval at proposal, range, or named-batch granularity. Revalidate both the Git commit SHA and exact current text. Apply only accepted IDs, update approved style and continuity records, write the application report, and create a distinct Git commit.

If an approved change exposes a new issue, record a new proposal rather than expanding the approved change silently.

## Completion

After chapter or batch work, run a global consistency pass across all manuscript files. Reconcile names, terminology, chronology, typography, approved exceptions, unresolved queries, and style-sheet entries before marking the copyedit `whole-book-complete`.
