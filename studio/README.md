# Manuscript Studio web application

```text
git submodule update --init --recursive tools/formattor
.venv-workflow/Scripts/python.exe -m pip install -r studio/requirements.txt -e tools/formattor
cd studio/frontend && npm ci && npm run build && cd ../..
.venv-workflow/Scripts/python.exe -m studio.server --server-root .workflow-runs --port 8765 --codex PATH-TO-CODEX
```

Open `http://127.0.0.1:8765`. The server binds to loopback only, refuses other
Host headers and cross-origin writes, and accepts an extra loopback origin only
when given with `--allow-origin` (for a local preview proxy).

New interior proposals use `/5`, with dedicated Chapter Openings and Part
Openings controls. Combined headings share one paragraph style; separated
number/title headings have independent styles. Title-only, number-only,
source-preserving presentation, number labels, opening offsets and text/glyph
ornaments are available. Parts may have dedicated pages or share their first
chapter's page. Source-bound heading inventories remain read-only; request an
agent revision to correct classification. These controls do not edit manuscript
text, invent optional content or certify rendered page fit. Older proposals
need new authoring/review rather than an automatic approval migration.

- **Works** is the place for intake and outcomes: add a manuscript (each upload
  creates a new work), browse every work's library, metadata, and publication
  log without opening a run, and download accepted editable DOCX editions.
  Only the manuscript is required at intake; there is no language-hint or
  pre-workflow metadata form. Preparation detects language and drafts
  source-supported metadata. The work displays a pending language until then.
  Translation's default passage limit and counting unit
  are selected after that language is known.
  Preparation proposes a title/subtitle when explicitly present in the source.
  Users review/correct titles, contributor credits and optional metadata in one
  place: the Work preparation review. Later metadata-only revisions reuse the
  same editor without another extraction or reading; select the ready source
  version on the Work page. User
  corrections are authoritative and need not appear in the source.
  Re-preparation drafts source metadata independently; the host retains reviewed
  values (including deliberate clearing) and shows discrepancies at audit.
  Published metadata supplies the work's display title; the upload filename is
  only a fallback. A title proposal does not overwrite a supplied title or an
  intentional clearing, and a generated filename heading is not a source title.
- **Work preparation** is an explicitly started Work-owned job after upload:
  extract/normalize, review metadata, analyze, validate and publish a ready
  immutable version. Jobs have their own progress/review/recovery pages under
  Works, not the workflow list. Ready versions include verified front matter,
  ordered Markdown/assets, metadata snapshots and source-bound provisional
  analysis. Storage retries do not repeat a completed model reading.
- **Workflows** starts editing or translation from an explicitly selected ready
  Work version and lists runs with what each needs. It does not repeat intake.
  The exact version/analysis identities remain pinned throughout the run.
  Accepted changed text creates a derived version with analysis pending;
  translation preserves the original. Unchanged/layout-only output attaches
  deliverables without creating another text version. A background worker runs agent
  turns or deterministic production steps until a human is needed; Pause stops after the current step. The run page
  shows controls from `available_actions` and native gate forms: approval-sheet
  items and the separate closure, exact command replies, metadata edits and
  revision-bound confirmation, and final acceptance behind an explicit
  finalization notice. Every reply is validated by the same parser as the CLI.
- **Review viewer** (inside a run) has an unnumbered **Overview**, opened by
  clicking the book title, above the chapter navigation. Front matter is not a
  numbered chapter: its original content, provenance and translated/edited text
  remain available in Overview. Metadata is shared; workflow adapters
  define their own additions and reading layout. Translation includes its brief
  and source/translation panes, while editing shows its current-text view.
  Approved brief snapshots remain distinct from evolving working documents.
  Manuscript Analysis includes provisional BISAC Subjects, Thema Subjects,
  Keywords and Place Subjects for new analysis revisions. Expand each group
  for rationale, confidence and source quotes. Taxonomy codes require a cited
  edition/reference or show as unresolved; these suggestions never replace
  confirmed metadata, apply keywords automatically or add an approval gate.
  Older analysis revisions remain unchanged.
  Review links and notices resolve to Overview or the appropriate
  chapter without changing stored gate IDs or source hashes. Display numbering
  starts with the body; processing progress says "manuscript units" because
  source front/back matter still participates in processing and export.
  The viewer shows each chapter beside its completed stage output. Translation
  decisions and final acceptance take place here. After the last manuscript unit is
  saved, whole-book consistency starts automatically. Its approval sheet stays
  available while browsing chapters, with a source/translation link on each
  finding. Decide every fix, then confirm separate closure; a clean review asks
  for explicit confirmation that no inconsistencies were found. Approved fixes
  are verified before final acceptance, and each chapter lists its applied
  consistency fixes. Whole-book progress is separate from manuscript-unit progress.
  The **Approved Sheets** reference list includes this run's closed review
  sheets, newest first, labeled by chapter/whole-book scope, stage, pass and
  revision. Clicking a link downloads a `.md` file directly, without opening
  another window or leaving the current review. Downloads use the exact saved
  approved Markdown when bound to the review; JSON-only sheets receive a plain
  Markdown export with their recorded decisions and closure receipt.
  Current workspace files are never substituted for approved snapshots.
  Superseded approvals are marked historical; unresolved drafts and feedback
  exchanges are not listed as approvals.

Pages stay current without polling. One server thread fingerprints every run (state revision, last visible
event, worker status) and every work (publication log) once a second, and `GET /api/live/stream` pushes the
fingerprints as server-sent events whenever they change, with a ping every 15 seconds. Each page refetches only
the data whose fingerprint moved; the timeline fetches only new events. If the stream stays silent, for example
behind a buffering proxy, the page falls back to polling the small `GET /api/live` snapshot.

## Pi Evaluation POC

Use Node.js 22 or newer and install the pinned evaluation harness from the
repository root (the installation stays in the ignored local run directory):

```text
npm install --prefix .workflow-runs/pi-evaluation --save-exact --no-audit --no-fund @mariozechner/pi-coding-agent@0.73.1
```

Set the environment variable named by each local endpoint's `api_key_env` in the
server process using your local secret-management mechanism. Do not put its
value in the profile or commit it.
The checked-in `workflow/profiles/pi-evaluation.json` contains only harness
and execution policy. Supply endpoint/model choices through the gitignored
local `execution-profile.user.json` using `--user-execution-profile`.
The private evaluation service address, endpoint-qualified model ID, and
credential variable name stay in that local file, not in checked-in code,
fixtures, or documentation. The live translation evaluation described below
used Pi's `openai-completions` adapter. A missing credential fails clearly;
another provider's credential is never substituted.

**Trust boundary:** Pi in this POC is not OS-sandboxed. Its tools and skill
scripts run with the server user's permissions and can access the host and
network. `trusted_local_execution: true` explicitly opts into this limitation.
Use only trusted manuscripts and skill bundles on a trusted local machine.
Runtime extensions, context files, and skills are not auto-discovered; the
workflow prompt supplies the pinned skill paths. Domain validation and gates
remain enforced, but they are not a security sandbox.

### Runtime structure

`workflow/src/execution.py` loads the immutable profile and binds a registered
`Harness` from `workflow/src/harnesses.py` at startup. Each registration owns its
factory, default command, sandbox description, and endpoint/trust requirements.
Unknown harnesses fail during profile loading. Adding a harness does not require
another construction branch or event translator in the profile wrapper.

The profile's `runtime()` returns a lightweight wrapper. For each operation it
resolves the selected model, creates an adapter through the bound factory, and
redacts events, results, and errors. Constructors do not launch subprocesses.

Both adapters compose `workflow/src/stdio.py` for process startup, JSONL pipes,
reader threads, deadlines, EOF/malformed-output handling, and cleanup. Stderr is
drained without persisting raw diagnostics. The adapters retain their own wire
protocols: Codex initialization/thread/turn JSON-RPC and Pi prompt/event RPC.
Graceful interrupt/abort commands remain adapter-specific; the transport handles
process cleanup, including Windows process-tree termination.

Adapters emit the common `runtime.turn_*`, `runtime.tool_*`, and `runtime.usage`
events directly. Codex notifications are no longer interpreted in the profile
wrapper. Workflow validation, gate enforcement, provenance, and recovery remain
in the engine; the shared transport does not know about workflow semantics.

### Run token usage

The run inspector and chapter viewer show a Token usage panel with input,
output, cached-input, and total tokens, plus the number of agent turns reporting
usage. The runs list is unchanged. Counts are aggregated read-only from saved
usage events, including failed/retried turns, and refresh at saved turn
boundaries rather than introducing another polling loop.

Cached input is already included in input; total is input plus output.
These are harness-reported counts, not billing estimates. Missing usage is
shown as "Not reported"; incomplete coverage is labeled partial, not fabricated
as zero. The detail API and CLI `show` expose the same `usage` object.

Codex accounting uses differences of cumulative thread totals. Its `last`
counter describes one model request, not a cumulative agent turn. Versioned
usage events now distinguish corrected accounting; older normalized Codex
events may undercount and are explicitly labeled partial. Those historical
events and accepted outputs are not rewritten. Older raw Codex telemetry can
be aggregated from its cumulative counters with resume/duplicate handling.
Pi usage is accumulated per assistant message, with cached tokens included in
input once. No provider log scraping or additional inference is used.

Start a separate evaluation server and root rather than modifying existing runs:

```text
.venv-workflow/Scripts/python.exe -m studio.server --server-root .workflow-runs/pi-poc --port 8767 --execution-profile workflow/profiles/pi-evaluation.json --user-execution-profile execution-profile.user.json
```

Open `http://127.0.0.1:8767`. Add a manuscript on Works, then start literary
translation and select the model. The workflow form shows the startup profile
and trust warning; the run inspector shows the last selected/effective execution
identity. Each attempt records its profile revision, harness, model, and endpoint.
Accepted translation `run.json` records include the attempt provenance.

The profile file and referenced credential values are read once at startup.
Editing them has no effect until the server restarts. There are no profile or
mid-run model switching controls. Configured model keys, not arbitrary provider
model IDs, are used in the API and CLI:

```text
.venv-workflow/Scripts/python.exe -m workflow --server-root .workflow-runs/pi-poc --execution-profile workflow/profiles/pi-evaluation.json --user-execution-profile execution-profile.user.json models
.venv-workflow/Scripts/python.exe -m workflow --server-root .workflow-runs/pi-poc --execution-profile workflow/profiles/pi-evaluation.json --user-execution-profile execution-profile.user.json create --template literary-translation-v1 --work WORK-ID --model YOUR-MODEL-KEY
.venv-workflow/Scripts/python.exe -m workflow --server-root .workflow-runs/pi-poc --execution-profile workflow/profiles/pi-evaluation.json --user-execution-profile execution-profile.user.json step RUN-ID
```

### Project and user profile JSON

Use a project profile for execution policy and an optional, separately owned
user JSON for endpoint/model choices. Both studio and CLI accept
`--user-execution-profile PATH` alongside `--execution-profile PATH`:

```text
.venv-workflow/Scripts/python.exe -m studio.server --server-root .workflow-runs/pi-poc --port 8767 --execution-profile workflow/profiles/pi-evaluation.json --user-execution-profile execution-profile.user.json
.venv-workflow/Scripts/python.exe -m workflow --server-root .workflow-runs/pi-poc --execution-profile workflow/profiles/pi-evaluation.json --user-execution-profile execution-profile.user.json models
```

The checked-in Pi policy intentionally has no endpoint, model list, or default
model; it cannot be launched alone. The local file supplies all three.
`workflow/profiles/user.example.json` shows the user-file shape; replace its
example URL, model ID, and credential variable name with your own configuration.
The root-level `execution-profile.user.json` is gitignored. Files may also live
outside the repository; `~` paths are supported. There is no automatic discovery,
so unrelated user settings cannot silently affect a deployment. An explicitly
requested missing or invalid file stops startup, rather than falling back.

Merge rules:

- User JSON allows only `endpoints`, `models`, and `default_model`. Harness,
  command, timeout, trust policy, and profile name remain project-owned.
- Endpoints merge by name; models merge by `key`. A user entry replaces the
  complete matching entry, not individual fields. New entries are appended;
  unmatched project entries remain. There is no deletion syntax.
- Endpoint replacements require the full `base_url`, `api`, and `api_key_env`;
  model replacements require their full applicable configuration. Omitted
  model fields do not inherit old endpoint bindings or workflow restrictions.
- The project default remains unless the user specifies `default_model`.
  The effective default and every model's endpoint reference must resolve.
- Duplicate JSON object keys and duplicate model keys within either file are
  errors. The same model key across the two files is an intentional override.
- The merged configuration is validated against the selected harness. Pi
  supports these profile endpoints; Codex model entries must omit `endpoint`
  and use its installed provider configuration.
- Relative command paths still resolve against the project file's directory,
  never the user file's directory. Credentials remain environment references.

For example, a Codex user file can add a native model without endpoint settings:

```json
{
  "default_model": "sol",
  "models": [
    {
      "key": "sol",
      "model": "gpt-6-sol",
      "workflows": ["literary-translation"]
    }
  ]
}
```

A project may omit its model list and default entirely when the user file
supplies them. It still owns `name`, `harness`, and any execution options;
Pi's explicit trusted-local-execution requirement remains project-owned.
The consolidated profile must be complete before startup succeeds.

The server snapshots both files and credential values once. Edits require a
restart, not a hot reload; each CLI invocation loads them afresh. Execution
provenance uses a revision hash of the consolidated configuration, and the
studio model picker sees the merged choices through the existing API. Use both
options consistently for subsequent CLI commands; the creation hint includes
both paths automatically. Never put literal API keys in either JSON file.

Do not step a run from the CLI while a studio worker is executing it.
With a profile, its `command` and `timeout` are authoritative; `--codex` and
nondefault `--timeout` overrides are refused. Commands are argument arrays, not
shell strings. Relative command paths resolve against the profile file's folder.

For another configured model, add a distinct `key`, its exact `model` ID,
`endpoint` name, and permitted `workflows`; the GUI filters choices by workflow.
Unknown keys or disallowed workflows fail without fallback. Adding endpoint
configuration requires a server restart. Custom endpoints in this POC use Pi;
Codex profiles use the installed Codex provider configuration.

After restarting with a different compatible profile, keep the saved run's model
key available in that profile. It may map to a different supported model/endpoint.
The next agent operation records the new identity and discards an incompatible
old session. Completed work and pending gates/receipts remain intact. Pi currently
starts a fresh session each turn using durable workflow context; cross-harness
conversation transfer is not attempted. Resume/retry explicitly using the usual
controls. After a hard crash, stop surviving old processes before confirming a
retry; this POC does not reconcile remote or orphaned turns automatically.
Actual engine-code updates still require workflow restart, independently of
profile-only changes.

The local evaluation model only enables literary translation. Formatting and editing
are not implicitly declared compatible. Pi remains an evaluation candidate, not
the default runtime. A live private-endpoint translation case has passed; human quality
review, cross-harness live recovery, and a second inference endpoint remain
unverified.
The pinned package is deprecated upstream in favor of the renamed Pi packages;
changing versions requires repeating the protocol and extension checks.

Live evidence: existing case `beijing-night-translation-gui-001` completed as run
`da6626a3-bfe6-4417-8960-bd0e7a1c7af7` in the separate Pi evaluation root,
using 10 Pi turns. Exported chapter and continuity hashes match the accepted
artifacts and manifest. All seven gate receipts and final acceptance are
`delegated-automation`, not human review. To retain that attribution on the
already-running server, the local browser driver intercepted decision requests
into the shared local engine and resumed the real server worker. This validates
workflow execution and browser gate interaction, not the complete browser
decision-API transport path. The local report is
`.workflow-runs/pi-translation-browser-report.json`.

After the shared-transport/factory refactor, the same case passed again for both
harnesses: Codex run `7057c015-0982-4462-b17f-f0ef64b8bdd3` and Pi run
`763a27f5-3a59-4561-a58c-d66faa05549c`. Each completed 10 turns and exported
two units with verified chapter/continuity hashes. Both engine identities match
the refactored source, and both emitted normalized lifecycle, tool, and usage
events. Each has seven delegated gate receipts and delegated final acceptance.
Reports are `.workflow-runs/refactor-codex-translation-report.json` and
`.workflow-runs/refactor-pi-translation-report.json`.
Codex used its installed provider and configured `gpt-6-astra` model; Pi used the
private endpoint and model from the local profile. These are functional checks, not a
same-model/provider comparison or human quality review.

Run the deterministic profile/transport checks, including a real pinned Pi
against a local fake inference server when that package is installed:

```text
.venv-workflow/Scripts/python.exe -m unittest workflow.tests.test_execution -v
```

These checks do not call external inference. Raw provider streams and stderr are
not stored by the Pi adapter; normalized lifecycle/tool boundaries and available
token usage are recorded. Inference failures are reported without raw provider
diagnostics, and configured credentials are redacted from structured events,
results, and errors. Trusted tool processes can still access their environment;
this is not credential isolation from agent tools.

## Interior-design review in literary editing

Start a new literary-editing run, or restart an older run whose engine has changed.
Select a ready Work version containing preparation, reviewed metadata and shared
manuscript analysis; then run and accept any editing passes, or
finish with zero passes. Choose **Review manuscript**, inspect the candidate
chapters under **Approve manuscript for formatting**, and choose
**Approve manuscript and continue**. This approval freezes the
manuscript and metadata, then automatically starts the final formatting phase.
There is no early Format/interior-design button or separate content-only finish.

At manuscript approval, choose **Purpose** (default **Print-ready**, or Submission
or Editorial review), **Binding** (paperback/hardcover) and optionally
**Print vendor: IngramSpark**. There is one vendor option; the matching binding
variant loads automatically, with its rule sources and DOCX guidance. The
selected version/data/hash are supplied to the design agent and bound in the
proposal. No vendor is selected by default.
The purpose and its design guidance reach the agent before authoring. Print-ready
describes intended use, not successful print validation.

The interior-design skill produces a proposal, then the chapter viewer presents
an editable human form. Edit geometry, fonts/leading, paragraph settings,
navigation, furniture and special-role style mappings. Geometry is edited in mm
with live inch equivalents. Preferred page count, internal IDs/profile references,
hashes and raw JSON/debug views are not exposed in this form. Literary reading is
read-only. **Save specification changes** creates a validated new revision.
You can request an agent revision or respond to necessary author/design questions and
prepare a draft from the exact saved proposal without approving its design.

Purpose, vendor and binding are shown as a read-only summary; target IDs and
profile references remain internal. Their duplicate selectors are removed, and
direct API saves cannot change them. To choose a different target, reopen manuscript
approval and select it there before authoring a new proposal. Layout, typography,
and other design settings remain editable.

Technical questions about fonts, producer capabilities, vendor readiness or final
PDF checks are not author decisions. If there are no author questions,
no answer fields are required. Draft generation is not design approval or
verification of print compliance.

### Editable-DOCX production POC

After **Generate draft DOCX**, the `produce-docx` step calls the separately installed
`book_formatter` public API. New workflow proposals must request exactly one
`editable-docx` target. PDF/multi-format bundles are refused, not silently reduced.
Print-ready purpose and vendor-guided geometry do not certify the DOCX for print.

1. Choose **Generate draft DOCX** once. Studio records the effective plan and
   builds/checks the candidate without an intermediate gate. The persisted,
   retryable job binds that human request, saved design, prepared inputs and
   formatter/runtime identity. A changed plan stops generation rather than
   silently replanning. Construction uses no agent, Word automation or renderer.
   Counts, styles, plan hash, policies and vendor advisories remain read-only
   technical details. The source-bearing plan stays in private run storage.
2. **Download DOCX candidate** and inspect it in Word. Generated `BF.*` styles
   are Quick Styles for post-generation editing. Downloaded edits are not
   synchronized back; acceptance always identifies the original checked bytes.
3. Choose **Revise design** to reopen saved settings or request an agent
   revision, then generate and inspect a new draft. The old build stays in
   history, but its acceptance identity and generation authorization cannot be
   reused. Manuscript approval and frozen text/metadata remain unchanged.
4. **Approve edition and finish** approves the current design and exact DOCX
   together and records the proposal/candidate/manifest/plan hashes. It
   finalizes the editable-document edition and publishes `document.docx`,
   `docx-build.json` and `design-proposal.json` alongside the accepted Markdown.
   The work's versioned library and run page retain checksum-verified download
   links; the export contains the same files.

This is DOCX construction/content/structure verification, not rendered-page
approval. No PDF, calculated pagination, field refresh, page images, actual font
resolution or print certification is supplied. Translation's finishing phase and
the full print-production/page-review pipeline remain unchanged/pending.

Retry uses a new owned output path without overwriting an interrupted candidate.
Design-only restarts invalidate old generation/candidate bindings and download
IDs while retaining the manuscript approval and archived evidence. Reopen
`approve-manuscript` to revise the basis and invalidate downstream decisions.
Older runs/approvals are not migrated or rewritten; restart an outdated run
explicitly to use the new engine.

The legacy work-page/completed-run formatter actions, separate template and old
format skill are removed. Existing legacy runs show read-only history rather
than an active six-item sheet; they do not block new supported workflows. See the
[tracked design](https://github.com/cli1980/book-formatter/blob/237be7d034b57f7a77fd0b7e9cd0ecb03a27d05c/docs/interior-design-and-production.md).

Run commands from the repository root. `npm run dev` (in `studio/frontend`) serves the frontend on port 5173 and proxies `/api` to the server.

Layout: `server/` holds the FastAPI app and the background worker, `frontend/` the
React/TypeScript (Vite) client, and `tests/` the API tests:

```text
.venv-workflow/Scripts/python.exe -m unittest studio.tests.test_web -v
```

## Case-driven tests

Each case lives in `studio/tests/cases/<case-id>/case.json` and lists API steps
run against a fresh server root through the same HTTP interface the browser
uses; no model runs unless a case provides a runtime. Inputs come from the
repository's shared `fixtures/` folder.

- Actions: `upload_work` (Works-page intake of a fixture), `get`, `post`, and
  `page` (the frontend entry point).
- `save_as` keeps a step's response; later steps reference it as `$name.field`,
  including inside paths.
- `expect` checks fields with `equals`, `not_equals`, `contains`, `length`,
  `unique`, `matches`, `every_startswith`, or `empty`; paths support list
  indexes, `*keys`, and `*len`, and a field on a list collects it from each item.

```text
.venv-workflow/Scripts/python.exe -m unittest studio.tests.test_cases -v
```

The feedback-isolation browser check uses mocked API responses and no model.
Build the frontend and install `studio/requirements-e2e.txt` and Playwright's
Chromium browser, then run:

```text
STUDIO_BROWSER=1 .venv-workflow/Scripts/python.exe -m unittest studio.tests.test_cases.StudioCaseTests.test_feedback_stays_with_its_review -v
```

It checks that comments and general feedback do not carry into the next review
without a page reload, and that failed submissions preserve the current draft.

The embedded interior-design browser check uses the real API/engine with a
scripted skill, not a live model. It covers form edits, desktop/390 px mobile
layout, single-action exact-plan generation, real DOCX candidate download, final editable
acceptance and the accepted work-library download:

```text
STUDIO_BROWSER=1 .venv-workflow/Scripts/python.exe -m unittest studio.tests.test_cases.StudioCaseTests.test_editable_interior_design_gate -v
```

### Live cases

A case with a `runtime` block (for example `beijing-night-translation-gui-001`)
runs real Codex turns and is skipped unless `STUDIO_LIVE=1`; it is also skipped
when a local-only fixture it lists is missing. `start_run` starts a workflow on a
work, and `drive_run` answers gates the way a reviewer would in the GUI
(confirm metadata, the first decision that resolves without a note for each
sheet item, then closure; offered commands or "continue" for questions) until
the run reaches `until`, accepting only when `"accept": true`. Set
`STUDIO_CASE_ROOT` to keep the server root for inspection, and `CODEX` if the
Codex executable is not on `PATH`:

```text
STUDIO_LIVE=1 STUDIO_CASE_ROOT=.workflow-runs/studio-cases .venv-workflow/Scripts/python.exe -m unittest studio.tests.test_cases -k beijing -v
```

With `"client": "browser"` in the runtime block, the case serves the studio on
its own port (`STUDIO_CASE_PORT`, default 8766) and makes every reviewer choice
by clicking the run page in Chromium through Playwright (install
`studio/requirements-e2e.txt`). Open `http://127.0.0.1:8766` to watch, or set
`STUDIO_HEADED=1` (optionally `STUDIO_SLOW_MO=500`) to show the automated
browser itself; `STUDIO_ALLOW_ORIGIN` admits a loopback preview origin.

### Profile-bound translation evaluation

To reuse the same Beijing-night case against an already-running Codex or Pi
profile server, use the explicit live evaluation launcher:

```text
.venv-workflow/Scripts/python.exe -m studio.tests.run_translation_case --origin http://127.0.0.1:8767 --server-root .workflow-runs/pi-poc --harness pi --report .workflow-runs/pi-translation-new-report.json
```

For Codex, supply its profile server's origin/root and `--harness codex`.
The launcher creates a new test work/run, initially without starting inference,
and checks that the server's engine identity matches the local source before
resuming. Restart servers after engine-code changes; never reuse an old loaded
server as evidence for new adapter code. Report paths must be new, so previous
evidence is not overwritten.

The launcher uses Chromium for gate interaction but intercepts decision requests
into the shared local engine with `decision_source=delegated-automation`; the
real server worker performs inference. It checks case expectations, exported
chapter/continuity hashes, attempt harness identity, and decision attribution.
This does not constitute human literary review or full browser decision-API
transport testing. Different models or endpoints are not a controlled
harness-quality comparison.
