# Manuscript workflow engine

A local CLI over the generalized workflow engine (M1, see
[docs/m1-design.md](docs/m1-design.md)). The literary translation template is:

```text
prepare → metadata review → manuscript analysis → translation brief → translate (per chapter, passage human gates) → whole-book consistency → accept → Markdown export
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
| `analysis.py` | Shared source-bound analysis stage, coverage/evidence/hash validation, frozen downstream handoff and export |
| `translation.py` | `literary-translation-v1` prompts, translation gate rules, chapter completion, accepted-output publication |
| `editing.py` | `literary-editing-v1`: developmental, line, and copy editing passes chosen by the user, each chapter by chapter with a whole-book pass |
| `interior.py` | Embedded interior-design proposal hand-off, native human review and manuscript/design approval lifecycle |
| `production.py` | Thin standalone-formatter API adapter: persisted exact-plan authorization, checked DOCX candidates and editable delivery |
| `document_audit.py` | Workflow-independent DOCX inspection primitives |
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
work has at most one unfinished supported run at a time. Retired historical
workflows do not occupy that slot. Final acceptance publishes the accepted artifacts into the work
library and makes that workflow read-only on the work.

Manuscript language may be omitted at intake (`--manuscript-language` is an
optional hint). Preparation infers it from the actual text and records evidence;
ready preparation requires a determined language. The engine adopts that result
before downstream stages and selects language-dependent translation defaults
then, rather than treating an unknown language as Chinese or English.

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
git submodule update --init --recursive tools/formattor
.venv-workflow/Scripts/python.exe -m pip install -r workflow/requirements.txt -e tools/formattor
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

Studio intake requires only the manuscript. Preparation produces source-supported
draft metadata, including explicit contributor credits, and detects language and
computes extent. There is no preliminary metadata form or language-hint field.
The post-preparation Overview audit is the single metadata editor, including for
later corrections; the Work page links there rather than offering another form.
Optional unknown fields can remain empty. On reruns, the host retains reviewed
shared metadata and shows source discrepancies at audit; the agent no longer
receives or merges a mutable prior-work-record file.

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

After metadata confirmation, both literary editing and translation run
`manuscript-analysis` before their workflow-specific stages. It produces a
source-bound story ledger, chapter summaries, full neutral synopsis, reading
profile and manifest. The engine checks the thin JSON binding envelope and
freezes the Markdown documents, then hands them directly to the next agents
through `manuscript_analysis`. No extra analysis approval is required.

The common Studio Overview exposes these documents as provisional source
context. Coverage is an agent assertion with checked unit identities and quotes,
not proof of semantic accuracy or author approval. Editing later marks the
handoff as historical when the manuscript text changes. Current text, metadata
and consumer-specific approvals retain authority. Snapshots are included in
accepted publication/export. See the
[handoff contract](../plugins/manuscript-studio/skills/manuscript-analysis/references/workflow-handoff.md).
Existing run definitions and approvals are not silently migrated; use a fresh
run for the new sequence.

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

### Whole-book translation consistency

After every chapter is approved and saved, the translation stage automatically
runs a concluding whole-book job. It checks all source and English chapters
against the glossary and voice records, and proposes only objective
inconsistencies. The `translation_consistency` gate presents one approval sheet:
decide every item, then close the resolved sheet separately. If there are no
findings, explicitly reply `confirm consistency`.

Approved fixes are written to separate candidate files. The engine checks that
each candidate contains exactly the approved replacements and that the saved
source-comparison report matches its source and output hashes before promoting
any candidate. Rejected fixes leave the chapter unchanged. Each applied fix and
its closure receipt are recorded with the chapter and in the accepted version's
`run.json`. See the skill's
[whole-book contract](../plugins/manuscript-studio/skills/literary-translation/references/whole-book-consistency.md).

Retry resumes the consistency job. `restart-chapter --chapter _whole` restarts
only that job; restarting any actual chapter invalidates its consistency review
and schedules a new whole-book attempt after all chapters complete again.

### Final acceptance

Once all chapters and the whole-book consistency pass finish, `review` displays the immutable English outputs beside
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

## Literary editing (M4)

```text
prepare → metadata review → [choose a pass → run it → accept its output]*
  → approve manuscript → design/review → authorize DOCX plan → build/check
  → accept editable DOCX → publish/export
```

Upload the text to edit (for example an accepted translation's assembled
Markdown) as a new work:

```text
.venv-workflow/Scripts/python.exe -m workflow create --template literary-editing-v1 --source book.en.md --manuscript-language en-US
```

After metadata review the run waits at the `passes` select stage. Reply exactly
`run developmental`, `run line`, or `run copy` to start a pass, or `finish` to
review and approve the manuscript (also with no pass at all). Approval starts the
final formatting phase automatically; it does not finalize or publish the run.
There is no early formatting shortcut. When a pass completes, the
run asks you to accept its output (`accept pass`); the accepted text and
editorial files are the next pass's starting point. Passes can run in any order
and repeat; each has its own job folders (`editorial/passes/<NNN>-<pass>/`) and
restart epoch. Before you accept a pass, `restart-stage --stage <pass>` returns
the text and editorial files to the pass's start; accepted passes are final,
and the text cannot change between passes. The select stage is a generic
engine stage kind (`"kind": "select"` with `options`), usable by any template.

The engine copies the verified prepared chapters verbatim into
`manuscript/chapters/`. Line and copy editing each run chapter by chapter, sharing
`editorial/style-sheet.md`, `continuity-concordance.md`, and `editorial-brief.md`,
and end with a whole-book consistency pass. Each job uses two gates: an
`editorial_review` decision sheet, closed by a submission that resolves every
item (closure is implied, since the next gate shows exactly what changes; a
reopening decision gets a new revision), or, with no proposals, the exact reply
`approve review`; then an `apply_authorization` gate requiring
exactly `apply accepted changes`, and only then application. A chapter cannot
complete if its text changed without that authorization, and other chapters
cannot change outside their own jobs. The developmental pass collects
chapter evidence and ends with one whole-book verdict and `DEV-###`
recommendations; it never changes text. Approval freezes the manuscript and
metadata before the interior-design proposal and editable specification review.
Design approval starts the bounded DOCX production phase; generation requires a
separate exact-plan authorization and publication requires final editable-DOCX
acceptance. No PDF/page review or print-ready claim is included.
Reopening manuscript approval invalidates design decisions, while restarting
only design preserves the approved content. Restarting a completed editorial
chapter, and other details, are deferred to the rest of M4.

## Final formatting

Formatting is the last embedded phase after manuscript approval, not a separate
workflow launched from a completed publication. In literary editing it starts
with `interior-design` and the editable specification-review form described
above. The CLI supports the same structured review; ordinary `reply` text cannot
approve a design. `review RUN` displays the proposal, blocking author questions,
vendor advisories, gate ID and exact proposal SHA-256:

```text
python -m workflow review RUN
python -m workflow review-design RUN --gate GATE-ID --proposal-sha256 PROPOSAL-SHA256 --action save --spec-file spec.json
python -m workflow review-design RUN --gate GATE-ID --proposal-sha256 PROPOSAL-SHA256 --action request-revision --feedback-file feedback.txt
python -m workflow review-design RUN --gate GATE-ID --proposal-sha256 PROPOSAL-SHA256 --action approve --answers-file answers.json
```

Use the same `--server-root`, `--execution-profile` and
`--user-execution-profile` options before the command when applicable.
`spec.json` contains exactly `edition_brief`, `design_system` and `role_styles`;
the latter maps every existing text-role ID to its selected style ID. The full
proposal is not a save payload. Source bindings, purpose/vendor/binding and
role scopes remain protected by the same service validation as Studio.
`feedback.txt` contains nonempty revision instructions. `answers.json` maps
every blocking question ID to a nonempty answer; omit `--answers-file` only
when no questions block approval. Each action accepts only its corresponding
file option. Saving changes produces a new gate ID and proposal hash; review
those before the next action, because stale bindings are rejected.

These commands neither invoke an agent nor authorize DOCX generation. A revision
request returns to `READY` for an explicit agent `step`; design approval returns
to `READY` for native planning. The `produce-docx` production stage consumes the
standalone formatter's public `prepare`/`build` API, not the old document adapters or an agent.
Translation composition and rendered-page/print production remain pending.

The native generation gate presents a safe summary and plan hash; the complete
source-bearing plan remains private. Studio can authorize it; the CLI also offers:

```text
.venv-workflow/Scripts/python.exe -m workflow review RUN
.venv-workflow/Scripts/python.exe -m workflow authorize-docx RUN --gate GATE-ID --plan-sha256 PLAN-SHA256
.venv-workflow/Scripts/python.exe -m workflow step RUN
```

Only a single editable-DOCX target is accepted. Missing dependencies, unsupported
source/design features and PDF bundles fail explicitly. Source/design receipts,
exact plan/runtime, candidate bytes and the build manifest are bound by hashes.
A changed plan returns to authorization; retries never overwrite existing files.
Design restarts invalidate stale candidate download IDs and authorizations.
Design-only restarts archive the previous proposals but restore the exact
content-addressed vendor-profile snapshot selected at manuscript approval.
They do not resolve a fresh profile or change that approval. Reopening
manuscript approval instead invalidates the old profile so a new target can
be selected.

After candidate inspection and final acceptance, versioned publication/export
contains `document.docx`, `docx-build.json` and `design-proposal.json` in addition
to the accepted Markdown artifacts. This finalizes only the editable-document
POC edition. It does not calculate fields/pagination, resolve fonts, render pages,
export PDF or certify print readiness. Quick Styles facilitate later Word edits;
those edits do not update workflow snapshots. Existing runs are not migrated.

Manuscript approval can select IngramSpark with paperback/hardcover binding.
The binding variant is automatic, pinned and incorporated into the proposal.
The native design form displays entry choices read-only; reopen manuscript
approval to choose a different purpose/vendor/binding. Source rules and recommendations remain distinct;
advisory geometry checks are not final-PDF preflight or proof of product availability.

The legacy formatter engine/template, adapter skill, work/run launch buttons and
CLI/E2E formatting flags have been removed. Old runs are displayed as `RETIRED`
read-only history, keeping their recorded status, artifacts and decisions.
They cannot resume or accept old `FM###` sheets and do not occupy the
one-unfinished-run slot. This does not cancel, migrate or approve them.

Workflow-neutral construction/rendering utilities remain in
[document_adapters.py](src/document_adapters.py), with DOCX inspection in
[document_audit.py](src/document_audit.py). They are retained foundations for
later rendering/print work, not used by the standalone POC adapter or exposed
as another application route.

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
after an engine update an unfinished run allows reading, `stop` and `restart`
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

Run deterministic tests after installing the standalone formatter as above
(install `requirements-docx.txt` to include retained low-level builder tests):

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
