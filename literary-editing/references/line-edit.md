# Line Edit

Use this workflow to improve prose at the sentence and paragraph level while preserving the author's voice and the manuscript's intended effects.

## Scope and readiness

A line edit may be performed on a chapter, scene, or coherent passage when enough surrounding context is available. Label local work `chapter-complete` or `batch-complete`; reserve `whole-book-complete` for a final cross-manuscript pass.

Confirm that major structural decisions are sufficiently stable. Bind the review to the Git commit SHA and exact manuscript paths. Read the entire selected unit once for effect before proposing sentence changes.

## Editorial lens

Evaluate:

- voice, tone, register, and narrative distance;
- sentence shape, syntax, cadence, emphasis, and variation;
- diction, imagery, specificity, cliché, and unintended repetition;
- dialogue, subtext, attribution, and character differentiation;
- point-of-view control and psychic distance;
- paragraph movement, transitions, and scene-level flow;
- exposition, action, interiority, and description balance;
- clarity versus productive ambiguity;
- local pacing and emotional rhythm.

Protect deliberate fragments, dialect, code-switching, idiolect, repetition, ambiguity, and unconventional grammar when they serve the work. Do not homogenize the prose into a generic house voice.

## Verdict and proposal diff

Return the verdict before editing. Summarize the unit's strengths, recurring patterns, priorities, and any questions about intent. Then create a source-ordered proposal ledger using `LE-001`, `LE-002`, and so on.

Each proposal must contain:

- exact location and current text;
- proposed replacement text;
- priority: `required`, `recommended`, `optional`, or `query`;
- rationale tied to the intended reader effect;
- dependencies or continuity impact;
- status.

Quote enough exact text to make the change deterministic without replacing unreviewed surrounding prose. Offer alternatives only when they create materially different effects, and explain the tradeoff. If authorial intent cannot be inferred safely, ask a query instead of manufacturing certainty.

Do not alter manuscript files while producing the verdict or proposal diff.

## Approval and application

The author may approve individual IDs, ranges, or a clearly identified batch. Partial approval is valid. Revalidate the reviewed commit SHA and exact current text before applying; if either changed, mark the proposal stale and regenerate it.

Apply only approved proposal IDs, update any affected style or continuity records, write an application report, and create a distinct Git commit. Do not silently include nearby cleanup.

## Completion

Work in manageable units. After all intended units are processed, perform a whole-book consistency pass for voice drift, repeated mannerisms, character differentiation, and cross-chapter effects. This pass should confirm coherence, not reopen every optional stylistic preference indefinitely.
