# Whole-work DOCX preparation: docx-novel-001

This case uses the supplied `遗落梦境与记忆尽头.docx` from
`evals/fixtures/manuscripts/novel-sample/`.

The generic [skill evaluator](../../../check_preparation.py) reads this case's
configuration; it contains no knowledge of this novel or its DOCX styles.
See [evaluation instructions](../../../PREPARATION_EVALUATION.md).

## Scope and expected structure

Prepare the whole work, retaining cover information and the table of contents as
one leading front-matter unit, followed by:

- 19 numbered chapters, from `一、新年` through `十九、末日`;
- `尾声`, as a narrative chapter;
- `附录：遗落的传说` and `后记`, as back matter.

This draft convention yields 23 Markdown units. The public case instructions
specify TOC and paragraph-style handling. The original DOCX has 22 TOC entries
and 22 `ChineseHeading` body headings; the former must not create duplicate chapters.
The cover author's name has Word Choice/Fallback representations that must be
read once. Embedded font files are not output manuscript assets. The footnote
and endnote XML parts contain separators, not authored notes.

## Fixed source ground truth

[`ground-truth.json`](ground-truth.json) is the fixed source baseline, pinned by
SHA-256 in `case.json`. The readable inventory is in
[`GROUND_TRUTH.md`](GROUND_TRUTH.md). It records all section boundaries, exact
non-whitespace character and paragraph counts, and text/paragraph fingerprints.

The DOCX contains **19 numbered chapters, one epilogue, one appendix, and one
afterword**: 22 body sections and 23 prepared units including combined front
matter. Its main document contains **114,063 non-whitespace characters**, including
cover and TOC. The body including headings contains **113,889**. Narrative prose
alone (the 19 chapters and epilogue, excluding their headings) contains **109,607**.

Counts include punctuation, numerals, Latin letters, and Chinese characters;
they exclude Unicode whitespace, XML/Markdown markup, field instructions, fonts,
and running headers/footers. The author in Choice/Fallback counts once. These
are measured source-text counts, not Word's cached application statistics.

Two independent XML traversals (different parsers and opposite Choice/Fallback
selection) agree on every logical paragraph's text, style, and order. The TOC
matches the body's heading sequence. The one-time establishment script is not
retained. Use the reusable evaluator to verify the source hash, frozen baseline
binding, and reference consistency without regenerating ground truth:

```text
python evals/check_preparation.py --case docx-novel-001 --check-reference
```

Source changes require a separately versioned case. The evaluator checks
reference Markdown against this frozen baseline before checking any candidate,
then reports candidate character counts and content fingerprints independently
of its self-reported hashes.

## Markdown presentation reference status

**Source text and structure are established. Markdown presentation review remains pending.**
`build_draft_reference.py` authors candidate reference Markdown from direct OOXML
inspection and the public case conventions. It is a fixture-authoring aid, not
a production DOCX extraction adapter. Do not use it to create the candidate
package being evaluated.

The reference's source-text counts and ordered-paragraph fingerprints have been
checked against the frozen ground truth. Before presentation approval, review
cover/TOC rendering, diary/quotation formatting, meaningful scene breaks, and inline
emphasis. The draft does not certify font-based or
inline formatting fidelity. Adjust the reference/profile if review finds a
problem, update the reference file hashes, and only then record the actual
reference reviewer and date.

The first 19 chapter-number strings are Chinese numerals as displayed in the
source. Unit titles in this reference retain the full source heading, including
that number. Generated work/chapter IDs are not fixed by the case.

The supplied source SHA-256 is pinned in `case.json`. Rebuilding a reference for
a modified source requires an explicit case update. The builder refuses to
regenerate a reference whose review status is already approved.

## What this fixture does not establish

This DOCX is not a test of scanned-document OCR, body tables, real footnotes,
tracked changes, or image extraction. Add separate cases with independently
reviewed references for those capabilities; the generic checker can evaluate
supported reference Markdown from different source formats.

No preparation agent has been evaluated merely by building or validating this
reference. No source manuscript is modified by either authoring or checking.
