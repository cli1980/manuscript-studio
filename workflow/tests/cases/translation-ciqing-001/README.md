# End-to-end workflow case: translation-ciqing-001

This is a live, human-supervised orchestration test using the supplied short story
《刺秦》. It tests a different interface from a translation-quality case.

| | Workflow test | Translation-output quality evaluation |
|---|---|---|
| Input | Raw DOCX, language/scope, workflow definition, runtime settings, and human decisions | Source text, candidate English text, and assessment rubric |
| Output | Verified preparation, durable run state, review receipts, accepted chapters, glossary/voice, and export manifest | Scores, rationale, and evidence-backed issues |
| Success | Lifecycle, approval, recovery, source-integrity, coverage, and export checks | Assessed fidelity, English naturalness, and literary voice |
| Execution | Workflow CLI plus Codex and human review | Review server or independent judge runner |

## Test manifest

[`case.json`](case.json) has task `literary-translation-workflow`, separate
`input` and `expected_output` contracts, and named workflow checks. File references
are relative to that manifest. Required output paths are relative to the created
run directory. `source_inventory` describes the input, not an already verified
preparation result; the prepared unit count is intentionally not fixed.

[`prompt.md`](prompt.md) describes the task and fidelity requirements. The source is
the [original DOCX](../../fixtures/short-story-ciqing/刺秦.docx),
with its hash pinned in the manifest. The expected output is not a gold English
translation and does not prescribe literary wording.

The [E2E launcher](../../run_e2e.py) reads this manifest, pins its identity and
task prompt to the run, and drives the workflow. It remains human-supervised.
Do not pass this file to `workflow create --definition`; that lower-level option
takes the separately referenced [workflow definition](../../../definitions/translation.json).
The live case is not automatically executed by the deterministic `unittest` suite.

## One-command launch

With Python 3.12+ and an installed, authenticated Codex CLI, run from the repository root:

```powershell
python workflow/tests/run_e2e.py --setup
```

`--setup` creates/reuses `.venv-workflow`, installs the existing workflow Python
requirements, and relaunches in that environment. It does not install Codex or
sign in on your behalf. If Codex is not on PATH, append
`--codex "C:/path/to/codex.exe"`. Use `--model MODEL_ID` to override the agents'
models when creating a new run.

The launcher:

1. Checks the manifest, raw DOCX hash/archive, definition, Python dependencies,
   pinned skill availability, Codex version, App Server command, and login status.
   Actual DOCX extraction/verification remains the preparation stage's responsibility.
2. Creates a uniquely named run under `.workflow-runs/e2e/` and prints its location.
   Use `--run-dir PATH` for a specific new destination; existing directories are refused.
3. Runs each available turn and presents saved review gates. It appends the pinned
   case task to the normal stage contract, using the run's source snapshot.
4. Reopens the pending gate from a fresh Python process and verifies unchanged
   state/receipts. After real responses, it checks that replaying the consumed gate
   is rejected without a second application.
5. Requires explicit final artifact acceptance, verifies export provenance, and
   writes `candidate.en.txt` for optional downstream quality assessment.
6. Collects human evidence for source coverage and domain behavior, then writes
   `e2e-report.json` with `passed`, `failed`, or `not-checked` results.

At a review, type the actual offered item commands or answer and finish with a
line containing only `.`. For example:

```text
PM001 approve
.
```

This approves that item only. Separate closure and chapter approval requests
still need their own responses. Use `/file PATH` to read a UTF-8 response file,
`/refresh` to request a new review revision, `/pause` to retain the current gate,
or `/cancel` to cancel the run. No option auto-approves editorial decisions.

Resume using the printed directory:

```powershell
.\.venv-workflow\Scripts\python.exe workflow/tests/run_e2e.py `
  --resume ".workflow-runs/e2e/PRINTED-RUN-DIRECTORY"
```

The saved case, source, definition, and task identities must still match.
Failures/blockers are not blindly retried: resolve their cause, then choose
`recover` when prompted. For a hard-crashed `RUNNING` operation, stop surviving
Codex processes before choosing `recover-stopped`. Human waits do not consume the
active-turn `--timeout` (default 900 seconds). `--max-turns` defaults to 100 new
turns per invocation; reaching it pauses advancement until resume.

Preflight without model calls:

```powershell
python workflow/tests/run_e2e.py --check-case
.\.venv-workflow\Scripts\python.exe workflow/tests/run_e2e.py --preflight
```

`--check-case` needs only Python's standard library and checks the manifest/fixture.
`--preflight` additionally checks dependencies, Codex, and authentication.
Neither creates a run. The launcher works from another directory when invoked
by its full path; explicit relative command-line paths are relative to that directory.

Exit codes: **0** means the completed workflow and every case check passed;
**1** means an error/check failure; **2** means paused, cancelled, or completed
with checks still unreviewed; **130** means interrupted. The report separately
records workflow status and E2E status. Literary quality is always reported as
not assessed by this launcher; it does not invent a quality score.

## Lower-level CLI alternative

For individual operations, follow the [workflow setup](../../../README.md),
including providing the required DOCX extraction capability:

```powershell
New-Item -ItemType Directory -Force .workflow-runs | Out-Null
.\.venv-workflow\Scripts\python.exe -m workflow create `
  .workflow-runs/ciqing-001 `
  --source "workflow/tests/fixtures/short-story-ciqing/刺秦.docx" `
  --source-language zh `
  --definition workflow/definitions/translation.json

.\.venv-workflow\Scripts\python.exe -m workflow step .workflow-runs/ciqing-001
.\.venv-workflow\Scripts\python.exe -m workflow status .workflow-runs/ciqing-001
.\.venv-workflow\Scripts\python.exe -m workflow review .workflow-runs/ciqing-001
```

Continue with the documented `reply`, `step`, and final `accept`/`step` commands.
Use the actual gate IDs, allowed decisions, and closure commands shown by the run.
Do not supply a canned blanket-approval transcript.

When using this manual alternative, record the case revision, run ID, model,
runtime version, pinned skill/source identities, and evidence for the checks
listed in `case.json`. Keep execution results with the run, not in the static
case manifest. The ordinary CLI does not inject `prompt.md` or collect an E2E
report; those are launcher responsibilities.

## Checkpoints and expected evidence

1. **Intake and preparation:** original DOCX unchanged; source snapshot matches
   the pinned hash; the existing preparation validator succeeds. Compare extracted
   text and structure with the source. Preserve the title and all ten numbered
   sections once, without forcing ten output files or making the title a narrative chapter.
2. **Translation boundaries:** inspect the passage-map proposals, item decisions,
   and separate closure before drafting. Preserve whole-unit context and real
   section boundaries rather than token-limit splitting.
3. **Domain behavior:** inspect evidence for two-path drafting, paired source/English
   review, passage continuation, and chapter sanity approval, including explicit
   approval of an empty diff. Keep glossary and scoped voice state across contexts.
4. **Recovery:** close/reopen the controller at a pending map or chapter gate.
   The same unresolved gate and settled decisions must remain available.
5. **Replay rejection:** after submitting a valid response, submit the old gate ID
   again. It must be rejected without an additional application or stage advance.
6. **Acceptance/export:** final acceptance binds exact English chapter hashes;
   exported chapter bytes match them and the manifest. Export includes glossary,
   voice, and provenance without changing the original.
7. **Fidelity routing:** the stage sequence remains preparation → translation →
   acceptance → export. Additional prose feedback stays in source-grounded
   translation review; no general English-only polishing stage is inserted.

Some checks require human inspection of the saved domain records. The first
implementation does not mechanically validate all Markdown drafting and assembly
records. A `COMPLETED` state alone does not prove literary fidelity or every
workflow assertion.

The test specification and its original input are both owned by `workflow/tests/`.
Missing DOCX tools produce a blocked result, not a successful end-to-end test.
Do not substitute the quality evaluator's extracted text to bypass DOCX intake.

## Optional downstream quality evaluation

The [separate quality case](../../../../evals/cases/literary-translation/zh-en-ciqing-001/README.md)
can assess this run's text after export. This is an explicit handoff: verify the
accepted chapter hashes, assemble the complete English text in source order,
and pass that candidate to the quality evaluator. It does not consume SQLite,
approval receipts, DOCX, glossary, or workflow logs as judge inputs.

The launcher already produces `candidate.en.txt` inside its run directory after
verifying the completed export. For a run made with the lower-level CLI instead,
the following snippet creates that candidate when it does not already exist:

```powershell
@'
from pathlib import Path
import hashlib
import json

run = Path(".workflow-runs/ciqing-001")
export = run / "export"
manifest = json.loads((export / "manifest.json").read_text(encoding="utf-8"))
assert manifest["source"]["sha256"] == "00383c51ec75fa57ff140f46180a7b20541a23094034fef72ec845f7508f62e3"
chapters = manifest["chapters"]
assert chapters
assert manifest["acceptance"]["hashes"] == [chapter["sha256"] for chapter in chapters]
parts = []
for number, chapter in enumerate(chapters, 1):
    data = (export / f"{number:04d}.md").read_bytes()
    assert hashlib.sha256(data).hexdigest() == chapter["sha256"]
    parts.append(data)
with (run / "candidate.en.txt").open("xb") as output:
    output.write(b"\n".join(parts))
'@ | .\.venv-workflow\Scripts\python.exe -
```

Use that candidate with the quality case's `--translation-file` command. Quality
scores are separate results: a high score cannot compensate for bypassed approval
gates, and a correct workflow cannot guarantee a high-quality translation.
