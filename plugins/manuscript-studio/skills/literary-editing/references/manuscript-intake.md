# Manuscript Intake and Project Initialization

Use this workflow before the first editorial review or whenever the source record, normalized chapters, manifest, workspace state, or operating mode is missing.

Read [workspace-and-source.md](workspace-and-source.md) before creating durable files. Keep the author-controlled source and editorial workspace separate throughout setup.

## Identify the two locations

Resolve and record:

- the source location and exact source draft;
- the workspace destination;
- work identity, responsible user, version, file type, and requested scope;
- whether the source is complete for the requested service;
- whether either location already belongs to a repository;
- whether the two locations are physically separate and not nested.

Never initialize the workspace inside the source location. Do not relocate, overwrite, or rename the source merely to simplify setup.

## Select the operating mode

Run the preflight in [workspace-and-source.md](workspace-and-source.md).

Use `dual-repository-git` only when Git can safely manage the workspace and source as two separate local repositories. Otherwise use `artifact-workspace` and resolve the environment-provided task artifact or Outputs destination as the workspace. Do not invent an artifact path.

Create the same workspace structure in either mode:

```text
workspace/
|-- source/
|   |-- source-record.md
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

The workspace `source/` directory contains provenance records, not the live source draft.

## Inspect extraction quality

Check whether extraction preserves every paragraph in order, punctuation, capitalization, italics, dialogue layout, intentional spacing, scene breaks, notes, chapter headings, and non-text anchors. Identify OCR errors, missing pages, duplicated text, encoding problems, and ambiguous boundaries.

Resolve objective extraction corruption against the source. Report uncertain cases rather than silently normalizing them.

## Import and normalize without editing

If the source is not already a verified chapter set:

1. extract it with the appropriate document or PDF workflow;
2. identify real chapter boundaries from headings and structure, not arbitrary length;
3. save one UTF-8 Markdown file per chapter under `manuscript/chapters/`;
4. use stable sortable filenames;
5. preserve exact wording, paragraphing, punctuation, order, and intentional irregularities;
6. preserve scene and section breaks using the project convention;
7. compare the ordered chapter files with the source;
8. verify that their bodies reproduce the complete manuscript exactly once.

Normalization may fix extraction errors only when the source makes the intended characters or layout objectively clear. It must not improve grammar, spelling, style, continuity, or story.

## Write provenance and project records

Record in `source/source-record.md`:

- source location or attachment identity;
- source draft path and format;
- source repository root and commit in Git mode;
- size, modification time, and checksum when feasible;
- import date and method;
- whether a workspace reference snapshot exists;
- permission and source-update constraints.

Record in `source/manuscript-manifest.md`:

- work, author, and manuscript identity;
- ordered normalized chapter filenames and counts;
- source identity from which they were imported;
- completeness and extraction limitations;
- operating mode and workspace identity;
- source and workspace baselines in Git mode;
- source and workspace fingerprints in artifact mode.

Record known values in `editorial/editorial-brief.md`: audience, genre, goals, concerns, service, scope, language variety, style references, intervention level, protected features, target medium, exclusions, and constraints. Mark unknowns instead of inventing them.

Create empty style and continuity records using [style-and-continuity.md](style-and-continuity.md). Do not treat observations as approved decisions.

## Establish baselines

In `dual-repository-git` mode, follow [git-versioning.md](git-versioning.md) and create separate source and workspace baseline commits. Because a commit cannot contain its own SHA, first commit the baseline content, then record the resulting SHAs in a small metadata commit in the workspace. Do not rewrite the baseline commit.

In `artifact-workspace` mode, fingerprint the source and normalized workspace chapters, assign a stable workspace revision ID, and preserve the initial artifact tree before review. Artifact mode supports verdicts, proposals, approvals, workspace revisions, and exports, but never direct source modification.

## Resume an existing project

Verify the source record against the current source, confirm the workspace mode and identity, inspect active job state, preserve established filenames and approvals, and resume from the recorded next action. If the source changed independently, preserve prior reports, import a new workspace revision, and mark affected proposals stale. Do not regenerate settled artifacts without a demonstrated integrity problem.