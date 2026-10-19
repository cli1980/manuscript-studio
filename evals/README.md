# Skill evaluations

Evaluate how an agent performs when using the five distributed Manuscript Studio
skills. Load skill instructions and resources from
[`../plugins/manuscript-studio/skills/`](../plugins/manuscript-studio/skills/);
do not maintain evaluation copies of the skills.

This directory provides a shared-source translation case format and a
[ground-truth review server](server/README.md) for human judges to inspect prepared
cases and record scores, comments, and issue annotations. Passages and case
metadata are read-only; dataset preparation happens outside the server.
The server validates supported records and references when reading and saving
them. The [blind judge runner](run_judge.py) prepares requests or calls a configured
Chat Completions API and compares predictions with human scores. Dataset export
and fine-tuning are not implemented.

The first [literary-translation placeholder](cases/literary-translation/zh-en-000001/README.md)
provides a draft structure for a Chinese passage, its English translation, and
separate human judgments. Its Chinese source and English translation are
populated, and submitted human reviews are preserved separately. Remaining
dataset metadata must be completed before inclusion in training or evaluation datasets.

## Layout

```text
evals/
├── README.md
├── cases/
│   ├── literary-editing/
│   ├── literary-translation/
│   ├── literary-agent-querying/
│   ├── format-manuscript/
│   └── review-approval-sheet/
├── fixtures/
│   ├── manuscripts/
│   └── reference-outputs/
├── rubrics/
├── server/
└── results/
```

- `cases/<skill>/`: scenarios for one skill, including prompts, input references,
  any follow-up author responses, expected behavior, and checks.
- `fixtures/manuscripts/`: small synthetic or appropriately licensed source texts
  and supporting inputs. Record provenance and permission to redistribute.
- `fixtures/reference-outputs/`: reviewed examples and expected artifacts.
  Keep these separate from newly generated run outputs.
- `rubrics/`: shared and skill-specific scoring criteria, with guidance for
  human review and any future automated judges.
- `server/`: the local web interface, restricted data repository, authentication,
  and tests. See its README for native and isolated-container startup.
- `results/`: generated outputs, scores, traces, and run metadata. Contents are
  Git-ignored except for `.gitkeep`, which preserves the directory in checkouts.

The `.gitkeep` files preserve otherwise empty directories; they are not cases
or fixtures. Evaluation files are outside the plugin and standalone installer's
source directory and are not installed with the skills.

## First evaluations

Start with successful workflows, missing-input scenarios, and approval boundaries
for each skill. Evaluate output quality as well as whether the agent follows the
workflow, pauses for required author decisions, and respects source-editing and
external-action boundaries.

Extend the case format when adding automated evaluations for more skills.
Keep model and execution settings explicit. Record the skill Git commit, whether
the checkout has local changes, the case and rubric versions, model identifier,
execution configuration, and run time with each result.

Existing Python unit tests remain in their current locations and continue to
validate deterministic utilities. See the
[development instructions](../README.md#development-and-verification) for their
commands.

## Run the translation judge

The runner uses Python 3.10 or newer and the standard library. The model receives
exactly the [judge skill](judges/literary-translation-judge/SKILL.md) as the system
message and a user message containing only `source_text` and `translation_text`.
Both texts are resolved from the case definition's file references; the shared
passage reference is checked for consistency.

The scoring criteria are embedded in the judge skill. The runner verifies that
this versioned snapshot matches the human rubric file before evaluation; update
both together when changing criteria. The human rubric file and case metadata
are used locally for validation, not appended as separate model inputs.

It never loads the production `literary-translation` skill. No case context,
translation brief, provenance, case identifiers, human scores, human comments,
or reviewer identity are sent to the model. The request has no tools, repository
access, or conversation history. Model settings and the output JSON schema
control generation without adding case information.

Prepare the current set without credentials or network access:

```text
python evals/run_judge.py --all --smoke-test --prepare-only
```

Preparation does not read `judgments.jsonl`. Inspect the generated `request.json`
before running a model. To include the intended model in the prepared request,
also supply `--model`.

For live scoring, configure `OPENAI_API_KEY` in your environment and select a
model supporting Chat Completions JSON-schema structured output:

```text
python evals/run_judge.py --case zh-en-000001 --reviewer lin-shaw --model YOUR_MODEL --smoke-test
```

`--case` can be repeated, or use `--all`. `--reviewer` chooses the human reference
for comparison and is never part of the API request. To use another compatible
provider, set `OPENAI_BASE_URL` or pass `--base-url` (including its API prefix,
such as `/v1`). Use `--api-key-env` to name a different credential environment
variable. The runner does not store the credential or follow API redirects.
HTTPS is required except for loopback test endpoints.

Temperature is omitted by default; use `--temperature` only when supported by
your model. `--timeout` defaults to 60 seconds. Record the model ID carefully:
results include the requested and returned model identifiers and the actual
request parameters.

Normal benchmark runs require case status `ready` and permitted usage rights for
both texts. The current sample still needs setup, so it requires explicit
`--smoke-test`. This marks the output exploratory and `benchmark_eligible: false`;
it does not change case metadata or turn one example into a reliability benchmark.

The run directory is created under the ignored `evals/results/` tree:

```text
results/judge-<timestamp>-<id>/
|-- run.json
|-- summary.json                  # Model runs only
`-- <case-id>/
    |-- request.json
    |-- response.json             # Parsed API response, even if scoring is invalid
    |-- prediction.json           # Validated prediction
    `-- comparison.json           # Selected human reference and score discrepancies
```

After saving a valid prediction, the runner checks that its input files have not
changed, then reads human judgments locally. It selects the last applicable
non-superseded record for the requested reviewer and matching case, source, and
rubric versions. A current draft blocks comparison rather than falling back to
an obsolete completed score. The comparison records the selected judgment ID and
the human-history file hash. The run records hashes of the source, translation,
metadata, judge skill, rubric, and request.

Each scored field reports `prediction - human`, absolute error, and exact
agreement. The summary reports sample count, mean signed error, mean absolute
error, and exact-agreement rate separately for overall score and each dimension.
Live runs also print a per-case human-versus-LLM score table, the judge's rationale,
and aggregate metrics to the terminal. Prepare-only runs explicitly report that
no model was called and no evaluation result exists.
Missing human dimensions are excluded, not treated as zero. Invalid model output
or missing valid human references are recorded as failures and excluded from
metrics, with failed-case counts reported explicitly. The script exits with 1 for
case failures and 2 for configuration or preflight errors.

Run the runner's tests:

```text
python -B -m unittest discover -s evals/tests -v
```

The tests use temporary copies of the current sample and a deterministic local
HTTP fixture. They verify request isolation, real case/history compatibility,
strict output validation, reference selection, discrepancy calculations, and
failure reporting. Fixture scores are software tests, not LLM quality measurements.

### Judge instruction design

The judge skill's linguistic, cultural, and communicative checks draw on
Qingqing Wu's [“A Study on Translator’s Subjectivity in Julia Lovell’s Translation
from the Perspective of Eco-translatology”](https://www.ijassjournal.com/2023/V6I8/4146663547.pdf)
(2023, pp. 220–228; particularly pp. 223–226). These are qualitative inspection
prompts within the existing scoring dimensions, not a new scale or a validated
LLM evaluation method. The paper and its translation examples are not sent to
the model. It discusses the same work as our first sample, so testing a change
on that sample is a development check, not independent evidence of improvement.

## Shared translation sources

Each translation case pairs a shared source passage with one candidate
translation and its own human judgments:

```text
evals/
|-- fixtures/manuscripts/
|   `-- work-001/passage-001/
|       |-- passage.json
|       `-- source.zh.txt
`-- cases/literary-translation/
    `-- zh-en-000001/
        |-- README.md
        |-- case.json
        |-- translation.en.txt
        `-- judgments.jsonl
```

`passage.json` owns work information, source provenance and usage rights, shared
context, source language, and source revision. `case.json` owns the candidate
translation, target language, translation provenance and usage rights, any
translation-specific brief, and case revision. Human scores remain separate
in `judgments.jsonl`.

All file references use forward slashes and resolve relative to the JSON file
containing them, not the shell's working directory. In a case, `source_file` must
resolve to the same file as the referenced passage metadata's `source_file`.
The case's `group_id`, `passage_id`, and `source_language` must match the shared
metadata, and `source_revision` must match its `revision`. Each judgment must
match its case ID and revision and the referenced passage ID and source revision.

To add an alternative translation, create a new case ID and translation file
while retaining the same source references and identifiers. Start fresh human
judgments for that candidate. Different target languages can also reference the
same source; declare the appropriate `target_language` and use a suitable rubric.
The current fidelity, English-naturalness, and literary-voice dimensions are a
draft for Chinese-to-English cases, not a universal rubric for every language.

## Revisions and dataset splits

- Keep `group_id` stable for the originating work and `passage_id` stable for a
  passage. Assign them before adding alternate translations.
- After any completed judgment references a source revision, preserve its text
  and assessment-relevant metadata. Put a corrected source and its metadata in a
  new location, for example `passage-001/revisions/2/`, increment the passage
  revision, and leave the old files intact.
- Cases using the old source remain valid records of that revision. To assess
  the corrected source, create a new case or preserve the old case revision
  before updating its source references and incrementing its revision. Never
  relabel an existing score as an assessment of the new source.
- Likewise, preserve a rated case's translation and judgments before revising its
  translation or brief. Use a new case ID for an independently compared candidate.
- Keep all cases from an originating work in one training, validation, or test
  split. This includes alternative translations, target languages, and revisions.
  Record split assignments in a separate versioned dataset manifest when building
  datasets; do not assign splits independently per candidate.
- Pass only the case-referenced source and translation plus the judge skill
  (with its embedded rubric) to the judge. Human scores are targets and are read
  only after prediction; context and translator/model identities are withheld.
  Store model predictions in `results/`, not as human judgments.

The review server enforces supported source references, score ranges, revision
bindings on new judgments, and conflicts when a case changes during review.
Score corrections append records linked by `supersedes_judgment_id`; old judgments
remain available for inspection. An exporter should select the current,
non-superseded completed assessments rather than treat every historical record
as an independent label.

One server serves one judge, across multiple browser sessions. Server assessments
stay in a shared temporary workspace until **Submit changes**
is confirmed. Submission publishes only judgment records for existing cases,
checks for conflicting changes to the originals, and preserves earlier ratings.
Restarting the service discards any unsubmitted changes. Unchanged saves add no
new judgment records; real edits retain earlier versions as history.

Dataset export and split enforcement are not implemented. Pending judgments,
placeholder cases, and unresolved usage rights must remain excluded from
training and evaluation exports.
