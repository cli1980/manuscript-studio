# Dual-Repository Git Versioning

## Contents

1. Repository selection
2. Source baseline
3. Workspace baseline
4. Review binding
5. Approved application
6. Source synchronization
7. Recovery and milestones
8. Artifact-workspace alternative

Read [workspace-and-source.md](workspace-and-source.md) first. Use this reference when the operating mode is `dual-repository-git`.

## Repository selection

Use two independent local repositories:

- the **source repository** contains the author-controlled source draft;
- the **workspace repository** contains normalized chapters and all editorial state.

Resolve the nearest repository root for each location before running `git init`. Never nest either repository inside the other. Reuse an existing repository only when its intended scope includes that location. If a parent repository's scope is unclear, ask before using it.

Keep both repositories local by default. Never add a remote or push manuscript content without explicit authorization. Warn when either root is cloud-synced or may be edited concurrently.

Verify Git author identity in both repositories before their first commits. If identity is missing, ask for repository-local `user.name` and `user.email`; do not invent them.

## Source baseline

Inspect the source repository before staging. Preserve unrelated user changes. Never use broad staging, automatic stash, destructive reset, checkout-based restoration, or history rewriting.

Stage only the identified source draft and an appropriate source `.gitignore` when needed. Create a baseline commit such as:

```text
chore(source): establish manuscript baseline
```

Tag it `source-manuscript-baseline`, or use a stable work-specific tag when the repository contains several works. The source baseline preserves the received draft through history; it does not make the source working file permanently immutable after approval.

## Workspace baseline

Create the invariant workspace layout and copy the verified chapters supplied by
`prepare-manuscript` before staging. Record the prepared revision and chapter
mapping; do not run a separate editorial extraction procedure. Stage only those
verified working copies, editorial provenance records, manifest, brief, shared
records, and project state. Create a baseline commit such as:

```text
chore(workspace): establish editorial baseline
```

Tag it `editorial-workspace-baseline`, or use a work-specific tag when necessary.

A commit cannot contain its own SHA. After both baseline commits exist, write their full SHAs and tags to `source/source-record.md`, `source/manuscript-manifest.md`, and `editorial/project-state.md`, then create a separate workspace metadata commit. Do not amend either baseline.

Confirm that tracked source-draft paths and workspace manuscript paths are clean before review.

## Bind reviews and proposals

At the start of a job, record:

- workspace repository root and full workspace review commit;
- reviewed workspace manuscript paths;
- source repository root, tracked source draft path, and source import commit;
- any source-to-workspace conversion or extraction identity.

Do not change source or workspace manuscript paths during review. Durable files under `editorial/` may be committed separately; preserve the original workspace manuscript review commit in the job records.

Before applying approval, verify:

1. both recorded commits exist;
2. workspace manuscript paths have not changed since the review commit;
3. tracked and untracked files under the target workspace scope contain no unreviewed work;
4. each proposal's exact current text still matches;
5. accepted proposals do not overlap incompatibly.

If the workspace manuscript changed, preserve the old report, compare the affected scope, and mark invalid proposals `stale`. Never silently rebase wording.

## Commit approved workspace application

After approval records are saved:

1. apply only accepted or accepted-with-modification proposal IDs to the workspace manuscript;
2. update style and continuity records only for approved decisions;
3. inspect the workspace manuscript diff against the review commit;
4. verify that every changed span maps to approval;
5. stage explicit changed paths;
6. commit one coherent approved workspace batch.

Use a message such as:

```text
line-edit(ch04): apply LE-004, LE-006, LE-009
```

Record the resulting full workspace SHA before synchronizing the source.

## Synchronize and commit the source

Treat source synchronization as a separate controlled operation:

1. verify the source repository is still at the recorded import commit or determine that only nonconflicting unrelated paths changed;
2. verify the tracked source draft and format;
3. transform only the approved workspace changes into the source format;
4. compare the updated source with the approved workspace manuscript;
5. verify no unapproved text, paragraph boundary, chapter order, or formatting change entered the source;
6. stage only the source draft paths;
7. create a separate source commit identifying the service, scope, proposal IDs, and workspace result commit;
8. record the resulting source SHA in project state and the application report.

If the source changed incompatibly or conversion cannot be verified, do not write or commit it. Preserve the workspace commit, generate a verified updated-source export, and mark the job `source-sync-pending`.

## Recovery and milestones

Use forward history in both repositories. If an accepted edit must later be reversed, create approved corrective commits; do not erase the original decisions.

Tag only meaningful milestones after verifying both workspace completion and source synchronization. On resume, inspect both repository roots, commits, statuses, baselines, active job identities, approval state, and the last application report.

When saved state and chat conflict, trust verified files, commits, fingerprints, and recorded approvals.

## Artifact-workspace alternative

If Git is unavailable or either repository cannot be created safely, use `artifact-workspace` instead of a degraded Git workflow. Follow [workspace-and-source.md](workspace-and-source.md): keep the same workspace structure, use fingerprints and preserved revisions, run the complete verdict-and-approval lifecycle, never modify the source location, and generate a verified updated-source export for manual application.