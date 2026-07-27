# Task-Artifact Fallback

Use this fallback when Git cannot be made usable during manuscript project setup. Keep the received manuscript or other user-supplied inputs unchanged in their original locations. Redirect every agent-generated setup and review output away from the manuscript project and into the current task's artifact or Outputs area.

## Resolve the destination

Use the task-artifact facility or output directory explicitly provided by the environment. Treat its identifier or path as opaque; do not invent, derive, or guess an Outputs path.

If no task-artifact facility is available, do not write generated editorial files into the manuscript project. Return the diagnostic and permitted verdict in chat, state that artifact persistence is unavailable, and remain `verdict-score-only`.

## Preflight before persistent setup

Before creating the persistent project layout, perform safe Git preflight:

1. confirm that the Git executable runs;
2. resolve an appropriate repository root or confirm that initialization is allowed;
3. check that repository-local or inherited author identity can support the baseline commit;
4. identify unrelated or overlapping changes that would prevent a safe baseline.

If preflight fails, enter task-artifact fallback immediately. Perform any necessary extraction or normalization only inside the task artifact area.

If baseline creation fails after generated project files were written:

1. stop project-local output immediately;
2. copy every generated setup and review artifact to the task artifact area;
3. record which project files were generated before failure;
4. never move, delete, or overwrite user-supplied or pre-existing files;
5. remove a partial generated project file only when it was created by the current setup, its artifact copy is verified, and removal is safely recoverable; otherwise leave it marked incomplete and do not use it as durable state.

## Permitted task artifacts

Create a compact fallback bundle such as:

```text
<task-artifact-root>/
|-- git-unavailable-diagnostic.md
|-- artifact-manifest.md
|-- normalized-manuscript/        # only when extraction is needed for review
`-- verdict.md
```

`artifact-manifest.md` records:

- work, scope, and source identity;
- source path or attachment identity, size, modification time, and checksum when feasible;
- Git failure stage and diagnostic;
- fallback mode: `verdict-score-only`;
- generated artifact paths;
- extraction, normalization, and completeness limitations.

`verdict.md` contains only the scoped verdict, 1–5 editorial-acceptance score, evidence, limitations, and permitted score revisions. Keep all later fallback revisions in the task artifact area.

## Prohibited outputs

Do not create project-local editorial state, proposals, decision tables, approvals, application reports, revised manuscripts, alternate draft folders, commits, or Git-bound completion claims. Do not treat task artifacts as a substitute version-control system.

## Recovery

When Git becomes usable:

1. return to the original source or verified manuscript input;
2. establish the normal project layout and clean baseline commit;
3. start a new commit-bound review;
4. treat fallback task artifacts as reference evidence only;
5. do not import proposals, approvals, or implied edit authority from the fallback bundle.