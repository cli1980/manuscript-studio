# Manuscript workflow engine

A local CLI over the generalized workflow engine (M1, see
[docs/m1-design.md](docs/m1-design.md)). The literary translation template is:

```text
prepare → metadata review → translate (per chapter, passage human gates) → accept → Markdown export
                                                                                  ↓ optional derived run
                                                                         format → verified DOCX
```

Literary drafting and source-grounded prose/fidelity review stay together in the
translation skill. There is no general line-editing or copyediting stage in this
template. Further editorial feedback belongs in translation review.

Implementation modules live in `workflow/src/`:

| Module | Role |
|---|---|
| `registry.py` | Discovers `templates/*/template.json`, validates them, resolves engine classes, computes the engine identity |
| `engine.py` | Base engine: lifecycle, lock, stage walker, template-declared gates, receipts, acceptance, export, retry, stage restart |
| `prepared.py` | Shared preparation stage, prepared-package verification, per-chapter iterations, restart chapter, metadata review |
| `translation.py` | `literary-translation-v1` prompts, translation gate rules, chapter completion, accepted-output publication |
| `editing.py` | `literary-editing-v1`: optional developmental, line, and copy editing, each chapter by chapter with a whole-book pass |
| `formatting.py` | `manuscript-formatting-v1`, a derived template over an accepted-output publication |
| `library.py` | Per-work artifact library with an append-only publication log |
| `service.py` | The service API shared by the CLI and the future web application; run/work index |
| `cli.py` | Thin CLI client of the service |

`storage.py` and `runtime.py` hold per-run SQLite state and the Codex App Server
adapter. Templates live in `templates/`, tests in `tests/`, and architecture
documentation in `docs/`.

### Server root

Every command takes `--server-root` (default `.workflow-runs`):

```text
<server_root>/
  index.sqlite3        works, per-workflow read-only status, runs (a cache; `reindex` rebuilds it)
  works/<work_id>/     engine-owned work library: sources/, work.json, metadata-history/,
                       translation/<target>/, accepted/, objects/, publications.jsonl
  runs/<run_id>/       per-run state.sqlite3, input/, skills/, workspace/, objects/, export/, archive/
```

Uploading a manuscript always creates a new work, even for an identical file. A
work has at most one unfinished run at a time, across all workflows including
formatting. Final acceptance publishes the accepted artifacts into the work
library and makes that workflow read-only on the work.

The case-driven [E2E launcher](tests/run_e2e.py) accepts an explicit workflow
manifest. Live model execution is separate from the deterministic unit-test suite,
which constructs small synthetic inputs without external manuscripts.
The full-length 《刺秦》 case at `tests/cases/translation-ciqing-001/` and its DOCX
under `tests/fixtures/short-story-ciqing/` are optional, Git-ignored local manual
tests. They are preserved locally but are not included in a fresh checkout.

To set up Python dependencies and launch that test in one command:

```text
python workflow/tests/run_e2e.py --case workflow/tests/cases/translation-ciqing-001/case.json --setup
```

This example requires the local case and fixture. `--case` is required; the launcher
never selects a long manuscript implicitly. Codex must already be installed and authenticated. The launcher creates
(through the service, under `--server-root`, default `.workflow-runs/e2e`) or resumes
(`--resume RUN_ID`) a run, presents each human gate, checks restart/replay behavior, verifies
the export, and writes an E2E report. Cases name a `template_id` and a
`manuscript_language`. See the case README for pause/resume, runtime
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

Choose a workflow, then upload one explicitly designated source file (a new work)
or select an existing work. This iteration prepares the whole file, including its
real chapters. Commands after `create` take the printed run ID.

```text
.venv-workflow/Scripts/python.exe -m workflow templates
.venv-workflow/Scripts/python.exe -m workflow create --template literary-translation-v1 --source "C:/Manuscripts/book.md" --manuscript-language zh-CN
.venv-workflow/Scripts/python.exe -m workflow step RUN
.venv-workflow/Scripts/python.exe -m workflow status RUN
.venv-workflow/Scripts/python.exe -m workflow create --template literary-translation-v1 --work WORK_ID
```

`--work` starts the workflow on an existing work's source; it is refused with
`work_busy` while another run on that work is unfinished and with
`workflow_read_only` once that workflow is finalized on the work. Every run
prepares again; confirmed shared metadata is reused from the work library.
`works list`, `works show WORK`, `works publications WORK`, and `works verify WORK`
inspect works and their libraries.

`create --model MODEL` sets the model for every agent; `--agent-model AGENT=MODEL`
sets one agent. The template is snapshotted at creation with the engine identity.
The template declares its stages, gates, agents, and skill bundles; custom
definition files are no longer accepted. An omitted model uses the installed
Codex default. `status RUN` reports `available_actions`, each with `enabled`, the
`reason` when disabled, `irreversible`, and a `confirmation` message.

Each `step` runs one agent turn, re-presents a refreshed metadata review, or
performs the final deterministic export.
It does not automatically run another turn after a human response. `READY`
means another step is available; `WAITING_FOR_HUMAN` means review is required.
The full skill directories are copied and hash-pinned at creation, preserving
sibling references. Instructions explicitly require the skills and their
referenced resources; this is instruction-based use, not automatic plugin installation.

## Review and resume

```text
.venv-workflow/Scripts/python.exe -m workflow review RUN
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
.venv-workflow/Scripts/python.exe -m workflow reply RUN --gate GATE-ID --response-file response.txt
.venv-workflow/Scripts/python.exe -m workflow step RUN
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

### Metadata review

When preparation completes, the run waits at a `metadata_review` gate before any
translation turn. `review` lists every shared `work.json` metadata field with its
value, origin, review status, and confidence, plus unknown and stale fields. No
agent runs at this gate. Edit one field at a time with a JSON value file:

```text
.venv-workflow/Scripts/python.exe -m workflow metadata RUN --gate GATE-ID --field /genres --value-file genres.json --reason "Author correction"
```

Each edit goes through the pinned `prepare_metadata.py set` helper: it increments
`record_revision`, keeps the previous record under `metadata-history/`, and
records the field as a confirmed user edit. The engine also snapshots each
version into the run's object store and logs a `metadata.edited` event. Every
edit at the gate presents a new gate ID, so a confirmation always refers to the
record you last saw. `/manuscript_language` is locked once the run exists.

To continue, reply to the current gate with a response file containing exactly
`confirm metadata` (the service's `confirm_metadata` also binds the inspected
record revision). The confirmation receipt is bound to that revision and hash,
the record is published to the work library, and the next stage becomes `READY`. If
`work.json` is changed outside the gate, the reply is refused; run
`retry RUN --refresh-gate`, then `step`, to present the current record again.
Before the gate is presented, the run adopts the work library's latest shared
metadata, so a later run on the same work starts from the confirmed record.

After confirmation, `metadata RUN --field ... --value-file ...` (without `--gate`)
still edits metadata while no agent turn runs; such edits and agent edits are
recorded as new versions and library publications without re-confirmation.
`metadata-history RUN [--version N]` lists or shows the run's versions. While no
run is unfinished, `works edit-metadata WORK --field ... --value-file ...` edits
the work's shared metadata and `works metadata WORK [--history | --version N]`
shows it.

### Front-matter reviews and the translation brief

Every prepared work starts with one front-matter unit, and the reviews made
before the first chapter belong to it: the shared metadata review, then each
workflow's own front-matter stages. A template marks such a stage with
`"front_matter": true` (a non-iterating agent stage after preparation); its gates
carry the front-matter chapter ID. A gate rule can list `documents`, workspace
files that are snapshotted when the gate is presented and shown to the reviewer;
it must also declare the approval `command`. Any other reply is feedback for the
agent, a changed document invalidates the gate, and the approval completes the
stage without another agent turn. The approval is kept in
`front_matter_approvals` and in the accepted version's `run.json`.

`literary-translation-v1` uses this for its translation brief (stage `brief`):
the agent drafts `translation/glossary.md` and `translation/voice.md` from the
whole prepared manuscript, starting from any files carried from an earlier run,
and translates three randomly picked sample passages three ways each into
`translation/brief-samples.md`. The `brief_samples` gate is an approval sheet
with one item per sample: an `Original` row, one row per variant labelled like
the decision that chooses it (`choose A`, …), and `none of these` (a reason is
required) to ask for new variants. A reply such as `S1 choose A: keeps the
restraint` picks a variant with reasons; deciding every sample closes the poll.
The agent then records accepted and rejected variants with the reasons, and the
`translation_brief` gate presents all three files. Reply `approve brief` to
approve them, or send corrections. The approved files become the chapter stage's
starting point, also after a chapter-stage restart; the samples guide tone and
voice and do not bind later passages.

### Final acceptance

Once all chapters finish, `review` displays the immutable English outputs beside
their original prepared chapters, an acceptance ID, and the finalization notice.
**Acceptance is irreversible:** it publishes the accepted chapters, glossary,
voice, and accepted-output manifest to the work library and makes literary
translation read-only on this work. Nothing in the run can be restarted
afterwards, and changes require adding the manuscript again as a new work.
Accept only after reviewing the final text:

```text
.venv-workflow/Scripts/python.exe -m workflow accept RUN --acceptance-id ACCEPTANCE-ID --confirm-final
.venv-workflow/Scripts/python.exe -m workflow step RUN
```

`export/` contains source-ordered Markdown chapters, glossary, voice record, and
a provenance manifest. Export reads accepted snapshots, not arbitrary working
files. It refuses to overwrite differing files. It does not modify the uploaded
source or claim to create a formatted edition.

## Web application

The Manuscript Studio web application (M3) is a separate client of the same
service API and lives in [`studio/`](../studio/README.md).

## Literary editing (first M4 iteration)

```text
prepare → metadata review → [developmental, optional] → line edit → copyedit → accept → Markdown export
```

Upload the text to edit (for example an accepted translation's assembled
Markdown) as a new work and skip optional stages at creation:

```text
.venv-workflow/Scripts/python.exe -m workflow create --template literary-editing-v1 --source book.en.md --manuscript-language en-US --skip-stage developmental
```

The engine copies the verified prepared chapters verbatim into
`manuscript/chapters/`. Line and copy editing each run chapter by chapter, sharing
`editorial/style-sheet.md`, `continuity-concordance.md`, and `editorial-brief.md`,
and end with a whole-book consistency pass. Each job uses three gates: an
`editorial_review` decision sheet with separate closure (or, with no proposals,
the exact reply `approve review`), then an `apply_authorization` gate requiring
exactly `apply accepted changes`, and only then application. A chapter cannot
complete if its text changed without that authorization, and other chapters
cannot change outside their own jobs. The optional developmental stage collects
chapter evidence and ends with one whole-book verdict and `DEV-###`
recommendations; it never changes text. Final acceptance publishes the edited
chapters under `literary-editing/` and an `accepted-markdown-chapters/1`
publication, so formatting works unchanged. Restarting a completed editorial
chapter, and other details, are deferred to the rest of M4.

## Optional final manuscript formatter

The final formatter consolidates the accepted English chapters into one readable
DOCX. It uses `format-manuscript`, `review-approval-sheet`, `prepare-manuscript`,
and the bundled [local document adapter](adapters/documents-local/SKILL.md).
It does not line-edit or retranslate the manuscript. It is the derived template
[`manuscript-formatting-v1`](templates/manuscript-formatting-v1/template.json): it
reads a work's `accepted-markdown-chapters/1` publication (not a parent run's
state) and uses that output's manuscript language. The built-in builder currently
supports English manuscripts only.

For a work whose translation is finalized:

```powershell
.\.venv-workflow\Scripts\python.exe -m pip install -r workflow/requirements-docx.txt
.\.venv-workflow\Scripts\python.exe -m workflow create --template manuscript-formatting-v1 `
  --work WORK_ID --renderer word --purpose reader-facing
```

`--publication PUB` selects a specific accepted-output publication (default: the
latest). This creates a run under `runs/` and prints its ID; an unchanged request
reuses the existing edition, and `--new-edition` creates a distinct one. Formatting
runs count toward the one-unfinished-run-per-work limit, publish nothing into the
work, and never make formatting read-only. Use the normal commands on that run:

```powershell
.\.venv-workflow\Scripts\python.exe -m workflow step FORMAT-RUN --codex "C:/path/to/codex.exe"
.\.venv-workflow\Scripts\python.exe -m workflow review FORMAT-RUN
.\.venv-workflow\Scripts\python.exe -m workflow reply FORMAT-RUN --gate GATE-ID --response-file response.txt
```

The formatter proposes a manuscript-bound format specification and machine
settings in `format-settings.json`, including the
edition classification, typography, page geometry, section headings, TOC, and
page furniture. Resolve its `FM###` items, run another step to receive the new
closure revision, then explicitly confirm final closure before generation.
The CLI uses the skill's text fallback. `--purpose` also supports
`editorial-review` and `submission`; source wording and order remain protected
for every profile.

The formatting run has its own pinned input/skill snapshots, runtime context,
review records, and SQLite state. It preserves the completed translation run and
the work's publications. Retry failures with `retry` on the formatting run,
subject to the same stopped-process rules as translation.

Document construction and rendering are separate capabilities:

| Component | Windows | Cloud/Linux |
|---|---|---|
| DOCX builder | `python-docx` | The same `python-docx` builder |
| Field/pagination/PDF renderer | Dedicated Microsoft Word COM instance | Isolated headless LibreOffice |
| Page-image generation | PDFium | PDFium |
| Content checks and visual-review gate | Shared workflow checks | The same checks |

Choose `--renderer word` or `--renderer libreoffice`. The default is controlled by
`document_backend.renderer` in the formatting template; `platform-default`
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

The verified result is `runs/<formatting-run>/export/manuscript.docx`, accompanied by
its provenance manifest. Format specifications and render evidence remain in the
job's workspace/snapshots. The accepted English text is the formatter's source;
the original Chinese preparation is never substituted for it.

The E2E launcher can trigger this final operation automatically after export:

```powershell
python workflow/tests/run_e2e.py --case PATH_TO_CASE_JSON --setup --format-docx `
  --renderer word
```

Use `--case PATH_TO_CASE_JSON --resume COMPLETED-TRANSLATION-RUN-ID --format-docx ...` to add it to an existing
E2E run without repeating translation. `--format-purpose` selects the profile.
Explicit `--auto-approve-recommended` also applies to recommended format decisions,
with the same separate-closure and delegated-decision audit rules. Formatting has
its own status in the E2E report; a successful DOCX does not turn unreviewed
translation-quality checks into passes.

## State, failures, and recovery

To monitor status and performance from another terminal without changing the run:

```text
python workflow/tests/monitor_performance.py .workflow-runs/e2e/runs/RUN-ID --watch --output .workflow-runs/e2e/runs/RUN-ID/performance-report.json
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
| `export/` | Accepted final Markdown and provenance (or the DOCX for a formatting run) |
| `archive/` | Workspace paths moved aside by chapter and stage restarts; never deleted |

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
.venv-workflow/Scripts/python.exe -m workflow events RUN --after 0
.venv-workflow/Scripts/python.exe -m workflow retry RUN
.venv-workflow/Scripts/python.exe -m workflow step RUN
```

`retry` verifies protected inputs and starts a new thread with saved checkpoints
and any unconsumed user receipt; the domain skill must reconcile that receipt
against its records before applying it. No automatic retry is performed.
After a hard controller crash leaves the database `RUNNING`, stop any surviving
Codex/agent processes before using `retry --confirm-stopped`. This iteration
does not reconcile an active remote turn or terminate an orphan process tree.
Normal successive turns resume the persisted thread.

If an awaiting review was changed, `retry --refresh-gate` requests fresh domain
validation and a new review rather than treating the stale response as approval.
Protected source corruption must be resolved from retained snapshots before
recovery; the command does not silently overwrite user files. `stop` cancels
an idle run permanently, keeping its artifacts and history; interrupt an active
step first.

There is no checkpoint rollback. When saved state is not sound, restart instead:

```text
.venv-workflow/Scripts/python.exe -m workflow restart-chapter RUN --chapter CHAPTER_ID --reason "..."
.venv-workflow/Scripts/python.exe -m workflow restart-stage RUN --stage translate --reason "..."
.venv-workflow/Scripts/python.exe -m workflow restart RUN --reason "..."
```

- **Restart chapter** archives the chapter's working directory (and, for a
  completed chapter, its output) under `archive/`, resets that chapter to a new
  attempt, and translates only it again. Restarting the chapter in progress
  restores glossary and voice from that chapter's start (the last completed
  chapter's versions plus any edits made between chapters); restarting a completed
  chapter, allowed only when no chapter is in progress, keeps the current ones.
  Outputs stay in source order.
- **Restart stage** archives the workspace paths owned by that stage and every
  later stage and resets their state. Receipts and events are kept; old receipts
  cannot satisfy the new attempt's gates.
- **Restart workflow** stops the run and creates a linked new run of the same
  template on the same work with the current engine. It prepares again and carries
  glossary and voice from the last completed chapter.

All restarts are refused after final acceptance (`run_finalized`). Each run
records an engine identity (a hash of `workflow/src/` and its template directory);
after an engine update an unfinished run allows only reading and `restart`
(`engine_updated`). `import RUN_DIR` registers a pre-M1 run directory as a new
work; a completed translation publishes its accepted output so it can still be
formatted, and other imported runs allow only reading and `restart`.

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
interleaving/timeouts, plus formatting approval/content/QA guards. They also cover
the M1 engine: a test-only template registered from `tests/templates/`, chapter
and stage restarts, workflow restart with carried glossary/voice, engine-update
refusals, library publications and hand-edit conflicts, work-level metadata
edits, import, the CLI, and index rebuilds. They do not call
a model or establish literary or visual quality. Before M1 the live translation
workflow completed the ten-section 《刺秦》 case with Codex on Windows; that run is
separate from the deterministic fixtures and does not establish formatter quality.
The first live formatting attempt using the external desktop Documents package saved a proposal but returned
`blocked-adapter`: the installed Documents instructions were available, while
their required managed runtime and LibreOffice render workflow were not exposed
in that App Server session. Supplying a skill directory alone does not establish
that its construction/render dependencies are usable. The native Word adapter
has separately passed a local build → Word PDF export → TOC convergence → PNG
smoke test. LibreOffice invocation/isolation is covered by unit tests; cloud
rendering still needs verification in its deployed font/runtime environment.
