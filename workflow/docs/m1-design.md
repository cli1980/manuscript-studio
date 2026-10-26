# M1 design draft — Generalized workflow engine

**Status:** Owner-reviewed design (2026-10-26 session); all open questions were
answered and are incorporated below. Implementation has not started except the
metadata review gate (section 7).\
**Milestone:** [M1 in roadmap.md](../../roadmap.md#m1--generalized-workflow-engine)\
**Inputs:** 2026-10-26 design discussion (decisions 1–8 below).

## Decisions this draft is based on

1. Templates combine JSON (declarative) with Python code (behavior).
2. Derived engines are reusable across workflows (e.g., literary edit also needs
   `FormattingEngine`).
3. Pause/resume move to M3.
4. The CLI accepts a server root as an argument.
5. Metadata can be edited only after preparation completes, and metadata
   inspection/editing becomes a required workflow step.
6. `source_language` is unified as `manuscript_language`.
7. Artifacts are shared per work across workflows through an engine-owned work
   library under the server root. Git versioning is a future consideration.
8. No checkpoint rollback. Recovery is retrying the current step, restarting one
   stage, restarting one chapter, or restarting the entire workflow. In literary
   translation each chapter is a repeated stage instance that the user can
   restart; restarting reuses the already established glossary and voice. Losing
   one chapter's in-progress work to an exception is acceptable as long as the
   chapter can be restarted. Once the workflow is finalized (final acceptance,
   then export to `COMPLETED`), nothing in it can be restarted and that workflow
   becomes read-only on its work; other workflows can still run on the work
   later. A work has at most one unfinished run at a time.
   There is no re-run: to make changes, the user starts from scratch by adding
   the manuscript again, which always creates a new work with a new ID. The GUI
   must notify users prominently so they don't miss this.

## 1. Layering

```text
CLI (thin client, --server-root)        Web API (M3)
              \                         /
               WorkflowService  (workflow/src/service.py)
               |  run/work index (server_root/index.sqlite3), owner, run IDs
               |  WorkLibrary (server_root/works/<work_id>/): checkout, publish, publications
               |
          Registry  -> template.json + engine class
               |
   Engine (base: lifecycle, lock, stage walker, gates, receipts, metadata, accept, export)
     ├─ PreparedManuscriptEngine (prepare stage, prepared-package verify, chapter iteration)
     │    ├─ TranslationEngine      (literary-translation-v1)
     │    └─ LiteraryEditEngine     (M4)
     └─ FormattingEngine            (derived template: manuscript-formatting-v1)
               |
          Store (per-run state.sqlite3 + objects/, unchanged) · Runtime (unchanged)
```

## 2. Templates = JSON + Python (decision 1)

- **JSON** declares *what*: stages and their kinds, agents/skill bundles, gate
  rules, locked metadata fields, produced/consumed artifact contracts, work
  library checkout/publish rules (section 9), the workspace paths each stage
  owns (section 10), and the engine class.
- **Python** implements *how*: prompts, cross-gate rules, and domain completion
  validation.
- Location: `workflow/templates/<name>/template.json`, next to the engine module.
  Several templates may reference the same engine class with different JSON.

```json
{
  "id": "literary-translation-v1",
  "title": "Literary translation",
  "engine": "workflow.src.translation:TranslationEngine",
  "target_language": "en-US",
  "locked_metadata": ["/manuscript_language"],
  "agents": { "prepare": {"...": "as today"}, "translate": {"...": "as today"} },
  "library": {
    "checkout": ["prepared", "work.json", "translation/{target}/glossary.md", "translation/{target}/voice.md"],
    "publish": {
      "prepare":  ["sources", "prepared", "work.json#preparation"],
      "metadata": ["work.json#metadata"],
      "accept":   ["translation/{target}/glossary.md", "translation/{target}/voice.md",
                   "translation/{target}/translated_english", "work.json#workflows.literary-translation"]
    }
  },
  "gates": {
    "passage_map":       {"sheet": "required", "binding": "required", "closure": "required"},
    "translation_issue": {"sheet": "optional", "binding": "required"},
    "chapter_sanity":    {"sheet": "optional", "binding": "required", "closure": "required"},
    "continuation":      {},
    "question":          {}
  },
  "stages": [
    {"id": "prepare",   "kind": "agent", "agent": "prepare", "gates": ["question"],
     "owns": ["prepared/"]},
    {"id": "metadata",  "kind": "metadata_review"},
    {"id": "translate", "kind": "agent", "agent": "translate", "iterate": "chapters",
     "gates": ["passage_map", "translation_issue", "chapter_sanity", "continuation", "question"],
     "owns": ["translation/"],
     "iteration": {
       "owns": ["translation/.literary-translation-work/{work_id}/{chapter_id}/"],
       "carry_forward": ["translation/glossary.md", "translation/voice.md"],
       "restartable": true
     }},
    {"id": "accept",    "kind": "acceptance"},
    {"id": "export",    "kind": "export"}
  ],
  "produces": "accepted-markdown-chapters/1"
}
```

**Registry:** discovers `workflow/templates/*/template.json`, validates each
against a template schema, and resolves `engine` to a class.
`registry.register(path)` adds a template at runtime (used by the test-only
template). Runs continue to pin the full template JSON in state (today's
`definition`), and additionally record the engine code hash (section 10,
"Engine updates"), as formatting already does for `document_adapters.py`.

**Engine hooks** (the base implements everything else):

| Hook | Replaces today's |
|---|---|
| `stage_prompt(state, stage)` | `prompt()` |
| `on_waiting(state, stage, result)` | translation-specific parts of `_wait()` (e.g., map closure before drafting) |
| `on_completed(state, stage, result)` | `_prepared()`, `_translated()` |
| `on_closure(state, gate)` | `_record_closure()` |
| `verify_extra(state)` | subclass parts of `verify()` |
| `accepted_output(state)` | direct reads of `state["outputs"]` by other code |

The result schema's `gate` enum is built per stage from JSON, so `RESULT_SCHEMA`
no longer hard-codes translation gates. Generic gate mechanics move to the base:
`item_signature`/`_verify_dispositions`, binding checkpoints, the sheet-reuse
ban, and enforcement of `required`/`closure` from the `gates` block.

## 3. Stage kinds

| Kind | Behavior |
|---|---|
| `agent` | Runs an agent turn. `iterate: "chapters"` makes the stage repeat once per prepared chapter; each chapter is a stage instance with its own status, attempt count, thread, gates, and approvals (section 10). |
| `metadata_review` | No agent. Waits for a human to inspect, optionally edit, and confirm metadata (section 7). |
| `acceptance` | Final artifact acceptance bound to output hashes (today's `accept`). |
| `export` | Write-once export; never overwrites a differing destination (today's `_export`). Files come from a hook. |

The pipeline walker follows `stages` instead of hard-coded stage names. Existing
statuses are unchanged: `READY`, `RUNNING`, `WAITING_FOR_HUMAN`,
`WAITING_FOR_ACCEPTANCE`, `BLOCKED`, `FAILED`, `PAUSED`, `COMPLETED`,
`CANCELLED`.

## 4. Reusable derived engines (decision 2)

Today `FormattingEngine.create_from_run` reads translation state directly
(`outputs[].chapter_id`, `acceptance.hashes`, the `kind != "manuscript-formatting"`
check, hard-coded `source_language: "en"`, and "English" in its prompt).

- **Derived templates.** Formatting becomes a registered template with
  `"consumes": "accepted-markdown-chapters/1"` and no intake stage.
- **Output contract.** Any template with
  `produces: accepted-markdown-chapters/1` implements
  `accepted_output(state) -> {manuscript_language, chapters: [artifact…], acceptance}`.
  Translation and literary edit both implement it, so both can be formatted
  without changing `FormattingEngine`.
- `service.create_derived_run(work_id, publication_id, "manuscript-formatting-v1", options)`
  checks that the accepted-output publication's contract matches the derived
  template's `consumes`. Translation publishes its `accepted_output()` to the
  work library at final acceptance (section 9), so a derived run reads that
  publication instead of a parent run's state and no longer needs the parent
  run directory. Derived runs live under `runs/<id>` like any other run.
- Formatting uses the manuscript language of the output it formats: the
  publication's `manuscript_language` (`en-US` for a translation; the
  manuscript's own language for a literary edit) becomes the derived run's
  `manuscript_language`. The formatting prompt and checks are parametrized by
  it instead of hard-coding English; English-only literals in the checks (such
  as the `Contents`/`Table of Contents` labels) come from the approved format
  specification for that language.
- `PreparedManuscriptEngine` holds the shared prepare stage, prepared-package
  verification, and chapter iteration, so literary edit (M4) reuses it instead of
  copying translation code.

## 5. Service API

Pause/resume move to M3 (decision 3). `KeyboardInterrupt` still yields `PAUSED`
as today.

```text
list_templates()
list_works(owner=None) · get_work(work_id) · work_publications(work_id, artifact=None)
create_run(template_id, *, upload=None, manuscript_language=None, work_id=None, owner, model=None) -> run_id
    # exactly one of: upload (+ manuscript_language) -> new work, or work_id -> existing work's source
create_derived_run(work_id, publication_id, template_id, *, owner, options) -> run_id
list_runs(owner=None, work_id=None) · get_run(run_id)   # includes available_actions (section 10)
step(run_id, runtime)
reply(run_id, gate_id, text)
accept(run_id, acceptance_id)
retry(run_id, *, confirm_stopped=False, refresh_gate=False)     # today's recover()
restart_stage(run_id, stage, *, reason)                          # section 10
restart_chapter(run_id, chapter_id, *, reason)                   # section 10
restart_workflow(run_id, *, reason, fresh_preparation=False) -> run_id
stop(run_id)                                                    # today's cancel()
events(run_id, after=0)
get_metadata(run_id) · edit_metadata(run_id, field, value, rationale)
metadata_history(run_id) · metadata_version(run_id, record_revision)
confirm_metadata(run_id, gate_id, record_revision)
```

## 6. Server root, run index, and CLI (decision 4)

```text
<server_root>/
  index.sqlite3        works(id, title, owner, source_sha256, created_at)
                       work_workflows(work_id, workflow, status, finalized_run_id)   # status: open | read_only
                       runs(id, template_id, work_id, owner, restart_of, path, status, stage, created_at, updated_at)
  works/<work_id>/     work library (section 9)
  runs/<run_id>/       existing per-run layout, unchanged
```

- Per-run `state.sqlite3` remains authoritative. The index caches status/stage,
  is updated by the service after each operation, and can be rebuilt with a
  `reindex` command.
- CLI:
  `python -m workflow --server-root .workflow-runs create --template literary-translation-v1 (--source FILE --manuscript-language zh-CN | --work WORK_ID)`.
  `--source` always creates a new work; `--work` starts this workflow on an
  existing work using its source.
  Subsequent commands take a run ID instead of a run directory. The owner
  defaults to the OS user name. `.workflow-runs/` is already gitignored and used
  in the README, so it is the natural documented default.
- New commands: `works list`, `works show WORK_ID`, `retry RUN` (today's
  `recover`), `restart-stage RUN --stage STAGE --reason TEXT`,
  `restart-chapter RUN --chapter CHAPTER_ID --reason TEXT`, and
  `restart RUN --reason TEXT [--fresh-preparation]`.
- `import RUN_DIR` registers existing run directories into the index.
- `workflow/tests/run_e2e.py` and `workflow/README.md` are updated accordingly.

## 7. Required metadata review and versioning (decision 5)

**Implemented early (2026-10-26, current engine):** the
literary-translation workflow now has the engine-owned `metadata_review` gate
between `prepare` and `translate`. It is presented when preparation completes;
`Engine.edit_metadata` / `python -m workflow metadata` edits one field through
the pinned `prepare_metadata.py set` helper and presents a new gate ID; a reply of
exactly `confirm metadata` records `state.metadata_approval` (record revision,
hash, receipt, decision source) and moves the run to `translate`.
`/manuscript_language` is locked. External `work.json` changes invalidate the
gate until `recover --refresh-gate` + `step`. Under
`--auto-approve-recommended`, the E2E launcher confirms it only on the completed
preparation turn's `confirm metadata` recommendation and only if no edit
followed. Still M1 work: the `metadata_review` stage kind in the registry,
`metadata_versions` / history listing APIs, and agent-edit detection after turns.

- When preparation completes, the run enters stage `metadata` with status
  `WAITING_FOR_HUMAN` and gate kind `metadata_review`.
- `get_metadata` returns current `work.json` metadata, provenance,
  missing/stale fields, and locked fields.
- `confirm_metadata(gate_id, record_revision)` binds confirmation to the exact
  revision the user inspected (stale revisions are rejected), records a receipt,
  and advances to the next stage.
- **Edits:**
  - Refused before preparation completes (no `work.json` exists yet).
  - Go through the run's pinned `prepare_metadata.update(..., operation="set")`,
    which already increments `record_revision` and writes `metadata-history/`.
  - Taken under the run lock. `advance()` holds that lock for the whole agent
    turn, so edits during a turn are refused automatically. A crashed `RUNNING`
    run is also refused.
  - Fields in the template's `locked_metadata` (`/manuscript_language` for
    translation) are refused at any time after run creation.
  - **After confirmation**, edits remain allowed while the run is unfinished
    and no agent turn is running (`edit_metadata` outside the gate), and agents
    may edit metadata during a turn. Later runs of other workflows on the work
    may also edit it through their own metadata gate. They are only
    recorded in history: a new version, a `metadata.edited` (or
    `metadata.changed_by_agent`) event, and a library publication. They do not
    require re-confirmation or reopen the gate; later agent turns read the
    latest metadata. A finalized workflow keeps the metadata snapshot it used.
- **History:** `metadata-history/` lives in the agent-writable workspace, so the
  engine also snapshots each version into the content-addressed `objects/` store
  and keeps
  `state.metadata_versions = [{record_revision, sha256, actor, created_at, fields}]`.
  Each edit records a `metadata.edited` event.
- **Agent edits:** after each agent turn, the engine compares `record_revision`.
  If the agent changed metadata, it snapshots the new version and records a
  `metadata.changed_by_agent` event, so history stays complete.
- **Library sync:** the library's `work.json` holds the shared metadata for all
  workflows. Before presenting the gate, the engine copies the library's latest
  metadata and provenance into the run's copy. Confirmation publishes the
  confirmed record back to the library (section 9). Only one run per work is
  active, so the library record changes only through that run or a hand edit;
  if a hand edit changed it in the meantime, the publish is refused and the gate
  is presented again with the newer record.

## 8. `manuscript_language` unification (decision 6)

- Rename the run-state key `source_language` → `manuscript_language`, the CLI
  flag `--source-language` → `--manuscript-language`, the prompt context key,
  the formatting state field, and the e2e case spec field. `target_language`
  stays.
- The v1 `work.json` field `source_language` in the skill schema is **not**
  renamed; the engine already handles both via its `language_key` switch.
- A small shim in `Store.load` renames the key for existing runs in memory; the
  next save persists it.

## 9. Per-work artifact library (decision 7)

Each work has one engine-owned folder for artifacts that outlive a run and are
shared across workflows (translation, literary edit, formatting). It follows the
preparation contract's "one package per work … shared by several workflows" and
architecture §7.3's binding of downstream inputs to explicit versions.

```text
<server_root>/works/<work_id>/
  work.json                  shared metadata + workflows summary (authoritative library copy)
  metadata-history/          previous work.json records
  sources/<sha256>.<ext>     every uploaded original, immutable
  prepared/revisions/rNNNN/  published prepared revisions (manifest, chapters, assets), immutable
  translation/<target>/      latest accepted glossary.md, voice.md, translated_english/
  editing/                   literary edit artifacts (M4)
  objects/<sha256>           every published version, content-addressed
  publications.jsonl         append-only publication log
  .library.lock
```

**Ownership and identity**
- Only the engine writes to the library. Agents never receive library paths;
  they work in their run workspace. Users browse the library read-only through
  the CLI/GUI.
- Uploading a manuscript always creates a new work with a new ID, even when the
  file is identical to an existing work's source; no duplicate detection or
  linking is done. The service assigns work IDs (a slug from the title or
  filename plus a short suffix). The preparation prompt receives the required
  `work_id`, and the engine rejects a prepared `work.json` with a different one.
- To run another workflow on an existing work (for example a literary edit of
  a manuscript whose translation has completed), the user selects that work
  instead of uploading; the run uses the work's source and published artifacts.

**Checkout** (template `library.checkout`, at run creation)
- Copies the latest published versions into the run workspace and records
  `state.inputs = [{artifact, publication_id, sha256}]`.
- Translation checks out the shared `work.json`, the prepared package when a
  ready published revision binds the same source hash, and the target language's
  `glossary.md` and `voice.md`.
- The run's copies are then pinned as today; `verify()` is unchanged.

**Publish** (template `library.publish`, engine-verified, under the library lock)

| Event | Publishes |
|---|---|
| Preparation completes with a new revision | `sources/`, `prepared/revisions/rNNNN/`, `work.json` preparation fields |
| Metadata confirmed | `work.json` metadata and provenance (new `record_revision`) |
| Final acceptance | `translation/<target>/` glossary, voice, and accepted chapters; `work.json` `workflows.literary-translation`; then literary translation becomes read-only on this work |

- Unaccepted work (draft chapters, open sheets, in-progress glossary/voice) is
  never published.
- Each publication appends
  `{id, created_at, run_id, workflow, stage, artifact, path, sha256, version, basis: {prepared_revision, metadata_record_revision}, receipts, supersedes}`
  and materializes the new version as the browsable latest file. Superseded
  versions remain in `objects/`, giving history without Git.
- The `workflows.<name>` summary becomes engine-maintained at publish time;
  agent edits to it in the run workspace are not published.

**Concurrency: one run per work**
- A work has at most one unfinished run at a time, across all workflows,
  including formatting runs. `create_run` and `create_derived_run` refuse with
  `work_busy` (naming the active run) until that run is `COMPLETED` or
  `CANCELLED`. `restart_workflow` cancels the old run before creating the new
  one, so it is not blocked by this rule.
- Workflows on the same work therefore run one after another, never in
  parallel. Users who want parallel attempts upload the manuscript again,
  which creates a separate work.
- Publishing still uses compare-and-swap as a safety check: a publish names the
  publication it was based on (from checkout). With one run per work, the head
  moves only through a hand edit to the library; in that case the publish is
  refused. For metadata, the gate is presented again with the newer record
  (section 7); for other artifacts the run becomes `BLOCKED` with the reason.

**Read-only workflows**
- Read-only applies per workflow on a work, not to the whole work. Each
  (work, workflow) pair is `open` until a run of that workflow on the work is
  finalized (section 10); it then becomes `read_only` permanently.
- A read-only workflow refuses new runs of that workflow on the work and any
  change to its library area (for translation, `translation/<target>/`) and to
  its `work.json` `workflows.<name>` summary. Its files and publication history
  stay readable.
- Other workflows on the same work are unaffected: once no run is active, they
  can start runs, confirm and publish metadata, publish new prepared revisions,
  and publish into their own areas. A finalized workflow keeps its recorded
  `basis_revision` and metadata snapshot; later shared changes do not alter it.
- Derived runs (formatting) may read a read-only workflow's accepted-output
  publication. Formatting requires a finalized translation, so this is its
  normal case. Their outputs stay in the derived run's own folder
  (`runs/<id>/export/`) and are not published into the work. Because formatting
  publishes nothing into the work, completing a formatting run does not make
  formatting read-only: further editions can be formatted later, one run at a
  time.
- To redo a finalized workflow, the user adds the manuscript again, which
  creates a new work with a new ID from scratch: new preparation, metadata
  review, and an empty glossary and voice. Nothing is copied from the old work.

**Direct edits and staleness**
- A hand edit to a library file (for example `glossary.md`) is detected by hash
  mismatch against its head publication at the next checkout or `works verify`.
  It is recorded as a new `user_edit` publication with unreviewed status, never
  silently used or overwritten.
- A new prepared revision marks publications based on an older revision stale in
  the workflows summary, following the preparation contract, without deleting
  them.

## 10. Restart semantics (decision 8)

Rollback to an arbitrary checkpoint is out of scope. Four recovery operations:

| Operation | Effect | Today |
|---|---|---|
| `retry` | Retry the current step from saved state with a fresh agent thread after a failure, block, or interruption. `refresh_gate` presents the current gate again. | `recover()` |
| `restart_chapter` | Discard one chapter's work and translate that chapter again, reusing the established glossary and voice. | new |
| `restart_stage` | Re-run one stage of the same run from its start. | new |
| `restart_workflow` | Start a new run of the same template on the same work and source. | new (manual re-create) |

Use `retry` first when the saved chapter state is still sound. Use
`restart_chapter` when it is not (for example after an exception left the
chapter's records inconsistent), or when the user wants a completed chapter
translated again.

**Chapters as repeated stage instances**
- `state.chapter_index` is replaced by one record per prepared chapter:
  `state.iterations = [{chapter_id, status, attempt, output, continuity_after, restarts}]`
  with status `pending`, `in_progress`, or `completed`. The stage works on the
  first chapter in source order that is not completed.
- Thread, domain state, gate, map approval, and sanity approval remain
  chapter-scoped, as today.
- The prompt tells the agent the exact chapter working directory
  (`translation/.literary-translation-work/<work_id>/<chapter_id>/`), so the
  engine can archive it deterministically.
- At each chapter completion the engine snapshots `glossary.md` and `voice.md`
  into `continuity_after` on that chapter's record, keeping every chapter's
  established version instead of replacing a single `state.continuity`.

**Glossary and voice rule (all restarts)**
- Every restart starts from the glossary and voice of the **last completed
  chapter**: the most recent `continuity_after` snapshot by completion time, so
  the accumulated understanding is never lost. Only provisional changes from an
  abandoned, uncompleted attempt are discarded. If no chapter has completed yet,
  the run's library checkout is used.
- User edits made to the working copies since that chapter completed (with no
  chapter in progress) are kept; the skill treats direct user edits as binding.
- **Completed chapters are frozen.** A completed chapter keeps the text it was
  translated with; later glossary or voice changes are not applied to it, and
  it is not flagged for review. To apply updated terminology to a completed
  chapter, the user restarts that chapter. `verify()` already rejects any change
  to a completed chapter's output outside the run's approval lifecycle.

**Point of no return: finalization**
- A run is **finalized** once final acceptance is recorded: acceptance publishes
  the accepted artifacts to the library and the export follows, ending in
  `COMPLETED`. `CANCELLED` runs are also closed.
- Finalization makes the run's workflow read-only on its work (section 9).
  Other workflows can start on that work once the run is `COMPLETED`.
- A finalized run cannot restart any chapter or stage, cannot be restarted as a
  workflow, and `retry` applies only to a failed export step. These operations
  refuse with a `run_finalized` error stating that changes require adding the
  manuscript again as a new work. Creating another run of the same workflow on
  the work is refused with `workflow_read_only`.
- There is no re-run of a finalized run. The finalized run, its export, its
  publications, and formatting outputs derived from them stay unchanged.
- **Notification requirements** (service provides, GUI presents):
  - `get_run` returns `available_actions`, each with `enabled`, `reason` when
    disabled, `irreversible`, and a `confirmation` message. Final acceptance is
    marked `irreversible`.
  - Before final acceptance, the GUI shows a prominent notice, not only a
    tooltip, that accepting finalizes the run and makes this workflow read-only
    on the work: no chapter or stage can be restarted afterwards, no new run of
    this workflow can start on the work, and any change requires adding the
    manuscript again as a new work. Acceptance requires an explicit
    confirmation of that notice; the confirmation is recorded with the
    acceptance receipt.
  - After finalization, the run view, and that workflow's section of the work
    view, show a persistent banner stating that the run is final and the
    workflow is read-only on this work. Its restart controls and the option to
    start the same workflow on this work are hidden or disabled with that
    reason; the related action offered is adding the manuscript as a new work.
    Starting other workflows on the work becomes available once the run is
    `COMPLETED`.
  - The CLI prints the same notice in `review` at the acceptance gate and in
    the output of `accept`.

**Restart chapter**
- Allowed for literary translation in any run that is not `RUNNING`,
  finalized, or `CANCELLED`:
  - **The chapter in progress** (including after a failure, block, or pending
    gate): its in-progress work is discarded.
  - **A completed chapter**, only when no other chapter is in progress (between
    chapters, or waiting for final acceptance). Otherwise the user must finish
    or restart the chapter in progress first.
- The engine moves the chapter's working directory, and for a completed chapter
  its output file, to `<run>/archive/chapter-<chapter_id>-<attempt>/`. Nothing
  is deleted.
- **Glossary and voice** follow the rule above:
  - Restarting the chapter in progress archives the working copies (which may
    contain provisional changes from the abandoned attempt) and restores both
    files from the last completed chapter's snapshot. Decisions recorded only
    during the abandoned attempt are lost by design.
  - Restarting a completed chapter (possible only between chapters) keeps the
    working copies, which already equal the last completed chapter's snapshot
    plus any user edits since. So a restarted early chapter benefits from
    terminology established in later chapters. Earlier entries pinned to the
    restarted chapter stay; the agent appends new pinned entries rather than
    overwriting, as the skill requires.
- The chapter's record is reset to `pending` with `attempt + 1`, and its
  chapter-scoped state is cleared. A completed chapter's previous output is
  removed from `outputs` and kept in the record's `restarts` as superseded.
- Other chapters, their outputs, and their receipts are unaffected. Receipts and
  events for the restarted chapter are retained; they cannot satisfy new gates
  because they are bound to old gate and sheet identities.
- If the run was waiting for final acceptance (not yet accepted), it returns to
  the `translate` stage for that chapter, then comes back to acceptance with a
  new acceptance ID covering the new output.
- Glossary or voice changes made while translating the chapter again apply only
  to chapters translated afterwards. Other completed chapters stay frozen
  unless the user restarts them.

**Restart stage**
- Allowed when the run is not `RUNNING`, finalized, or `CANCELLED`, and only for
  the current stage or an earlier one.
- Each stage declares the workspace paths it owns (`owns` in the template). The
  engine moves the owned paths of the target stage and every later stage to
  `<run>/archive/restart-<n>/`, outside the agent workspace and never deleted.
  It then checks out that stage's library inputs again, except that restarting
  `translate` restores `glossary.md` and `voice.md` from the last completed
  chapter's snapshot (the rule above) before the chapter records are cleared.
- State produced by those stages is reset to its initial values. Restarting
  `translate` clears every chapter record, outputs, continuity snapshots, gates,
  approvals, domain state, and the agent thread; restarting `prepare` also clears the
  preparation, chapter list, and metadata approval. Restarting `metadata`
  presents the metadata gate again.
- Receipts and events are retained. `state.restarts[]` records
  `{id, stage, reason, created_at, archive, superseded_receipt_ids}`. Old
  receipts cannot satisfy new gates because they are bound to old gate and sheet
  identities.
- A restart neither publishes nor withdraws library publications.

**Restart workflow** (unfinished runs only)
- Creates a new run with the same template, work, and source snapshot, starting
  from the first stage, and cancels the old run, keeping its artifacts and
  history. The index records `restart_of`. Not available for finalized runs.
- Inputs come from the work's library. Published preparation is reused: a ready
  published prepared revision for the same source hash satisfies the prepare
  stage through checkout (still validated with source checks), so the new run starts
  at the metadata gate. `fresh_preparation=True` runs preparation again.
- Glossary and voice come from the abandoned run's last completed chapter
  snapshot, or start empty if no chapter completed. The new run records which
  run and chapter they came from. Nothing else from the abandoned run is
  carried over.

**Engine updates**
- At creation each run records `state.engine = {version, sha256}`: a hash over
  the engine code (`workflow/src/**/*.py`) and its template directory. Skill
  bundles are already copied and pinned per run, so skill updates do not
  affect existing runs.
- Before every operation the service compares the recorded hash with the
  running engine. If they differ and the run is not `COMPLETED` or
  `CANCELLED`, every operation except `restart_workflow` (and reading) is
  refused with `engine_updated`. The user must restart the workflow, so the
  new run is created with the new code. It reuses published preparation and
  carries glossary and voice forward from the old run's last completed chapter,
  as above.
- Exception: a finalized run whose export step has not finished may complete
  its export under the new code, because export only writes the accepted
  snapshots and the workflow can no longer be restarted.
- Completed and cancelled runs stay readable under any engine version.
  Formatting runs follow the same rule: an unfinished formatting run must be
  restarted after an engine update.
- `available_actions` reports the reason, and the GUI shows a notice listing the
  runs that need a restart after an update.

## 11. Roadmap impact (applied to roadmap.md on 2026-10-26)

- M1 scope: remove pause/resume (already in M3); add the `metadata_review` stage
  kind, derived templates with the `accepted_output` contract, the
  `--server-root` CLI, the per-work artifact library with checkout/publish and
  the publication log, per-chapter stage instances, and the retry /
  restart-chapter / restart-stage / restart-workflow operations.
- M1 acceptance criterion 1 becomes: "Literary translation runs through the
  registry with unchanged gate behavior, apart from the new required metadata
  review; the existing suite passes after updates for that step and for the
  CLI/naming changes."
- New acceptance criteria:
  - Formatting runs as a derived template on any accepted-output publication of
    `accepted-markdown-chapters/1`.
  - A second run on an existing work (another workflow, or a workflow restart)
    checks out the published prepared revision and metadata; a conflicting
    metadata publish is refused.
  - Restarting a stage archives its workspace and resets its state without
    losing receipts or events; restarting the workflow creates a linked new run.
  - After an exception in a chapter, restarting that chapter archives its work,
    restores glossary and voice from the last completed chapter, and translates
    only that chapter again; a completed chapter can also be restarted between
    chapters. Other chapters and their receipts are unaffected.
  - After final acceptance, chapter, stage, and workflow restarts are refused
    with `run_finalized`; the workflow becomes read-only on the work and new
    runs of it there are refused with `workflow_read_only`, while other
    workflows on the work continue and formatting can still read its accepted
    output. `available_actions` marks acceptance `irreversible`.
  - Uploading a manuscript always creates a new work with a new ID, even when
    identical to an existing work's source.
  - After an engine update, an unfinished run refuses every operation except
    reading and `restart_workflow` (`engine_updated`); the restarted run uses
    the new code, reuses published preparation, and carries glossary and voice
    forward.
  - Metadata edits after confirmation are recorded in history without
    re-confirmation; formatting uses the formatted output's manuscript language.
  - Creating any run on a work that already has an unfinished run (any
    workflow, including formatting) is refused with `work_busy`.
- M3: replace the **Restart** control ("retry the current step from its last
  verified checkpoint") with **Retry**, **Restart chapter**, **Restart stage**,
  and **Restart workflow** as defined in section 10. No checkpoint rollback.
- M3 scope and acceptance: before final acceptance the GUI shows a prominent
  notice that accepting finalizes the run and makes the workflow read-only on
  the work (no restarts or new runs of it there; changes require adding the
  manuscript again as a new work) and requires explicit confirmation; finalized
  runs and the workflow's section of the work view show a persistent banner,
  with its restart controls disabled.

## 12. Implementation order

Each step keeps the test suite green.

1. `manuscript_language` rename with compatibility shim.
2. Split the base `Engine`, `PreparedManuscriptEngine`, and `TranslationEngine`;
   add `template.json` files, the registry, and dispatch by template ID.
3. Move gate rules into JSON; build the result schema from them.
4. Add the service, server root, run/work index, and thin CLI; update
   `run_e2e.py` and the README.
5. Add the work library: checkout, publish with compare-and-swap, publication
   log, metadata sync, and direct-edit detection.
6. Make formatting a derived template reading an accepted-output publication.
7. Replace `chapter_index` with per-chapter records and per-chapter continuity
   snapshots; add retry (rename of recover), restart chapter, restart stage,
   restart workflow, and the engine-update check.
8. Complete the metadata stage kind and the edit/history/version APIs.
9. Add a test-only template (one agent stage, then acceptance and export, with a
   fake runtime).
10. Update `architecture.md`, `workflow/README.md`, and `roadmap.md`.

## 13. Open questions

None at this time. Decisions from the 2026-10-26 review are incorporated
above: metadata edits after confirmation are history-only; formatting uses the
formatted output's manuscript language; an engine update requires restarting
unfinished runs; published preparation is reused; and a work has at most one
unfinished run at a time.

## 14. Future considerations

- **Git versioning of the work library.** Optional local repository per
  `works/<work_id>/`, committed only by the engine at publish time. Required
  rules: repository-local `core.autocrlf=false` and `* -text` so bytes and
  SHA-256 bindings are preserved; per-command author identity, never global
  config; binaries (DOCX, PDF, PNG, uploads) excluded and kept in `objects/` and
  `sources/`; local only, no remotes; engine SHA-256 bindings remain
  authoritative, with commit IDs recorded alongside.
- **Checkpoint rollback.** Restoring a run's workspace to an earlier verified
  checkpoint; would build on per-boundary snapshots or Git commits.
