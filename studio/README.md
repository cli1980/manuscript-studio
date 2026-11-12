# Manuscript Studio web application (M3, in progress)

```text
.venv-workflow/Scripts/python.exe -m pip install -r studio/requirements.txt
cd studio/frontend && npm ci && npm run build && cd ../..
.venv-workflow/Scripts/python.exe -m studio.server --server-root .workflow-runs --port 8765 --codex PATH-TO-CODEX
```

Open `http://127.0.0.1:8765`. The server binds to loopback only, refuses other
Host headers and cross-origin writes, and accepts an extra loopback origin only
when given with `--allow-origin` (for a local preview proxy).

- **Works** is the place for intake and outcomes: add a manuscript (each upload
  creates a new work), browse every work's library, metadata, and publication
  log without opening a run, and start derived formatting.
- **Workflows** starts a workflow on an existing work (preparation is its first
  stage) and lists runs with what each needs. A background worker runs agent
  turns until a human is needed; Pause stops after the current turn. The run page
  shows controls from `available_actions` and native gate forms: approval-sheet
  items and the separate closure, exact command replies, metadata edits and
  revision-bound confirmation, and final acceptance behind an explicit
  finalization notice. Every reply is validated by the same parser as the CLI.
- **Chapters** (inside a run) shows each prepared chapter once preparation is
  complete, beside every stage's completed output for that chapter. Translation
  decisions and final acceptance take place here. After the last chapter is
  saved, whole-book consistency starts automatically. Its approval sheet stays
  available while browsing chapters, with a source/translation link on each
  finding. Decide every fix, then confirm separate closure; a clean review asks
  for explicit confirmation that no inconsistencies were found. Approved fixes
  are verified before final acceptance, and each chapter lists its applied
  consistency fixes. Whole-book progress is separate from the chapter count.

Pages stay current without polling. One server thread fingerprints every run (state revision, last visible
event, worker status) and every work (publication log) once a second, and `GET /api/live/stream` pushes the
fingerprints as server-sent events whenever they change, with a ping every 15 seconds. Each page refetches only
the data whose fingerprint moved; the timeline fetches only new events. If the stream stays silent, for example
behind a buffering proxy, the page falls back to polling the small `GET /api/live` snapshot.

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
