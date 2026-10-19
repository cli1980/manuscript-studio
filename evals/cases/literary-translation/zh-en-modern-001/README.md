# Chinese-to-English translation case: zh-en-modern-001

This modern Chinese literature case uses a passage from Lu Xun's (鲁迅)
《故乡》 (*My Old Home*).

This case remains a dataset placeholder while its metadata is being completed.
The user-provided Chinese passage
is stored in the [shared source fixture](../../../fixtures/manuscripts/modern-lu-xun-guxiang/passage-001/source.zh.txt);
the English translation remains in `translation.en.txt`.
Human reviews are recorded in `judgments.jsonl`; submitting a review does not
complete the remaining dataset metadata. Exclude placeholder cases and pending
judgments from training, validation, and test datasets.

## Fill in the case

1. Review the supplied passage and translation. Both are UTF-8 plain text.
   Resolve `source_file` and `source_metadata_file` relative to `case.json`.
2. Complete the shared [passage metadata](../../../fixtures/manuscripts/modern-lu-xun-guxiang/passage-001/passage.json)
   with verified work information, source provenance, usage rights, and any shared
   context. `modern-lu-xun-guxiang` identifies the source work, and
   `modern-lu-xun-guxiang-passage-001` identifies this excerpt. In `case.json`, record translation
   provenance, its usage rights, and any translation-specific brief. The source
   identifiers, language, and revision must match the shared metadata. Leave
   unavailable optional context null.
3. Select a versioned rubric under `evals/rubrics/`. The initial
   `literary-translation-quality-v1` rubric defines a 1-5 overall scale with
   optional dimension scores. Calibrate its anchors with reviewers before
   collecting a training benchmark.
4. Fill in the pending record in `judgments.jsonl` with a pseudonymous `rater_id`,
   the rubric version, and the human's `overall_score`. Dimension scores,
   rationale, and evidence-backed issues are optional. Keep unavailable scores
   null rather than using zero.
5. Mark the judgment `complete` after the human assessment is recorded. Change
   the case status to `ready` once its inputs and metadata are complete and usage
   rights for both texts are established.

Keep each judgment as one JSON object on a single line in `judgments.jsonl`.
For another reviewer, append a record with a unique judgment ID; do not overwrite
an independent rating. An empty `issues` array in this pending template does not
mean the translation has been reviewed and found error-free.

For another translation of this passage, create a separate case directory with
a unique case ID, its own `translation.en.txt`, and a fresh pending judgment.
Reuse this case's source references, work and passage IDs, and source revision.
Do not copy the Chinese text or reuse human ratings from this case.

Judgments identify both the case revision and the source passage revision.
No completed judgments exist yet, so this layout migration retains revision 1.
For subsequent text changes, follow the
[revision and dataset rules](../../../README.md#revisions-and-dataset-splits).

Human scores and provenance such as translator identity are not judge inputs.
Keep model predictions under `evals/results/`, separate from human judgments.

The [review server](../../../server/README.md) displays both supplied texts and
lets reviewers save draft or completed assessments. It preserves assessment
history when scores are amended. Saves remain in a temporary workspace until
**Submit changes** is confirmed; restarting discards unsubmitted edits.
The judge's label is set at startup or the first sign-in and applies to all browser
sessions for that server run. The review form edits only scores, comments, and issue annotations.
Case metadata and texts are read-only; rubric assignment is server-controlled.
The preparation steps above are performed by the dataset maintainer outside the
judge interface.
The initial pending record is a template, not a human judgment.
