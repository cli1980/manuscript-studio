# End-to-end translation workflow task

Translate the complete supplied Chinese short story, 《刺秦》, into natural
US English using the repository's `prepare-manuscript`, `literary-translation`,
and `review-approval-sheet` skills.

The designated source is
`workflow/tests/fixtures/short-story-ciqing/刺秦.docx`. Prepare the whole
document, preserving its title, numbered sections 1–10, paragraph order, and
dialogue. Identify real structural units from the source; do not split by token
limits or treat the title as an additional narrative chapter.

Read complete units before passage drafting. Initialize and maintain the glossary
and scoped voice record, obtain passage-map decisions and separate closure,
perform the complete two-path drafting process, and conduct source-grounded
fidelity/prose review. Preserve the skill's passage-continuation and chapter
sanity gates, including explicit approval when no textual changes are proposed.

Preserve the contemporary narrator's register and the embedded historical voices.
Keep aliases and distinct characters straight, preserve local uncertainty and
the sequence in which information becomes available, and retain the narrator's
revisions of the embedded story. Do not repair the fiction to match external
historical accounts, add explanations, or smooth out apparently contradictory
versions of an event. Resolve substantive choices through review rather than
inventing a preferred interpretation.

Deliver only approved English manuscript text, glossary/voice records, and the
workflow's required provenance. Keep analysis, review instructions, and decision
ledgers out of the English manuscript. Do not add a separate general line-editing
pass after translation.

The supplied source is complete for this task. Author identity and an English
title are not supplied; do not invent the author or assume a fixed English title.
If DOCX extraction is unavailable, report the blocker rather than substituting
the quality evaluator's extracted text and claiming successful DOCX ingestion.

This is the workflow test's task specification. The E2E launcher pins and appends
it to the current operation's skill-contract prompt; it does not override that
operation's scope or approval gates. The lower-level CLI does not load this file
automatically. The separate translation-quality case receives the resulting
English text as a candidate, not the DOCX, run directory, or this prompt.
