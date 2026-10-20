# Workspace and Source Strategy

Use two distinct locations for every project:

- **Source location:** the author-controlled manuscript draft. It may be a folder, file, attachment, connected document, or local repository.
- **Workspace:** the editorial working environment containing the normalized manuscript, evidence, proposals, approvals, state, reports, and exports.

Never use the source location itself as the workspace. Record both identities explicitly and keep their files, version identities, and permissions separate.

The neutral package produced by [prepare-manuscript](../../prepare-manuscript/SKILL.md)
is a third, shared input location. It is neither the author-controlled source
repository nor the editable editorial workspace. Keep it outside both roots.
Preparation owns source extraction; editing owns its working copies and approvals.

## Invariant workspace layout

Use the same logical layout in both operating modes:

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

`source/` inside the workspace contains provenance records, not the author-controlled source draft. Do not copy the received source into the workspace unless extraction requires a reference copy and the user or environment permits it. Mark any such copy as an imported snapshot, never as the source location.

## Select the operating mode

Run preflight before creating durable state:

1. confirm whether Git runs;
2. confirm whether two separate local repository roots can be used;
3. confirm author identity can support commits in both repositories;
4. inspect both locations for existing repositories and unrelated changes;
5. reject a nested-repository layout.

Use:

- `dual-repository-git` when both workspace and source draft can be managed safely as separate local Git repositories;
- `artifact-workspace` when Git is unavailable, either repository cannot be created safely, or the environment exposes only task/output artifacts.

Do not mix modes within one editorial job. Record the selected mode and reason in `editorial/project-state.md`.

## Dual-repository Git mode

Use two independent local repositories:

1. **Workspace repository:** owns the invariant workspace tree and all editorial history.
2. **Source repository:** owns the author-controlled source draft and its source history.

Do not nest one repository inside the other. Record both roots, baseline commits, current commits, and tracked source paths in the manifest and project state.

Copy the selected verified prepared chapters into `workspace/manuscript/chapters/`
without editorial changes. Bind each review to the workspace manuscript commit,
the prepared revision and chapter hashes, and the original source identity.
Verify the original repository commit/fingerprint against preparation's recorded
source identity before recording the import base.

After explicit approval:

1. apply and verify approved changes in the workspace;
2. commit the approved workspace batch;
3. revalidate the source repository base, tracked draft path, and absence of conflicting source changes;
4. update the source draft using only the approved changes;
5. verify the updated source against the approved workspace result;
6. commit the source update separately;
7. record both resulting commits.

If source synchronization fails, preserve the workspace commit, mark `source-sync-pending`, create a verified export for manual application, and do not rewrite either repository's history.

## Artifact-workspace mode

Use the environment-provided task artifact or Outputs destination as the workspace root. Treat its path or identifier as opaque; never invent or guess one. Create the same invariant workspace layout there.

Identify review inputs with durable fingerprints rather than Git commits. Record source identity, size, modification time, checksum when feasible, normalized chapter checksums, and workspace revision identifiers in the manifest and project state.

Treat every persisted artifact workspace revision as immutable. Use native artifact versioning when it preserves addressable prior versions. Otherwise create a new artifact workspace revision root with the same invariant internal layout; do not overwrite the reviewed revision or create ad hoc draft folders inside it.

Artifact mode supports the complete editorial lifecycle:

- normalized workspace chapters;
- verdicts and score revisions;
- proposals and decision tables;
- approval records;
- approved workspace revisions;
- style and continuity state;
- application reports;
- updated-source exports.

Never write to, overwrite, rename, or delete the source location in artifact mode, even after approval.

After explicit approval:

1. revalidate the reviewed fingerprints and exact current text;
2. apply only approved proposals to a new workspace revision;
3. verify the approved-only diff and manuscript integrity;
4. generate a complete updated source under `exports/<job-id>/`;
5. preserve the prior workspace revision and export;
6. ask the user to apply or replace the source manually;
7. mark the job `awaiting-manual-source-update` until the user confirms the source was updated.

After confirmation, re-read and fingerprint the source when access is available, compare it with the delivered export, and record manual-source-update-confirmed. If verification access is unavailable, record the confirmation as user-reported and do not claim independent verification.

Do not claim that the source draft changed merely because an export was created.

## Mode transition

When moving from artifact mode to Git mode:

1. verify the current source independently;
2. preserve the artifact workspace as provenance;
3. create separate source and workspace repositories;
4. import the confirmed current source into the invariant workspace layout;
5. establish fresh baselines in both repositories;
6. start new reviews against those baselines.

Do not retroactively attach old approvals or source-update authority to the new repositories. Existing artifact reports remain evidence and may be referenced, but every unapplied proposal must be revalidated.