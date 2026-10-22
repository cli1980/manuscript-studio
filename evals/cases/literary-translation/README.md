# Translation cases: one source task, multiple candidates

A version-2 case owns one source passage and translation task. Its `candidates`
array contains independently assessable translations, including adverse variants.
See [the schema](../../schemas/translation-case.schema.json).

```json
{
  "schema_version": 2,
  "case_id": "example",
  "revision": 1,
  "source_file": "../../../fixtures/manuscripts/example/source.zh.txt",
  "source_revision": 1,
  "target_language": "en",
  "translation_instructions": null,
  "candidates": [
    {
      "candidate_id": "c-6fe91284bade9201",
      "revision": 1,
      "translation_file": "candidates/c-6fe91284bade9201.en.txt",
      "status": "ready",
      "provenance": {"usage_rights": "permitted"}
    },
    {
      "candidate_id": "c-4ec0768fb9d2a3ed",
      "revision": 1,
      "translation_file": "candidates/c-4ec0768fb9d2a3ed.en.txt",
      "status": "ready",
      "derived_from": "c-6fe91284bade9201",
      "provenance": {"usage_rights": "permitted"}
    }
  ]
}
```

This abbreviated example omits the required shared passage identifiers, source
metadata reference, language, task, and source-task status. Text files stay separate;
paths are relative to `case.json`. Candidate IDs must be unique within a case.
`derived_from` records a relationship, not an assertion that the variant is worse.
Candidate provenance may record intended defects; it is never sent to the model.
New IDs are random `c-` plus 16 hex digits, independently assigned per case.
Ordering by those IDs carries no original/synthetic convention.
The human review API also withholds provenance, filenames, derivation links,
English reference titles, and evaluation notes. Authoring files and private
mapping reports are for maintainers, not evaluator inputs.

| Evaluation target | Iteration unit | Model input |
| --- | --- | --- |
| Translator | Source task, once per generation configuration | Source + target language + translation instructions |
| Judge | Each selected candidate | Source + that candidate's text + independent judge skill |

## Translator inputs

```text
python evals/prepare_translation.py --all --instructions-file TRANSLATOR_INSTRUCTIONS.txt
```

This exports source-only input files and an audit `tasks.json` under `evals/results/`.
Only the per-task input files go to the translator. No stored translations,
ratings, evaluation notes, candidate labels, or published English titles enter
those files. Omit `--instructions-file` to use each case's `translation_instructions`;
null means the caller must supply its translation instructions/skill.
Cases with no candidates are supported. Identical source identity/revision/hash,
target language, and instructions are deduplicated even across legacy cases.
Additional candidates never create additional translator tasks.
Each audit task names one `case_id` for scoring the generated output; `case_ids`
lists equivalent aliases for provenance, not additional scoring jobs.
Automatic discovery skips case directories containing `.local-only`, including
the optional local 《刺秦》 case. Select a local case explicitly with `--case` for
manual testing; it is never included merely by choosing `--all`.

Generation is separate from this exporter. Record translator/model, skill version,
and generation settings with each new output, then assess it:

```text
python evals/run_judge.py --mode judge --case CASE_ID --translation-file NEW_OUTPUT.txt --model JUDGE_MODEL
```

This assessment reads neither stored candidates nor their human ratings. Preserve
the supplied passage scope; do not present an excerpt as a complete chapter.

### Minimal-prompt synthetic candidates

```text
python evals/generate_translation_candidates.py --contemporary --model azure/openai/gpt-4.1-mini
```

This selects only the contemporary corpus. Use `--case` for explicit cases or
`--all` for the whole collection. It uses a lightweight non-reasoning model with exactly
`translate the Chinese to English` as the system instruction and the Chinese
source as the user message. It appends candidates with fresh opaque IDs, preserving
other translations and all human ratings. Outputs are unscored adverse candidates,
not certified bad translations. Model, prompt, source/output hashes, settings, and
usage are recorded. Truncated/refused outputs are not published.
Use `--resume <run-directory>` to reuse saved responses after an interruption.
Finish review submissions and stop the snapshot-based review server before
publishing new candidates, then restart it to load the updated collection.

## Judge evaluation and human review

```text
python evals/run_judge.py --mode evaluate --case CASE_ID --reviewer HUMAN_REVIEWER --model JUDGE_UNDER_TEST
python evals/run_judge.py --mode evaluate --case CASE_ID --candidate CANDIDATE_ID --reviewer HUMAN_REVIEWER --model JUDGE_UNDER_TEST
```

The first command assesses every candidate independently; the second selects one.
`--candidate` requires one case and cannot accompany `--translation-file`.
Model requests contain no candidate labels, provenance, other translations, or
human scores. `--all` reports and skips unavailable candidates; explicitly selected
cases/candidates report missing-input errors.

Human records share `judgments.jsonl` but each binds `case_id`, `case_revision`,
`candidate_id`, `candidate_revision`, `passage_id`, `source_revision`, and rubric
version. Amendments cannot cross candidate revisions. The review UI has a candidate
selector, candidate-specific forms/history, and case-level progress.

Case `status` describes source-task readiness; each candidate has its own status
and provenance. Completed human labels are additionally required for judge
benchmarking or training. `judge` mode can assess unlabelled candidates but does
not measure judge accuracy. Model outputs never become human ratings.

Results are stored under `<run>/<case-id>/<candidate-id>/`. Evaluation reports
candidate-weighted metrics and `case_macro_metrics`, which weight each case equally.
Failed comparisons and skipped candidates remain explicit; metrics cover only
successful comparisons. Paired baseline/adverse score-change analysis is separate
and is not yet implemented.

## Revisions and migration

Add another candidate to the same case instead of duplicating the source task.
Start fresh human reviews for it. Preserve rated text before revising it, increment
that candidate's revision, and never relabel old ratings. Adding/changing a candidate
does not change the source-task revision or invalidate other candidates' ratings.
Change the case revision when its source binding or translation task changes.
Keep all candidates and passages from a work's `group_id` in one dataset split.

Legacy version-1 cases remain readable as one `baseline` candidate. Migrate them:

```text
python evals/migrate_translation_cases.py
python evals/migrate_translation_cases.py --write
```

Migration preserves text bytes, provenance, ratings, and historical revisions,
adds candidate bindings, and saves original records under ignored `evals/results/`.
It is idempotent. Finish pending review submissions before maintainer migrations,
then restart the review server to load the changed records.

Convert descriptive candidate IDs and filenames to opaque ones with:

```text
python evals/anonymize_translation_candidates.py --write
```

This preserves texts and scores, rebinds human judgments and derivation links,
and saves originals plus an old/new ID mapping under ignored `evals/results/`.
Existing model-run artifacts remain historical records; use the private mapping
to relate their old IDs to current ones. Legacy descriptive IDs receive opaque
session aliases in the review API as well.
