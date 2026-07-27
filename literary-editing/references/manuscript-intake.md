# Manuscript Intake and Project Initialization

Use this workflow before the first editorial review or when required project artifacts are missing.

## Locate and qualify the manuscript

Search available project files, attachments, and connected sources by title, author, chapter heading, and likely filename. Confirm the work identity, responsible user, intended draft, file type, completeness for the requested service, chapter order, and in-scope book components.

If the required artifact cannot be found, ask the user to provide it. Do not infer missing manuscript content or issue a conclusive whole-book verdict from a synopsis or sample.

## Inspect extraction quality

Check whether extraction preserves every paragraph in order, punctuation, capitalization, italics, dialogue layout, intentional spacing, scene breaks, notes, chapter headings, and non-text anchors. Identify OCR errors, missing pages, duplicated text, encoding problems, and ambiguous boundaries.

Resolve objective extraction corruption against the received artifact. Report uncertain cases rather than silently normalizing them.

## Normalize without editing

If the manuscript is not already a verified chapter set:

1. Use the appropriate document or PDF workflow to extract it.
2. Identify real chapter boundaries from headings and structure, not arbitrary length.
3. Save one UTF-8 Markdown file per chapter under `manuscript/chapters/`.
4. Use stable sortable filenames.
5. Preserve exact wording, paragraphing, punctuation, order, and intentional irregularities.
6. Preserve scene and section breaks using the project convention.
7. Compare the ordered chapter files with the received artifact.
8. Verify that their bodies reproduce the complete manuscript exactly once.

Normalization may fix extraction errors only when the artifact makes the intended characters or layout objectively clear. It must not improve grammar, spelling, style, continuity, or story.

## Establish the project layout

Use an existing convention when present. Otherwise create:

```text
project/
|-- source/
|   |-- received-manuscript.<ext>
|   `-- manuscript-manifest.md
|-- manuscript/
|   `-- chapters/
|-- editorial/
|   |-- editorial-brief.md
|   |-- style-sheet.md
|   |-- continuity-concordance.md
|   |-- project-state.md
|   `-- reports/
`-- exports/
```

Keep the received artifact unchanged. Do not create version-numbered copies of the normalized chapter tree.

## Write the manifest and brief

Record in `source/manuscript-manifest.md`:

- work, author, and manuscript identity;
- received artifact path, type, and checksum when feasible;
- normalized chapter filenames in order;
- chapter and total word counts;
- completeness and extraction limitations;
- intended Git root;
- baseline commit SHA and tag after setup, or Git-failure status and artifact fingerprint in fallback mode.

Record known values in `editorial/editorial-brief.md`: audience, genre, goals, concerns, service, scope, language variety, style references, intervention level, protected features, target medium, exclusions, and constraints. Mark unknowns instead of inventing them.

Create empty style and continuity records using `style-and-continuity.md`. Do not treat observations as approved decisions.

## Hand off to Git

After exact-once verification, complete `git-versioning.md`. Normally, do not begin editorial review until the baseline commit exists, the manifest records its full SHA, and tracked manuscript paths are clean. If Git is unavailable or setup fails, enter `verdict-score-only` mode and limit the work to a verdict and acceptance score without proposals or manuscript changes.

## Resume an existing project

Verify the manifest against the received artifact and chapter set, confirm the Git root and baseline, inspect active job state, preserve established filenames and approvals, and resume from the recorded next action. Do not regenerate settled artifacts without a demonstrated integrity problem.
