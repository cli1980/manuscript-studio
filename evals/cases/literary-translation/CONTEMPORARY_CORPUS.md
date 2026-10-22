# Contemporary Chinese–English review cases

`zh-en-contemporary-001` through `zh-en-contemporary-050` contain 50 passage pairs
from 29 Chinese-original works. Their English texts are published translations,
not model-generated reference answers. The collection covers speculative fiction,
horror, and satire from the SCP community; it is not a representative sample of
all contemporary Chinese literature.

These cases support [both evaluation targets](README.md). To evaluate a translator,
provide the Chinese source and translation instructions while withholding the
published English text and all assessments. Score its new candidate separately.
To evaluate a judge, provide the fixed Chinese/English pair and compare its
predicted scores with completed human ratings for that pair.

Each case has:

- `case.json`: source references, rubric assignment, opaque candidate IDs with private translation provenance,
  credits, license evidence, extraction ranges, and alignment notes.
- `candidates/<opaque-id>.en.txt`: published or generated English text, unchanged.
- `judgments.jsonl`: initially empty, awaiting candidate-specific human reviews.

Shared Chinese originals are under
`evals/fixtures/manuscripts/contemporary-<source-work-id>/passage-<record-number>/`.
All passages from a work share one `group_id`, so keep that entire group in one
training, validation, or test split.

Source-task and baseline-candidate metadata are marked `ready` because the text pair, source references, rubric,
and recorded license/attribution data are populated. This does not mean the
translation has been scored or independently human-certified. The source corpus
describes AI-reviewed passage boundaries and passage-level alignment. Some
excerpts depend on context elsewhere in their source work or fictional universe.

The judge interface should display these cases as **Not reviewed** until a judge
saves an assessment. Human scores are required before training export or comparison
against human ground truth.

See the [text license notice](../../fixtures/manuscripts/CONTEMPORARY_CORPUS.md)
and [import manifest](../../imports/contemporary-corpus/manifest.json). The
modern-literature `zh-en-modern-001` calibration case is separate and is not replaced by this import.

Reproduce or verify the import from the repository root:

```text
python evals/import_contemporary.py --dry-run
python evals/import_contemporary.py
```

The importer reads the final corpus JSONL and saved source evidence without
running the upstream crawler. It rejects changed or incomplete existing imports,
preserves existing human judgments, and leaves identical records untouched.
Additional candidates in an imported case are preserved; the importer checks
the original published candidate (identified privately by corpus provenance) and
source-task fields without replacing those variants or changing opaque IDs.
An interrupted import can be rerun; complete directories already published are
retained. A running review server must be restarted to load the newly imported
cases. Submit any pending reviews before restarting.
