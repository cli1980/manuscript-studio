# Manuscript workflow — iteration 1

A local CLI prototype of the architecture's durable execution layer:

```text
prepare → translate (chapter/passage human gates) → accept → Markdown export
                                                           ↓ optional/manual
                                                   format → verified DOCX
```

Literary drafting and source-grounded prose/fidelity review stay together in the
translation skill. There is no general line-editing or copyediting stage in this
template. Further editorial feedback belongs in translation review.

Implementation modules live in `workflow/src/`: `engine.py`, `runtime.py`,
`storage.py`, `formatting.py`, and `cli.py`. The package-level `__main__.py` is a thin launcher
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

For explicitly delegated acceptance of the agent's structured recommendations,
add `--auto-approve-recommended`. This preserves the gates and marks decisions as
automated; requests needing clarification or revision stop the run. It does not
mark human-only E2E checks or literary-quality assessments as passed.

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

Python dependencies include the existing preparation validator's dependency and
`markdown-it-py` for comparing accepted Markdown content with formatted DOCX text.
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
The translation template retains this four-stage topology and these skill bundles;
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

## Optional final manuscript formatter

The final formatter consolidates the accepted English chapters into one readable
DOCX. It uses `format-manuscript`, `review-approval-sheet`, `prepare-manuscript`,
and the bundled [local document adapter](adapters/documents-local/SKILL.md).
It does not line-edit or
retranslate the manuscript. The separate
[`definitions/formatting.json`](definitions/formatting.json) describes that agent.

For any completed run, including an existing run created before formatting was added:

```powershell
.\.venv-workflow\Scripts\python.exe -m pip install -r workflow/requirements-docx.txt
.\.venv-workflow\Scripts\python.exe -m workflow format `
  .workflow-runs/my-book `
  --renderer word `
  --purpose reader-facing
```

This creates or reuses a job under `<run>/formatting/edition-.../` and prints its
path. Use the normal commands on **that job directory**:

```powershell
.\.venv-workflow\Scripts\python.exe -m workflow step "PRINTED-FORMATTING-JOB" --codex "C:/path/to/codex.exe"
.\.venv-workflow\Scripts\python.exe -m workflow review "PRINTED-FORMATTING-JOB"
.\.venv-workflow\Scripts\python.exe -m workflow reply "PRINTED-FORMATTING-JOB" --gate GATE-ID --response-file response.txt
```

The formatter proposes a manuscript-bound format specification and machine
settings in `format-settings.json`, including the
edition classification, typography, page geometry, section headings, TOC, and
page furniture. Resolve its `FM###` items, run another step to receive the new
closure revision, then explicitly confirm final closure before generation.
The CLI uses the skill's text fallback. `--purpose` also supports
`editorial-review` and `submission`; source wording and order remain protected
for every profile.

The job has its own pinned input/skill snapshots, runtime context, review records,
and SQLite state. It preserves the completed translation run and its acceptance.
Repeated unchanged requests reuse the same job; use `--new-edition` to request a
distinct edition, preserving prior results. Resume failures with `recover` on
the formatting job, subject to the same stopped-process rules as translation.

Document construction and rendering are separate capabilities:

| Component | Windows | Cloud/Linux |
|---|---|---|
| DOCX builder | `python-docx` | The same `python-docx` builder |
| Field/pagination/PDF renderer | Dedicated Microsoft Word COM instance | Isolated headless LibreOffice |
| Page-image generation | PDFium | PDFium |
| Content checks and visual-review gate | Shared workflow checks | The same checks |

Choose `--renderer word` or `--renderer libreoffice`. The default is controlled by
`document_backend.renderer` in `definitions/formatting.json`; `platform-default`
selects Word on Windows and LibreOffice elsewhere. Builder code, renderer identity,
settings, and the accepted manuscript are bound to the edition. Switching renderers
creates a distinct edition and requires fresh design review/rendering/QA; page
numbers from Word are not reused for LibreOffice.

After specification closure, the host records the closure, constructs the DOCX,
and runs the selected renderer without another model-authored builder script.
It reads actual heading destinations from the PDF outline and rebuilds the static
linked TOC until page numbers converge. All PDF pages are rasterized to PNG.
Only then does the formatting agent inspect every page and record visual QA.
Generated files and their hashes cannot be edited by the agent; design corrections
go through a new specification review and a fresh build.

Word requires a local Windows session with Microsoft Word installed. The worker
uses `DispatchEx`, refuses an instance with existing documents, and closes only its
own generated document/application. Active COM rendering is bounded by a timeout;
an interrupted worker may require closing its isolated orphan Word instance.
The renderer is trusted host code over job-local paths, rather than a request to
relax the Codex agent's sandbox.

For cloud deployment, install LibreOffice Writer, fontconfig, and the approved
fonts in the image, plus `requirements-docx.txt`. `pywin32` is Windows-only and is
not installed on Linux. The LibreOffice process uses a private user profile.
Missing fonts fail rather than silently substituting an unapproved face.

An external Documents skill is still supported through `--documents-skill PATH`,
instead of `--renderer`; it must provide its own usable toolchain/render contract.
The earlier desktop-managed Documents package remains incompatible with this
standalone environment, but is no longer the default. Missing selected capabilities
produce `blocked-adapter`; visual review is never bypassed.

Completion requires:

- A current specification closure and exact source/specification/output hashes.
- One DOCX containing all accepted manuscript paragraphs in source order, with
  semantic heading/title styles and no unapproved additional prose.
- Automatic page-number fields for multi-page editions, and declared TOC entries
  using TOC styles rather than duplicated manuscript paragraphs.
- A QA manifest and hashed PNG evidence for every rendered page, with recorded
  visual inspection and specification-conformance results.

The host checks paragraph text/order, headings, identities, and evidence
completeness. Visual inspection and layout conformance are agent attestations,
not independently proven by a PNG's existence. The current content audit supports
ordinary paragraph/heading Markdown with inline emphasis, links, and line breaks;
unsupported blocks such as images, raw HTML, and thematic-break markup are
rejected rather than silently omitted. More specialized literary structures
need an extended audit contract before delivery.

The verified result is `<formatting-job>/export/manuscript.docx`, accompanied by
its provenance manifest. Format specifications and render evidence remain in the
job's workspace/snapshots. The accepted English text is the formatter's source;
the original Chinese preparation is never substituted for it.

The E2E launcher can trigger this final operation automatically after export:

```powershell
python workflow/tests/run_e2e.py --setup --format-docx `
  --renderer word
```

Use `--resume COMPLETED-TRANSLATION-RUN --format-docx ...` to add it to an existing
E2E run without repeating translation. `--format-purpose` selects the profile.
Explicit `--auto-approve-recommended` also applies to recommended format decisions,
with the same separate-closure and delegated-decision audit rules. Formatting has
its own status in the E2E report; a successful DOCX does not turn unreviewed
translation-quality checks into passes.

## State, failures, and recovery

To monitor status and performance from another terminal without changing the run:

```text
python workflow/tests/monitor_performance.py .workflow-runs/e2e/RUN-DIRECTORY --watch --output .workflow-runs/e2e/RUN-DIRECTORY/performance-report.json
```

Omit `--watch` for a one-time table; `--interval` defaults to 60 seconds.
The report separates startup, tool intervals, other runtime time, and post-turn
handling, and records per-turn tokens, cached input, context growth, and phase
averages. Overlapping tool intervals and repeated cumulative token snapshots are
not double-counted. Active turns are provisional and excluded from finished-turn
totals. Other runtime time includes inference, generation, network/provider waits,
and event handling; the current trace cannot separate those costs. The monitor
opens SQLite read-only and never starts a model turn or changes workflow state.
It also separates local delegated-response submission from model work following
each receipt: map-decision recording, drafting/source review, issue application,
chapter sanity review, and approved-chapter delivery. These categories are inferred
from gate transitions; mixed review/application turns are not labeled pure approval
overhead. `work_groups` and `delegated_approval_timing` contain the detailed split.

The run directory holds:

| Location | Purpose |
|---|---|
| `state.sqlite3` | Lifecycle state, submitted review receipts, attempts, thread identity, ordered runtime events |
| `input/` | The original file snapshot |
| `skills/` | Pinned complete skill bundle |
| `workspace/` | Agent-writable prepared package and translation project |
| `objects/` | Immutable snapshots named by SHA-256 |
| `export/` | Accepted final Markdown and provenance |
| `formatting/` | Optional isolated formatting jobs, specifications, page evidence, and DOCX exports |

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

Run deterministic tests (install `requirements-docx.txt` to include builder tests):

```text
.venv-workflow/Scripts/python.exe -m unittest workflow.tests.test_workflow -v
```

Tests use synthetic manuscripts and a scripted runtime, plus a real subprocess
speaking the App Server JSONL protocol. They cover gates, stale/replayed responses,
source mutation, recovery, concurrent writers, export identity, and protocol
interleaving/timeouts, plus formatting approval/content/QA guards. They do not call
a model or establish literary or visual quality. The live translation workflow
has also completed the ten-section 《刺秦》 case with Codex on Windows; that run is
separate from the deterministic fixtures and does not establish formatter quality.
The first live formatting attempt using the external desktop Documents package saved a proposal but returned
`blocked-adapter`: the installed Documents instructions were available, while
their required managed runtime and LibreOffice render workflow were not exposed
in that App Server session. Supplying a skill directory alone does not establish
that its construction/render dependencies are usable. The native Word adapter
has separately passed a local build → Word PDF export → TOC convergence → PNG
smoke test. LibreOffice invocation/isolation is covered by unit tests; cloud
rendering still needs verification in its deployed font/runtime environment.
