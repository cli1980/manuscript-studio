# Ground-truth review server

A review interface for one literary judge per server run, usable from multiple
browser sessions. Inspect supplied texts and record
subjective quality scores, comments, and evidence-backed issues. The five skills
appear in navigation; literary translation has the first assessment form.
Other skills remain unsupported until their review formats are defined.

Dataset preparation is separate from judging. There are no passage or case
creation routes, no text editing routes, and no case metadata editing routes.
Work identity, languages, source references, revisions, briefs, provenance,
usage rights, dataset readiness, and rubric configuration are read-only.
Maintainers prepare those files outside this server, then restart it to load them.

## Run locally

From the repository root, using Python 3.12 or newer:

```text
python -m venv .venv-evals
.venv-evals/Scripts/python.exe -m pip install -r evals/server/requirements.txt
.venv-evals/Scripts/python.exe -m evals.server
```

On macOS or Linux, use `.venv-evals/bin/python` instead. Open
`http://127.0.0.1:8765`, enter the access key and your reviewer label, then select
`zh-en-000001` under Cases. The sample's text is displayed unchanged alongside
its saved human reviews; testing never changes real ground truth.

For a server dedicated to one judge, set the label at startup:

```text
.venv-evals/Scripts/python.exe -m evals.server --reviewer-label "judge-01"
```

Sign-in then asks only for the access key. All sessions use the configured label;
clients cannot override it. The label appears after sign-in and is attached to
every assessment. Omit `--reviewer-label` to bind the judge's label at the first
successful sign-in. Subsequent browsers need only the access key.
Blank labels and labels longer than 500 characters are rejected.

Use `--port` to choose another port or `--data-dir` to select an existing evaluation
workspace at startup. The workspace must contain `cases/`,
`fixtures/manuscripts/`, and `rubrics/`. Requests cannot change that root.
Use the exact displayed browser origin; `localhost` and `127.0.0.1` are distinct.

## Temporary workspace and submission

At startup, the server copies only the permitted evaluation records into a
private temporary directory. All of the judge's browser sessions share that workspace.
Inspecting data, saving scores and comments, and marking assessments complete
operate on this copy. They do not modify the original evaluation files.

The banner shows pending changes. Press **Submit changes** to review the affected
cases, then **Submit to source** to publish only their judgment records to the
configured data directory. The submission includes your saved assessments from
all connected browser sessions. Unsaved form fields must be
saved first.

Submission checks both the reviewed workspace version and the original snapshot.
If another browser changes the workspace, reopen the confirmation to review the
latest changes. If original data has changed outside the server, submission stops
without overwriting it, and pending edits remain in the temporary workspace.
Reconcile those originals before retrying, or preserve the pending edits before
restarting to load a fresh snapshot. Browser reload does not reload original files.

Successful submission establishes a new baseline for subsequent edits. Submitting
again without changes does nothing. There is no Git commit or push.
Logout does not clear the shared workspace. Restarting the service discards
unsubmitted edits and loads the current originals; normal shutdown removes the
temporary directory. A hard crash may leave an orphan temporary directory, but
the next startup never resumes it automatically.

Judgment files use atomic replacement. New judgment files may be created only
inside pre-existing cases. On an ordinary publication failure, completed writes are rolled
back and drafts are kept for retry. Submission is not crash-atomic across multiple
files: a process or machine failure during publication can leave partial changes.
If rollback itself fails, stop submitting and inspect the originals. Back up the
evaluation data before using it as a production ground-truth store.

The temporary key permits any holder to inspect cases and record judgments. Every
startup generates a fresh key; existing keys and browser sessions cease to work
after restart. Keys and sessions stay in memory. A nonblank reviewer label is
supplied either at startup or the first successful sign-in; surrounding whitespace
is trimmed. The label is fixed for the entire server run and the server attaches it
to every draft and completed assessment.
It is displayed read-only in the review interface and survives browser reload.
Changing the judge requires a restart; submit pending assessments first.
Each browser receives its own session cookie and CSRF token. Reauthentication
rotates only that browser's session. Logout invalidates only that browser's
session, leaving other browsers signed in and the server's judge assignment intact.

Labels remain self-reported, not verified identities or managed accounts.
Anyone holding the access key acts as the server's configured judge. Historical
reviews from other judges can be inspected but not amended by this judge.

Run one server process per data workspace, without reload or multiple workers.
Do not run two independent server processes against the same files. The provided
launcher uses one worker. Request logging is disabled so passage text and access
keys are not written to request logs.

## Scope of access

The repository layer permits reads only from supported case files, passage
fixtures, and rubric JSON. Normal writes are confined to the startup-created
temporary workspace. Only the authenticated, CSRF-protected submission endpoint
may publish `judgments.jsonl` files for existing supported cases to the original
data root. Earlier judgment records must be preserved; corrections append
amendments. Sources, candidate translations, all metadata, and rubrics cannot be
changed by submission, even if a temporary file was modified outside the UI.
There is no generic filesystem, upload, deletion, shell, Git, model, or skill
execution API. Application assets are served by three fixed routes.

Client identifiers are validated; judgment filenames, new judgment IDs, source and
case revision bindings, rubric IDs, and timestamps are server-controlled.
Stored JSON references are also validated. Absolute paths, escapes from the
permitted area, symbolic links, Windows reparse points/junctions, and files with
multiple hard links are rejected. Request bodies are limited to 1 MiB, comments
and each issue text field to 10,000 characters, and persisted data files to 4 MiB.
Snapshots and submissions are limited to 16 MiB and 5,000 files.

Authentication is required for every data endpoint. Writes require a matching
Origin and a session-specific CSRF token. Host checks reject DNS-rebinding
requests; cross-origin requests are not enabled. Cookies are HttpOnly and
SameSite=Strict. A configured HTTPS origin also enables Secure cookies.
Login attempts are rate limited. Security headers disable framing and inline
scripts. No external fonts, scripts, or browser services are used.

The native process still inherits the operating-system permissions of its user.
Application checks do not sandbox a compromised process, and concurrently
malicious filesystem writers are outside that boundary. For operating-system
isolation, use the container configuration or a dedicated account with equivalent
permissions.

## Isolated container

With Docker Compose available, run from the repository root:

```text
docker compose -f evals/server/compose.yaml up --build
```

The image contains server code and dependencies, not the repository or sample
data. Its non-root process has a read-only root filesystem and exactly three
data mounts:

| Mount | Permission |
| --- | --- |
| `evals/cases/` | Read/write |
| `evals/fixtures/manuscripts/` | Read-only |
| `evals/rubrics/` | Read-only |

Skill instructions, `.git/`, results, and other repository files are not mounted.
Capabilities are dropped, privilege escalation is disabled, and CPU, memory,
process count, and temporary storage are bounded. An internal Docker network
limits external connectivity; the published port binds only to host loopback.
On Linux, grant container UID 10001 write access to case directories for atomic
judgment replacement, and read access to passages and rubrics. The application
limits writes inside those directories to `judgments.jsonl`; the case-directory
mount itself is not an OS-level per-file write restriction. Do not grant access
to the rest of the repository.

For access from other machines, explicitly deploy behind an HTTPS reverse proxy
and set `--origin https://your-host` with `--host 0.0.0.0`. Preserve the configured
Host header. Forwarded headers are not trusted. Do not expose the native HTTP
port directly on an untrusted network.

## Review behavior

- Original texts, translations, case context, and the session's reviewer label
  are read-only. The editable form contains overall and dimension scores,
  comments, issue annotations, and draft/complete assessment status.
- **Your review** automatically loads your latest current assessment for the
  case, source revision, and assigned rubric. If you have not reviewed that version,
  it starts with an empty form. There is no assessment-selection dropdown.
- Case cards and the open case's subtitle show **Not reviewed**, **Draft**, or
  **Completed** for this judge, using the same current-review rules as the form.
  Empty placeholders, other judges' ratings, and outdated reviews do not count.
  The status updates after saving and does not depend on dataset readiness.
  Dataset preparation status remains in the collapsed read-only metadata section.
- Saving an edit appends a record with `supersedes_judgment_id`, preserving the
  earlier version. Older reviews and other reviewers' assessments appear in the
  collapsed, read-only **Review history** section. Opening history never replaces
  your editable review. Empty unassigned placeholders are hidden from the UI but
  preserved in storage. These records remain temporary until Submit changes
  publishes them.
- Drafts may contain unset scores, but always carry the session's reviewer label.
  Completing an assessment requires a configured rubric and an overall integer
  score from 1 to 5. Optional
  dimensions and evidence-backed issues are supported. Overall scores are not
  calculated automatically.
- **Mark complete** saves the review, collapses the completed case, and opens the
  next unfinished case in the selected skill for the signed-in judge. It skips that judge's completed current
  reviews and wraps to earlier unfinished cases when needed. A newer draft,
  another judge's score, or a review for an old revision or rubric does not count
  as completed. When none remain, the case stays collapsed and the page announces
  that all cases for that skill are complete and reminds the judge to submit the
  pending changes. Completed cases can be reopened from the case list.
  **Save draft** stays on the current case. Neither action publishes to source.
- Saving unchanged scores, comments, issues, and completion status is a no-op:
  it creates no history entry and does not touch the file. Mark complete still
  advances to the next unfinished case. Changing draft/complete status is a real
  change. Existing historical records, including older duplicate entries, are
  preserved.
- The initial rubric is `literary-translation-quality-v1.json`. Its anchors and
  dimension descriptions appear in the interface. It is an initial calibration
  rubric, not evidence that the sample has been judged. Judges cannot select or
  change rubric versions. A maintainer can set `rubric_id` in `case.json`; otherwise
  the server uses the sole matching rubric for the case's language pair. If the
  assignment is missing or ambiguous, drafts are allowed but completion is blocked.
- Completed judgments remain associated with their case and source revisions.
  Historical or superseded assessments are inspectable but cannot be amended.
  A changed rubric requires a new assessment. Judges cannot change the brief,
  identity, source binding, revisions, or provenance.
- Completing an assessment does not mark the dataset case ready or resolve
  usage rights. Readiness and provenance remain the maintainer's responsibility.
  Dataset exporters must still exclude unresolved rights and drafts.
- Every case response includes a content-based version. Stale writes return 409
  without saving. The interface keeps the local form edits and shows **Load latest
  review** only after a conflict. Loading the latest review asks before discarding
  unsaved edits. There is no permanent reload button. Versions cover case
  metadata, source metadata, both texts, the assigned rubric, and judgment history.
- Writes use a process lock and staged replacement. Submission shares the
  same lock, so API edits cannot race with publication. This is a single-process
  file workspace, not a database transaction across multiple independent servers.

Case and passage revisions are initially loaded from the shared-source format in
the [evaluation guide](../README.md). Dataset export, automatic judging, and source
revision editing are not implemented.

## Tests

```text
.venv-evals/Scripts/python.exe -m pip install -r evals/server/requirements-test.txt
.venv-evals/Scripts/python.exe -B -m unittest discover -s evals/server/tests -v
```

Tests copy the existing sample texts into a temporary workspace and seed synthetic
judgment records there before editing scores. They do not assume the real sample
is unreviewed and never reset submitted human judgments.
They cover authentication, restart invalidation, CSRF, origin
and host checks, request limits, path restrictions, judgment history, stale edits,
atomic-write failure, staging without original writes, explicit submission,
source conflicts, rollback, and loss of unsubmitted drafts on restart. They also
verify that creation and metadata routes are absent and only judgment files can
be published. Multi-browser tests verify one fixed judge, browser-local logout,
conflict recovery, and unchanged saves without extra history.

Optional browser coverage uses Playwright and Chromium:

```text
.venv-evals/Scripts/python.exe -m pip install playwright
.venv-evals/Scripts/python.exe -m playwright install chromium
```

Set `EVAL_BROWSER_TEST=1` before running the same suite. In PowerShell:

```powershell
$env:EVAL_BROWSER_TEST = "1"
.venv-evals/Scripts/python.exe -B -m unittest discover -s evals/server/tests -v
```

The browser test starts its own loopback server on port 18765 and exercises the
sample comparison, scores, comments, issue annotations, amendment history,
persistence after reload, automatic loading of the current review, collapsed
read-only history without empty placeholders, read-only passage inspection, explicit submission,
and logout using disposable data. It verifies that the originals remain unchanged
until submission, and then only `judgments.jsonl` changes.
