# Manuscript workflow — iteration 1

A local CLI prototype of the architecture's durable execution layer:

```text
prepare → translate (chapter/passage human gates) → accept → Markdown export
```

Literary drafting and source-grounded prose/fidelity review stay together in the
translation skill. There is no general line-editing or copyediting stage in this
template. Further editorial feedback belongs in translation review.

Implementation modules live in `workflow/src/`: `engine.py`, `runtime.py`,
`storage.py`, and `cli.py`. The package-level `__main__.py` is a thin launcher
preserving `python -m workflow`. Workflow definitions live in `definitions/`,
tests in `tests/`, and architecture documentation in `docs/`. The README and
requirements remain at the workflow root.

The [《刺秦》 end-to-end case](tests/cases/translation-ciqing-001/README.md)
defines raw DOCX inputs, expected workflow artifacts, and human-supervised
approval/recovery checks. It uses a workflow-specific manifest, separate from
the source/English quality-evaluation format under `evals/`. The case-driven
[E2E launcher](tests/run_e2e.py) runs it interactively; live model execution is
separate from the deterministic unit-test suite.
Its original manuscript lives in
[`tests/fixtures/short-story-ciqing/`](tests/fixtures/short-story-ciqing/).

To set up Python dependencies and launch that test in one command:

```text
python workflow/tests/run_e2e.py --setup
```

Codex must already be installed and authenticated. The launcher creates or
resumes a run, presents each human gate, checks restart/replay behavior, verifies
the export, and writes an E2E report. See the case README for pause/resume, runtime
options, and the distinction between workflow checks and literary quality.

## Setup

From the repository root, with Python 3.12 or newer:

```text
python -m venv .venv-workflow
.venv-workflow/Scripts/python.exe -m pip install -r workflow/requirements.txt
.venv-workflow/Scripts/python.exe -m workflow --help
```

On macOS/Linux, use `.venv-workflow/bin/python` instead. Install and authenticate
the Codex CLI separately using its official setup instructions. `codex app-server`
must support the JSONL `initialize`, `thread/start`, `thread/resume`, and
`turn/start` methods and `outputSchema`. Pass `--codex` with the executable's
absolute path when it is not on PATH. No credentials are stored by this package.
The installed Codex authentication/configuration selects the provider.

The only Python dependency is the existing preparation validator's dependency.
The approval-sheet validator/parser is loaded from the pinned repository bundle.
No document converter is bundled: missing DOCX/PDF/OCR adapters must block
preparation. Start with a short UTF-8 Markdown manuscript.

## Run a manuscript

Create the parent directory for runs, then snapshot one explicitly designated
source file. This iteration prepares the whole file, including its real chapters.
The destination must be new; it never initializes over an existing project.

```text
mkdir .workflow-runs
.venv-workflow/Scripts/python.exe -m workflow create .workflow-runs/my-book --source "C:/Manuscripts/book.md" --source-language zh-CN
.venv-workflow/Scripts/python.exe -m workflow step .workflow-runs/my-book
.venv-workflow/Scripts/python.exe -m workflow status .workflow-runs/my-book
```

`create --model MODEL` sets the model for both agents. Alternatively copy
[`definitions/translation.json`](definitions/translation.json), set each agent's `model`, and pass
`create --definition PATH`. The configuration is snapshotted at creation.
Only this four-stage topology and these skill bundles are supported in iteration 1;
the configuration loader rejects other targets, stages, and incomplete bundles.
An omitted model uses the installed Codex default.

Each `step` runs one agent turn, or performs the final deterministic export.
It does not automatically run another turn after a human response. `READY`
means another step is available; `WAITING_FOR_HUMAN` means review is required.
The full skill directories are copied and hash-pinned at creation, preserving
sibling references. Instructions explicitly require the skills and their
referenced resources; this is instruction-based use, not automatic plugin installation.

## Review and resume

```text
.venv-workflow/Scripts/python.exe -m workflow review .workflow-runs/my-book
```

The CLI displays the saved gate ID, agent's explanation, structured review items
and their exact labeled excerpts, allowed commands, and bound English checkpoint
where applicable. This is the approval skill's permitted text fallback; there is
no inline HTML host in this iteration.

Save your explicit response as UTF-8 text, for example:

```text
PM001 approve
PM002 move boundary: End after the following dialogue exchange.
```

Use only commands actually offered by the current sheet. Send the exact displayed
gate ID:

```text
.venv-workflow/Scripts/python.exe -m workflow reply .workflow-runs/my-book --gate GATE-ID --response-file response.txt
.venv-workflow/Scripts/python.exe -m workflow step .workflow-runs/my-book
```

The parser binds these fallback lines to the saved sheet/revision. Old gate IDs,
duplicate submissions, changed checkpoint/sheet files, and stale envelope
revisions are rejected. Parsed dispositions are persisted before the next turn.
The domain skill updates its own records and returns a new sheet revision;
the engine does not apply domain choices itself.

An item acceptance does not close a map or chapter review. After all item
dispositions are saved, review the newly returned closure gate and submit its
exact closure command. Resolved items must have matching human receipts;
an agent cannot bypass item review by initially returning an all-resolved sheet.
When the chapter sanity diff is empty, the saved record must explicitly say
`No textual changes proposed`; the separate response is `approve chapter`.
Other responses to that gate are feedback. Translation issue conversations and
passage continuation use their own saved gate IDs and free-text responses.

Once all chapters finish, `review` displays the immutable English outputs beside
their original prepared chapters and an acceptance ID. Accept only after reviewing
the final text:

```text
.venv-workflow/Scripts/python.exe -m workflow accept .workflow-runs/my-book --acceptance-id ACCEPTANCE-ID
.venv-workflow/Scripts/python.exe -m workflow step .workflow-runs/my-book
```

`export/` contains source-ordered Markdown chapters, glossary, voice record, and
a provenance manifest. Export reads accepted snapshots, not arbitrary working
files. It refuses to overwrite differing files. It does not modify the uploaded
source or claim to create a formatted edition.

## State, failures, and recovery

The run directory holds:

| Location | Purpose |
|---|---|
| `state.sqlite3` | Lifecycle state, submitted review receipts, attempts, thread identity, ordered runtime events |
| `input/` | The original file snapshot |
| `skills/` | Pinned complete skill bundle |
| `workspace/` | Agent-writable prepared package and translation project |
| `objects/` | Immutable snapshots named by SHA-256 |
| `export/` | Accepted final Markdown and provenance |

The source snapshot, skill bundle, prepared chapter/asset/manifest hashes, and
completed outputs are checked before advancing. Preparation uses the repository
validator with local source hash checking. Domain checkpoint and sheet snapshots
survive restart. SQLite updates use revision checks, and an OS file lock prevents
two CLI processes from operating on the same run concurrently.

Human waits have no running agent process and do not consume timeout/retry budgets.
`step --timeout SECONDS` bounds an active turn. Ctrl+C records a paused state and
terminates the adapter's App Server process. Runtime permission escalation is
declined: execution requests use `workspace-write`, no network access, and no
automatic approval of commands outside that sandbox. Unsupported runtime requests
receive a protocol error; the skill must use the saved domain-gate mechanism.
The actual filesystem sandbox is supplied by the installed Codex runtime.

Inspect status and events after failure:

```text
.venv-workflow/Scripts/python.exe -m workflow events .workflow-runs/my-book --after 0
.venv-workflow/Scripts/python.exe -m workflow recover .workflow-runs/my-book
.venv-workflow/Scripts/python.exe -m workflow step .workflow-runs/my-book
```

Recovery verifies protected inputs and starts a new thread with saved checkpoints
and any unconsumed user receipt; the domain skill must reconcile that receipt
against its records before applying it. No automatic retry is performed.
After a hard controller crash leaves the database `RUNNING`, stop any surviving
Codex/agent processes before using `recover --confirm-stopped`. This iteration
does not reconcile an active remote turn or terminate an orphan process tree.
Normal successive turns resume the persisted thread.

If an awaiting review was changed, `recover --refresh-gate` requests fresh domain
validation and a new review rather than treating the stale response as approval.
Protected source corruption must be resolved from retained snapshots before
recovery; the command does not silently overwrite user files. `cancel` terminates
an idle run; interrupt an active step first.

## Prototype limits and verification

This is a backend/CLI iteration, not the complete web application. It has no
upload API, React UI, inline review bridge, remote-storage intake, arbitrary DAGs,
cross-run revision routing, or automated source synchronization. Model operations
can still fail or request unavailable tools.

The driver enforces stage order, source identities, review receipts, separate
map/chapter closure, and final artifact acceptance. The skill remains responsible
for two-path drafting, semantic fidelity, exact-once passage assembly, and the
correct application of the Markdown sanity diff. This iteration does not parse
those domain Markdown records into a complete deterministic validator. If the
final chapter differs from the approved sanity-review base, final review flags
that fact and displays the exact resulting text. Final acceptance is mandatory;
a successful model turn alone never exports a manuscript.

Approved map bindings use an immutable proposal copy, separate from the skill's
mutable map approval-status record. Both are retained in the run. Changes to
completed chapter working files are rejected; starting a revision workflow for
them is future work. Mutable glossary/voice files are reread by the skill and
snapshotted at chapter completion; automatic dependency-aware invalidation for
arbitrary external continuity edits is not implemented yet.

Run deterministic tests:

```text
.venv-workflow/Scripts/python.exe -m unittest workflow.tests.test_workflow -v
```

Tests use synthetic manuscripts and a scripted runtime, plus a real subprocess
speaking the App Server JSONL protocol. They cover gates, stale/replayed responses,
source mutation, recovery, concurrent writers, export identity, and protocol
interleaving/timeouts. They do not call a model or establish literary quality.
The implementation session had no Codex executable on PATH, so live provider,
installed-version compatibility, and sandbox behavior still need a local smoke run.
