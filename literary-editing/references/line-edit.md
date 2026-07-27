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
- paragraph boundaries, paragraph movement, transitions, and scene-level flow;
- exposition, action, interiority, and description balance;
- clarity versus productive ambiguity;
- local pacing and emotional rhythm.

Protect deliberate fragments, dialect, code-switching, idiolect, repetition, ambiguity, and unconventional grammar when they serve the work. Do not homogenize the prose into a generic house voice.

## First-class paragraph-break pass

After the initial read for effect, run a dedicated paragraph-boundary pass over the complete selected unit. Inspect every existing break and every plausible missing break rather than noticing paragraphing only when another sentence-level issue draws attention to it.

Presume the manuscript's existing paragraphing is intentional. The burden of proof rests on the proposed change. Do not recommend a break merely because a paragraph is long, short, visually dense, or unlike a generic house preference. Compare analogous passages in the selected unit and, when available, elsewhere in the manuscript. Preserve the boundary when its reader effect is defensible and it fits the manuscript's prose or structural pattern.

Evaluate:

- paragraph unity: whether each paragraph carries a coherent action, image, thought, or rhetorical movement;
- dialogue control: new speakers, interrupted speech, attribution, and deliberately continuous dialogue;
- shifts in time, place, viewpoint, narrative distance, subject, or mode;
- action and reaction sequencing, including whether a break sharpens or falsely separates causality;
- emphasis, reveal, suspense, comic timing, emotional turn, and white-space rhythm;
- overlong blocks that bury distinct movements;
- overfragmentation that produces unintended staccato, false emphasis, or visual mannerism;
- consistency with the work's established paragraphing without flattening purposeful exceptions.

Classify every paragraph-boundary finding as `clarity`, `attribution`, `narrative-shift`, `pacing`, `emphasis`, `unity`, `consistency`, or `intentional-exception`. Use `intentional-exception` to document a nonstandard but defensible boundary that should be retained; do not create a change proposal for it unless unresolved intent requires a query.

Distinguish a manuscript paragraph break from a scene or section break and from automatic typesetting line or page wraps. A paragraph-break pass may propose a narrative paragraph boundary; it must not silently create a scene division or prescribe production reflow.

Include a `Paragraph-break assessment` in the verdict even when no changes are proposed. Summarize strengths, recurring boundary patterns, intentional exceptions to preserve, and the number of paragraph-break proposals.

## Verdict and proposal diff

Return the verdict before editing. Summarize the unit's strengths, recurring patterns, priorities, and any questions about intent. Then create a source-ordered proposal ledger using `LE-001`, `LE-002`, and so on.

Each proposal must contain:

- exact location and current text;
- proposed replacement text;
- priority: `required`, `recommended`, `optional`, or `query`;
- rationale tied to the intended reader effect;
- dependencies or continuity impact;
- status.

For every paragraph-boundary change, use category `paragraph-break` and record:

- classification: `clarity`, `attribution`, `narrative-shift`, `pacing`, `emphasis`, `unity`, or `consistency`;
- operation: `insert-break`, `remove-break`, or `move-break`;
- exact left and right text anchors;
- current boundary state and proposed boundary state;
- whether wording remains unchanged;
- reader-effect evidence: the specific clarity, attribution, rhythm, pacing, emphasis, or narrative consequence;
- manuscript-pattern evidence: the analogous local or manuscript-wide pattern supporting the change, or a precise explanation of why this boundary is an unintended deviation;
- interaction with adjacent textual proposals.

Both evidence fields are required. Paragraph length or visual density alone is not sufficient evidence. If manuscript-pattern evidence is unavailable or the effect remains plausibly intentional, retain the boundary or raise a query instead of proposing a change.

Do not encode a boundary change only as invisible whitespace inside a replacement block. Label the operation explicitly. Keep wording changes under a separate proposal ID unless the boundary and wording are inseparable; if combined, provide the complete deterministic result and explain why.

Quote enough exact text to make the change deterministic without replacing unreviewed surrounding prose. Offer alternatives only when they create materially different effects, and explain the tradeoff. If authorial intent cannot be inferred safely, ask a query instead of manufacturing certainty.

Do not alter manuscript files while producing the verdict or proposal diff.

## Approval and application

The author may approve individual IDs, ranges, or a clearly identified batch. Partial approval is valid. When the author wants an editable checklist, use [decision-tables.md](decision-tables.md), quick-check the completed table without editing the manuscript, and require a separate explicit apply instruction. Use its chat or structured-block fallback if the table cannot be written.

Revalidate the reviewed commit SHA and exact current text before applying. For paragraph-break proposals, also revalidate both anchors and the recorded boundary state; if any changed, mark the proposal stale and regenerate it.

Apply only approved proposal IDs, update any affected style or continuity records, write an application report, and create a distinct Git commit. Do not silently include nearby cleanup.

## Completion

Before completing a line-edit unit, compare its paragraph-boundary map with the reviewed commit. Verify that every inserted, removed, or moved break maps to an approved proposal and that no other boundary changed.

Work in manageable units. After all intended units are processed, perform a whole-book consistency pass for voice drift, repeated mannerisms, character differentiation, paragraphing drift, and cross-chapter effects. This pass should confirm coherence, not reopen every optional stylistic preference indefinitely.
