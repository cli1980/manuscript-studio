# Git Versioning

## Contents

1. Repository selection
2. Baseline setup
3. Review binding
4. Approved application
5. Recovery and milestones
6. Git-unavailable fallback

Use Git as the manuscript version system. Keep one checked-out chapter tree; do not create `v001`, `v002`, or equivalent draft copies.

## Repository selection

Resolve the nearest repository root before running `git init`.

- Reuse a repository only when its intended scope includes the manuscript project.
- Do not create a nested repository accidentally.
- If a parent repository exists but its intended scope is unclear, ask the user.
- If no repository exists, initialize one at the manuscript project root.
- Keep the repository local by default. Never add a remote or push manuscript content without explicit authorization.
- Warn when a cloud-synced root could be edited concurrently on several machines. Do not let synchronization replace Git history.

Verify that Git author identity is available before the first commit. If it is missing, ask for repository-local `user.name` and `user.email`; do not invent them.

## Baseline setup

Create `.gitignore` before the baseline commit. Ignore only disposable material, such as office lock files, extraction scratch files, caches, and reproducible exports. Track normalized chapters, the manifest, project state, shared editorial records, verdicts, proposals, approvals, and application reports.

Inspect status before staging. Never run `git add -A`, `git add .`, automatic stash, destructive reset, checkout-based restoration, or history rewriting. Stage explicit in-scope paths only. Leave unrelated user changes untouched.

If unrelated changes overlap the required manuscript paths, stop and ask the user to resolve or authorize a checkpoint. Do not absorb them into an editorial commit.

After exact-once manuscript verification:

1. Stage the verified chapter set, manifest, initial brief, shared records, state, and agreed source record.
2. Commit with `chore(manuscript): establish normalized baseline` or an equivalent clear message.
3. Tag the commit `manuscript-baseline` in a dedicated book repository. If that tag already exists or the repository contains several books, use a stable work-specific tag and record it.
4. Save the full commit SHA and tag in the manifest and project state.
5. Confirm that tracked manuscript paths are clean.

Large DOCX and PDF files are binary. Retain the received artifact and checksum, but use normalized Markdown for meaningful diffs. Track the binary only when repository policy and size make that appropriate.

## Bind reviews and proposals

At the start of a job, save `git rev-parse HEAD` as `reviewed_commit`. The verdict and every proposal must reference it.

Do not change `manuscript/` while reviewing. Durable files under `editorial/` may be saved and committed separately; their commit does not change the manuscript base.

Before applying approval, verify:

1. the recorded reviewed commit exists;
2. `git diff --quiet <reviewed_commit> -- manuscript/` reports no manuscript changes;
3. tracked and untracked files under the target manuscript scope contain no unreviewed work;
4. each proposal’s exact current text still matches its recorded location;
5. accepted proposals do not overlap incompatibly.

If manuscript paths changed, compare the affected scope. Preserve the old report, mark invalid proposals `stale`, and regenerate only what needs review. Never silently rebase wording.

## Commit approved application

After approval records are saved:

1. Apply only accepted or accepted-with-modification proposal IDs.
2. Update style and continuity records only for approved decisions.
3. Inspect the manuscript diff against `reviewed_commit`.
4. Verify that every changed span maps to approval and no rejected, deferred, or pending proposal appears.
5. Stage explicit changed manuscript and editorial record paths.
6. Commit one coherent approved batch.

Use a message such as:

```text
line-edit(ch04): apply LE-004, LE-006, LE-009
```

Do not amend a previous commit. Record the resulting full SHA in the application report and project state.

## Recovery and milestones

Use normal forward history. If an accepted edit must later be reversed, create a new approved corrective commit; do not erase the original decision.

Tag only meaningful milestones, such as a completed developmental revision, manuscript-wide line edit, manuscript-wide copyedit, or final proof. Verify the relevant completion gate before tagging.

On resume, inspect the repository root, HEAD, status, manifest baseline, current job base, proposal statuses, and last application report. When saved state and chat conflict, trust verified files, commits, and recorded approvals.

## Git-unavailable fallback

If the Git executable is unavailable, repository initialization fails, the baseline commit cannot be created, or Git cannot safely protect the manuscript:

1. Record the failure and its diagnostic evidence without repeatedly retrying destructive or broad alternatives.
2. Identify the reviewed artifact precisely with path, size, modification time, and checksum when feasible.
3. Enter `verdict-score-only` mode.
4. Read and assess the requested scope without changing manuscript files.
5. Deliver only the verdict and 1–5 editorial-acceptance score.
6. Do not produce proposal diffs, record approvals, apply edits, create alternate version folders, or claim a Git-bound completion state.

If Git later becomes available, establish and verify a clean baseline first. Start a new review bound to that commit before creating proposals; do not retroactively attach a fallback verdict to a commit.
