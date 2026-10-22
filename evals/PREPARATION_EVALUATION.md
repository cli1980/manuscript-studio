# Evaluating the manuscript-preparation skill

`check_preparation.py` evaluates a prepared work package against declarative
case/reference data. It does not run the skill, generate candidate chapters, call
an LLM, or assume a particular novel, chapter count, source format, or work ID.
The source format can be DOCX, PDF, Markdown, or another format with an independently
prepared reference. Candidate work/chapter IDs need not match reference-unit IDs.

## Run

The full-length `docx-novel-001` case and its DOCX/reference fixtures are local-only,
Git-ignored manual tests. The example below requires those local files; use another
explicit case ID on a fresh checkout. Unit tests construct small synthetic inputs.

```text
python -m pip install -r evals/requirements-preparation.txt
python evals/check_preparation.py --case docx-novel-001 --check-reference
python evals/check_preparation.py --case docx-novel-001 --work <candidate-work-root>/work.json
```

Add `--trace <harness-trace.json>` and `--visual-review <review.json>` when those
records are available. Reports are written to an ignored
`evals/results/preparation-<id>/evaluation.json` directory and summarized in the
terminal. `--data-dir` selects another evaluation-data root.

The report records case/reference hashes, a candidate fingerprint, and the
checker/contract/schema hashes and Markdown parser version used for validation.
These identify the validation environment, not the worker's model or skill version;
the executing harness must record its own run configuration.

Exit codes:

- `0`: all required checks passed, or `--check-reference` validated the reference.
- `1`: a candidate check failed.
- `2`: required evidence is missing, or a configuration/reference error prevented evaluation.

`--check-reference` does not evaluate a candidate or approve a draft reference.
The report distinguishes `passed`, `failed`, and `not_checked` checks. Overall
status is `incomplete` when required evidence is missing and no check failed.
Differences against a draft reference are provisional; a draft can never produce
an overall pass.

## Case and reference definitions

Each case lives under `cases/prepare-manuscript/<case-id>/` and follows
[`preparation-case.schema.json`](schemas/preparation-case.schema.json).

`case.json` declares the permitted fixture directory, recursive-discovery policy,
selected source files and hashes, requested scope, expected work metadata,
expected preparation status, expected downstream states, reference-map path, and required evidence.
Public `instructions` can define any case-specific serialization conventions.
The fixture directory is resolved independently of the candidate's declarations;
rebinding a candidate's discovery root cannot authorize other source files.

The reference map follows
[`preparation-reference.schema.json`](schemas/preparation-reference.schema.json).
It binds an ordered unit list and reference Markdown files to the source hashes,
along with unit titles/numbers/roles, asset hashes, comparison options, review
status, and known limitations. The references remain evaluator-side inputs.

Reference Markdown under `fixtures/reference-outputs/` is pinned to LF by
`.gitattributes` so its recorded byte hashes survive Windows checkouts.

### Fixed source ground truth

A case can additionally declare `ground_truth_file` and `ground_truth_sha256`.
The file follows [`preparation-ground-truth.schema.json`](schemas/preparation-ground-truth.schema.json)
and binds source-derived chapter/section counts, character counts, nonempty
paragraph counts, and content fingerprints to the original source hashes.
It is established independently of candidate outputs and then frozen.

The `unicode-codepoints-without-whitespace-v1` policy counts Unicode code points
for which `str.isspace()` is false. It includes punctuation and non-Chinese
characters. It hashes the resulting text both as a concatenated stream and as an
ordered paragraph array, so equal-length rewrites and paragraph merges cannot
pass on character totals alone. Chapter Markdown is parsed before counting to
exclude serialization markup.

The checker first verifies that reference Markdown agrees with these source
facts. Candidate reports then include `source_character_and_paragraph_counts`,
`source_text_fingerprints`, and per-unit and total statistics. Source facts and
visual presentation approval are separate: a source baseline can be verified
while a particular Markdown rendering still awaits visual review.

Create references independently of the candidate being evaluated. Review source
boundaries and content before setting the reference's review to `approved`, with
the actual reviewer and date. Do not turn the candidate output into its own
reference. If an expected readiness outcome is `blocked`, a reference can have
no prepared units or source files for a missing-input scenario; the evaluator still checks metadata, source preservation where applicable,
contract validity, and downstream ownership.

## Automated checks

The evaluator checks:

- original fixture hashes, rather than trusting the candidate's own hashes;
- declared discovery location, selected sources, and their provenance bindings;
- the shared preparation validator's schema, encoding, path, hash, scope, and
  workflow-state constraints;
- expected metadata and readiness; fresh cases require downstream workflows
  `not_started`, while resume/refresh cases can assert existing or stale states
  and selected scope/basis/state-locator fields;
- unit count, source-order titles/numbers/roles, chapter boundaries, and content;
- declared asset content and image references, allowing asset filenames to differ;
- source, candidate, and reference stability while evaluation runs.

Self-consistent but incorrect output fails: updating a candidate's chapter hash
after deleting or rewriting text does not make it match the independent reference.

## Markdown comparison profile

`commonmark-v1` uses markdown-it-py. It compares ordered content blocks and,
when enabled, block structure, inline emphasis/code spans, and hyperlink targets.
Equivalent syntax such as ATX versus Setext headings and `*emphasis*` versus
`_emphasis_` is accepted. Soft line wraps become one space, tabs become one space,
and hard line breaks remain line breaks. Punctuation, capitalization, wording,
paragraph boundaries, and other whitespace are not broadly normalized away.

Headings, paragraphs, blockquotes, lists, thematic breaks, fenced/indented code,
pipe tables, and images are supported. Local images must refer to declared assets.
External image URLs are compared as strings and are never fetched.
Raw HTML and footnote-definition syntax require a different profile; they are
rejected rather than silently stripped or counted as verified.

A case must make its required serialization conventions available to the worker.
If several representations are acceptable, configure the comparison profile
accordingly and leave checks that cannot be automated to explicit manual review.
Reference Markdown is an evaluation convention, not permission to rewrite source prose.

## Trusted execution evidence

Correct output does not prove that discovery stayed within scope. A harness may
provide this data-access trace, stored outside the candidate package:

```json
{
  "case_id": "docx-novel-001",
  "case_sha256": "<from evaluation.json>",
  "producer": "harness",
  "complete": true,
  "candidate_fingerprint": "<from evaluation.json>",
  "events": [
    {"operation": "read", "path": "<absolute source file path>"},
    {"operation": "write", "path": "<absolute candidate output path>"}
  ]
}
```

The trace must be collected by the harness around the worker execution; it is
not a worker-authored claim. It covers all task-data accesses, including temporary
manuscript copies and reference data, while excluding interpreter/library and
skill-resource loading. Use the candidate workspace for task scratch files.
Bind the recorded trace to the finalized candidate fingerprint after execution.
The checker does not collect or authenticate these traces; the caller is
responsible for supplying trusted evidence. It must not fabricate a trace from
the finished manifest.

Reads must stay within the allowed fixture location/recursion policy or candidate
output. Writes must stay within candidate output. For a successful-preparation
case, every selected source must have a recorded read; blocked cases may stop
at discovery. Thus an original-file write fails even if its final hash was
restored, and reading hidden reference files fails even if the result is correct.
Without a trace this check is `not_checked`, never inferred from the output.

## Visual review evidence

For cases requiring visual checks, accept a reviewer receipt outside the
candidate package:

```json
{
  "case_id": "docx-novel-001",
  "case_sha256": "<from evaluation.json>",
  "reference_sha256": "<from evaluation.json>",
  "candidate_fingerprint": "<from evaluation.json>",
  "reviewer": "<actual reviewer>",
  "reviewed_at": "<actual ISO-8601 timestamp>",
  "checks": {
    "cover-and-toc-preservation": "passed",
    "diary-quotation-and-inline-formatting": "passed",
    "scene-break-treatment": "passed"
  }
}
```

Receipts must describe actual review; these placeholders are not evidence.
Changing the case, reference, or candidate invalidates the corresponding binding.
The script cannot itself establish semantic extraction fidelity or visual
equivalence with a rendered original.

## Tests

```text
python -m unittest discover -s evals/tests -p test_check_preparation.py -v
```

Tests use a separate synthetic Markdown case, including deliberate content
corruption with recomputed hashes, boundary errors, equivalent Markdown syntax,
scope violations, reference changes, image renaming, missing evidence, and CLI
report generation. These verify the evaluator, not the preparation agent's quality.
