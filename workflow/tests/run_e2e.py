"""Launch the live workflow E2E case; all editorial decisions remain interactive."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from zipfile import BadZipFile, ZipFile

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CASE = Path(__file__).parent / "cases/translation-ciqing-001/case.json"
if __package__ in (None, ""):
    sys.path.insert(0, str(REPO))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def load_case(path):
    """Resolve case-relative inputs without creating a run or calling a model."""
    path = Path(path).resolve()
    raw = path.read_bytes()
    spec = json.loads(raw)
    require(isinstance(spec, dict) and spec.get("schema_version") == 1 and spec.get("task") == "literary-translation-workflow",
            "Expected a version-1 workflow E2E manifest, not a translation-quality case.")
    require(isinstance(spec.get("case_id"), str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", spec["case_id"]),
            "Invalid case ID.")
    require(type(spec.get("revision")) is int and spec["revision"] > 0, "Invalid case revision.")
    inputs = spec["input"]
    require(inputs["scope"] == "whole_work" and inputs["target_language"] == "en-US",
            "This launcher supports whole-work translation into US English.")
    require(inputs["runtime"]["adapter"] == "codex-app-server"
            and inputs["runtime"]["human_responses"] == "interactive",
            "This launcher requires Codex App Server and interactive human responses.")
    source = (path.parent / inputs["manuscript"]["file"]).resolve()
    require(sha(source.read_bytes()) == inputs["manuscript"]["sha256"], "Case manuscript hash mismatch.")
    if inputs["manuscript"]["format"] == "docx":
        with ZipFile(source) as archive:
            require("word/document.xml" in archive.namelist(), "DOCX has no main document part.")
            require(archive.testzip() is None, "DOCX archive integrity check failed.")
    definition_path = (path.parent / inputs["workflow_definition"]).resolve()
    definition_raw = definition_path.read_bytes()
    definition = json.loads(definition_raw)
    require(definition["stages"] == spec["expected_output"]["stage_sequence"],
            "Case stage sequence differs from the workflow definition.")
    require(definition["target_language"] == inputs["target_language"], "Target-language mismatch.")
    task_path = (path.parent / inputs["task_specification"]).resolve()
    task_raw = task_path.read_bytes()
    require(task_raw.strip(), "Case task specification is empty.")
    ids = [check["id"] for check in spec["checks"]]
    require(len(set(ids)) == len(ids), "Case check IDs must be unique.")
    return {
        "case_path": str(path), "case_sha256": sha(raw), "spec": spec,
        "source_path": str(source), "definition_path": str(definition_path),
        "definition_sha256": sha(definition_raw), "task_sha256": sha(task_raw),
        "task": task_raw.decode("utf-8"),
    }


def preflight(case, codex):
    from workflow.src.engine import SKILLS, definition_at, module_at
    config = definition_at(Path(case["definition_path"]))
    module_at(SKILLS / "prepare-manuscript/scripts/validate_preparation.py").validators()
    for name in config["agents"]["translate"]["skills"]:
        require((SKILLS / name / "SKILL.md").is_file(), f"Missing skill: {name}")
    executable = shutil.which(codex)
    require(executable is not None, "Codex not found. Install/authenticate Codex, or pass --codex PATH.")
    executable = str(Path(executable).resolve())
    version = subprocess.run([executable, "--version"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=30)
    require(version.returncode == 0, "Could not read Codex version.")
    server = subprocess.run([executable, "app-server", "--help"], capture_output=True, timeout=30)
    require(server.returncode == 0, "Installed Codex does not expose app-server.")
    login = subprocess.run([executable, "login", "status"], capture_output=True, timeout=30)
    require(login.returncode == 0, "Codex is not authenticated. Run 'codex login' and retry.")
    return {"executable": executable, "version": version.stdout.strip() or version.stderr.strip()}


def bind_case(engine, case, runtime_info, model=None, *, resume=False):
    """Store the task/definition identities before executing any case turn."""
    with engine.store.locked():
        revision, state = engine.store.load()
        require(state["source_hash"] == case["spec"]["input"]["manuscript"]["sha256"],
                "Run belongs to a different manuscript.")
        require(state["source_language"] == case["spec"]["input"]["source_language"],
                "Run source language differs from the case.")
        if resume:
            saved = state.get("e2e")
            require(saved is not None, "This run was not created by the E2E launcher.")
            for field in ("case_sha256", "definition_sha256", "task_sha256"):
                require(saved["case"][field] == case[field], f"Changed {field}; start a new test run.")
            require(model is None or model == saved["model_override"],
                    "Cannot change a pinned model on resume; start a new run.")
        else:
            require("e2e" not in state, "Run already bound to an E2E case.")
            state["e2e"] = {"case": case, "model_override": model, "runtime": runtime_info}
            engine.store.save(revision, state, "e2e.created", {"case_id": case["spec"]["case_id"]})
        engine.store.event("e2e.launch", {"runtime": runtime_info, "resume": resume})


class CaseRuntime:
    def __init__(self, runtime, task):
        self.runtime, self.task = runtime, task

    def run(self, request, on_event, on_thread):
        prompt = (
            request.prompt + "\n\nE2E CASE TASK (apply only to the current stage/chapter; "
            "preserve the skill gates and the structured return contract above; use the input "
            "snapshot/workspace paths in the execution context, while original fixture paths "
            "below are provenance rather than additional file-access requests):\n" + self.task
        )
        return self.runtime.run(replace(request, prompt=prompt), on_event, on_thread)


def observation(engine, check_id, status, evidence, *, method):
    engine.store.event("e2e.observation", {
        "check_id": check_id, "status": status, "evidence": evidence, "method": method,
    })


def restart_probe(engine):
    """A fresh interpreter reopens persisted state at a human gate; no model call."""
    code = (
        "import json,sys; from pathlib import Path; "
        "from workflow.src.engine import Engine; "
        "from workflow.tests.run_e2e import fingerprint; "
        "e=Engine(Path(sys.argv[1])); "
        "print(json.dumps({'fingerprint':fingerprint(e.store.load())})); e.close()"
    )
    with engine.store.locked():
        before = engine.store.load()
        require(before[1]["status"] == "WAITING_FOR_HUMAN", "Restart probe requires a pending gate.")
        child = subprocess.run([sys.executable, "-c", code, str(engine.root)], cwd=REPO,
                               capture_output=True, text=True, encoding="utf-8", timeout=30)
        require(child.returncode == 0, "Fresh-process restart probe failed: " + child.stderr)
        require(json.loads(child.stdout)["fingerprint"] == fingerprint(before)
                and engine.store.load() == before, "Restart probe changed or lost saved state.")
        observation(engine, "recovery", "passed",
                    "A fresh Python process reopened the identical pending gate, state revision, and receipts. "
                    "This does not test recovery of an active native Codex turn.", method="automated-probe")


def replay_probe(engine, gate_id, text):
    before = engine.store.load()
    try:
        engine.reply(gate_id, text)
    except ValueError as exc:
        require(str(exc) == "Stale or already answered gate.", "Replay failed for an unexpected reason.")
    else:
        raise ValueError("Consumed review gate was accepted a second time.")
    require(engine.store.load() == before, "Replay rejection mutated workflow state.")
    observation(engine, "stale-response", "passed",
                "Replayed the consumed gate ID; response was rejected and persisted state was unchanged.",
                method="automated-probe")


def latest_observations(engine):
    return {event["payload"]["check_id"]: event["payload"]
            for event in engine.store.events() if event["kind"] == "e2e.observation"}


def atomic_json(path, value):
    from workflow.src.storage import plain
    path = plain(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_report(engine, case):
    """Report exact evidence; domain/quality judgments never become inferred passes."""
    from workflow.src.storage import local_file
    with engine.store.locked():
        state = engine.state()
        automated = {}

        def check(name, operation, *, ready=True):
            if not ready:
                automated[name] = {"status": "not-checked", "evidence": "Required stage has not completed."}
                return
            try:
                evidence = operation()
                automated[name] = {"status": "passed", "evidence": evidence}
            except (OSError, ValueError, KeyError) as exc:
                automated[name] = {"status": "failed", "evidence": str(exc)}

        def integrity():
            require(sha(Path(case["source_path"]).read_bytes()) == case["spec"]["input"]["manuscript"]["sha256"],
                    "Original case manuscript changed.")
            engine.verify(state)
            return "Original hash, input snapshot, pinned skills, and available prepared/output artifacts verified."

        check("source-integrity", integrity)

        def preparation():
            result = engine.preparation.validate(engine.file(state["prepared"]["work_record"]), check_sources=True)
            require(result["preparation_status"] == "ready", "Preparation is not ready.")
            return "Existing preparation validator passed with local source checks."

        check("preparation-validation", preparation, ready=bool(state["prepared"]))
        events = engine.store.events()

        def stage_order():
            stages = []
            for event in events:
                stage = (event["payload"].get("stage") if event["kind"] == "execution.started" else
                         {"artifacts.accepted": "accept", "run.completed": "export"}.get(event["kind"]))
                if stage and (not stages or stages[-1] != stage):
                    stages.append(stage)
            require(stages == case["spec"]["expected_output"]["stage_sequence"],
                    f"Unexpected executed stage sequence: {stages}")
            return stages

        check("stage-order", stage_order, ready=state["status"] == "COMPLETED")

        def receipts():
            for index, output in enumerate(state["outputs"]):
                closures = [(number, receipt["gate"]) for number, receipt in enumerate(state["receipts"])
                            if receipt["gate"]["chapter_index"] == index
                            and receipt["parsed"]["type"] == "final-closure"]
                maps = [number for number, gate in closures if gate["kind"] == "passage_map"]
                sanity = [number for number, gate in closures if gate["kind"] == "chapter_sanity"
                          and gate["binding"]["sha256"] == output["sanity_review_sha256"]]
                require(maps and sanity and min(maps) < max(sanity),
                        f"Missing ordered map/sanity closure receipts for {output['chapter_id']}.")
            return "Completed chapters have map and bound sanity closure receipts; drafting behavior needs domain review."

        check("closure-receipts", receipts, ready=bool(state["outputs"]))

        def export():
            spec = case["spec"]["expected_output"]
            for relative in spec["required_files"]:
                local_file(engine.root, relative)
            manifest = json.loads(local_file(engine.root, "export/manifest.json").read_text(encoding="utf-8"))
            require(manifest["run_id"] == state["id"] and manifest["source"] == state["source"]
                    and manifest["chapters"] == state["outputs"]
                    and manifest["continuity"] == state["continuity"]
                    and manifest["acceptance"] == state["acceptance"], "Export manifest differs from accepted run state.")
            require(state["outputs"] and len(state["outputs"]) == len(state["chapters"]),
                    "Not every requested prepared unit has an output.")
            require(state["acceptance"]["hashes"] == [a["sha256"] for a in state["outputs"]],
                    "Acceptance does not bind the exported versions.")
            expected_files = {f"{i:04d}.md" for i in range(1, len(state["outputs"]) + 1)}
            require({p.name for p in (engine.root / "export").glob("[0-9][0-9][0-9][0-9].md")} == expected_files,
                    "Missing or extra exported chapter files.")
            for index, (output, source) in enumerate(zip(state["outputs"], state["chapters"]), 1):
                require(output["chapter_id"] == source["chapter_id"] and output["source_sha256"] == source["sha256"],
                        "Export source order or identity differs from preparation.")
                require(local_file(engine.root, f"export/{index:04d}.md").read_bytes() == engine.store.content(output),
                        "Exported chapter differs from its accepted snapshot.")
            for name in ("glossary", "voice"):
                require(local_file(engine.root, f"export/{name}.md").read_bytes()
                        == engine.store.content(state["continuity"][name]), f"Exported {name} differs from its snapshot.")
            return "Complete source-ordered export, acceptance hashes, continuity files, and manifest agree."

        check("export-provenance", export, ready=state["status"] == "COMPLETED")
        observations = latest_observations(engine)
        checks = []
        for item in case["spec"]["checks"]:
            evidence = automated.get(item["id"], observations.get(item["id"], {
                "status": "not-checked", "evidence": "Requires an observed scenario or human domain review.",
            }))
            checks.append({**item, **evidence})
        failure = any(item["status"] == "failed" for item in [*checks, *automated.values()])
        status = ("failed" if failure or state["status"] == "FAILED" else
                  "incomplete" if state["status"] != "COMPLETED" else
                  "passed" if all(item["status"] == "passed" for item in checks) else "needs-review")
        report = {
            "case_id": case["spec"]["case_id"], "case_revision": case["spec"]["revision"],
            "case_sha256": case["case_sha256"], "run_id": state["id"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "workflow_status": state["status"], "e2e_status": status,
            "runtime": state.get("e2e", {}).get("runtime"),
            "agents": state["definition"]["agents"], "checks": checks, "automated_checks": automated,
            "literary_quality": {"status": "not-checked", "evidence": "Separate bilingual assessment; no model quality score generated."},
            "error": state.get("error"),
        }
        atomic_json(engine.root / "e2e-report.json", report)
        return report


def collect_candidate(engine, report):
    if any(check["status"] != "passed" for check in report["automated_checks"].values()):
        return
    with engine.store.locked():
        state = engine.state()
        require(state["status"] == "COMPLETED", "Candidate requires a completed run.")
        data = b"\n".join(engine.store.content(artifact) for artifact in state["outputs"])
        from workflow.src.storage import plain
        target = plain(engine.root / "candidate.en.txt")
        if target.exists():
            require(target.read_bytes() == data, "Existing candidate differs; refusing to overwrite it.")
        else:
            with target.open("xb") as handle:
                handle.write(data)


def read_response(input_fn=input):
    print("Enter your response; finish with a line containing only '.'.")
    print("Or use /file PATH, /pause, /cancel, or /refresh as the first line.")
    lines = []
    while True:
        line = input_fn("> " if not lines else "")
        if not lines and line in ("/pause", "/cancel", "/refresh"):
            return line, None
        if not lines and line.startswith("/file "):
            return "reply", Path(line[6:].strip().strip('"')).read_text(encoding="utf-8-sig")
        if line == ".":
            require(lines and "\n".join(lines).strip(), "An explicit response is required.")
            return "reply", "\n".join(lines)
        lines.append(line)


def review_checks(engine, case, input_fn):
    observations = latest_observations(engine)
    for check in case["spec"]["checks"]:
        if check["id"] in ("source-integrity", "export-provenance", "recovery", "stale-response"):
            continue
        if check["id"] in observations:
            continue
        print(f"\nE2E evidence check: {check['id']}\n{check['expectation']}")
        answer = input_fn("pass / fail / skip (or pause): ").strip().lower()
        while answer not in ("pass", "fail", "skip", "pause"):
            answer = input_fn("Enter pass, fail, skip, or pause: ").strip().lower()
        if answer == "pause":
            return
        if answer == "skip":
            continue  # Still available for review on resume.
        evidence = input_fn("Evidence / saved record locations: ").strip()
        while not evidence:
            evidence = input_fn("Describe the evidence, or enter 'skip': ").strip()
        if evidence != "skip":
            observation(engine, check["id"], "passed" if answer == "pass" else "failed",
                        evidence, method="human-review")


def drive(engine, case, runtime, *, max_turns=100, input_fn=input):
    from workflow.src.cli import display
    turns = 0
    try:
        while True:
            state = engine.state()
            report = write_report(engine, case)
            if report["automated_checks"]["source-integrity"]["status"] == "failed":
                raise ValueError(report["automated_checks"]["source-integrity"]["evidence"])
            print(f"\n[{state['stage']}] {state['status']} — completed units {len(state['outputs'])}/{len(state['chapters'])}")
            if state["status"] == "COMPLETED":
                collect_candidate(engine, report)
                review_checks(engine, case, input_fn)
                report = write_report(engine, case)
                print(f"E2E result: {report['e2e_status']}\nExport: {engine.root / 'export'}")
                return 0 if report["e2e_status"] == "passed" else 1 if report["e2e_status"] == "failed" else 2
            if state["status"] == "CANCELLED":
                return 2
            if state["status"] == "READY":
                if turns >= max_turns and state["stage"] != "export":
                    print("Turn limit reached; resume this run to continue.")
                    return 2
                try:
                    engine.advance(runtime)
                    turns += 1
                except (ValueError, OSError, RuntimeError, TimeoutError) as exc:
                    print(f"Execution stopped: {exc}")
                    if engine.state()["status"] == "READY":
                        raise  # Pre-execution integrity/export failure; no automatic retry.
                continue
            if state["status"] == "WAITING_FOR_HUMAN":
                if "recovery" not in latest_observations(engine):
                    try:
                        restart_probe(engine)
                    except (ValueError, OSError, subprocess.SubprocessError) as exc:
                        observation(engine, "recovery", "failed", str(exc), method="automated-probe")
                        raise
                display(engine, state, review=True)
                try:
                    action, response = read_response(input_fn)
                    if action == "/pause":
                        return 2
                    if action == "/cancel":
                        engine.cancel()
                    elif action == "/refresh":
                        engine.recover(refresh_gate=True)
                    else:
                        engine.reply(state["gate"]["id"], response)
                        try:
                            replay_probe(engine, state["gate"]["id"], response)
                        except (ValueError, OSError) as exc:
                            observation(engine, "stale-response", "failed", str(exc), method="automated-probe")
                            raise
                except (ValueError, OSError) as exc:
                    print(f"Response not accepted: {exc}")
                    if engine.state()["status"] != "WAITING_FOR_HUMAN":
                        raise
                continue
            if state["status"] == "WAITING_FOR_ACCEPTANCE":
                display(engine, state, review=True)
                action = input_fn("Type 'accept' for these exact artifacts, 'cancel', or 'pause': ").strip()
                if action == "accept":
                    engine.accept(state["acceptance_id"])
                elif action == "cancel":
                    engine.cancel()
                elif action == "pause":
                    return 2
                continue
            if state["status"] in ("FAILED", "BLOCKED", "PAUSED", "RUNNING"):
                print(state.get("error") or "An earlier execution needs reconciliation.")
                print("Resolve the cause before recovery. For RUNNING, stop any surviving Codex processes first.")
                action = input_fn("recover / recover-stopped / cancel / pause: ").strip()
                if action == "pause":
                    return 2
                try:
                    if action == "cancel":
                        engine.cancel()
                    elif action in ("recover", "recover-stopped"):
                        engine.recover(confirm_stopped=action == "recover-stopped")
                except (ValueError, OSError) as exc:
                    print(f"Recovery refused: {exc}")
                continue
            raise ValueError(f"Unsupported workflow state: {state['status']}")
    except EOFError:
        print("\nInput ended; state retained for resume.")
        return 2
    finally:
        write_report(engine, case)
        print(f"Report: {engine.root / 'e2e-report.json'}")


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--case", type=Path, default=DEFAULT_CASE)
    destination = result.add_mutually_exclusive_group()
    destination.add_argument("--run-dir", type=Path, help="New run directory; default is a unique .workflow-runs/e2e path.")
    destination.add_argument("--resume", type=Path, help="Resume a run created by this launcher.")
    result.add_argument("--codex", default="codex", help="Codex executable, not a shell command.")
    result.add_argument("--model", help="Override both agents' models on creation.")
    result.add_argument("--timeout", type=float, default=900, help="Active-turn timeout; human waits do not count.")
    result.add_argument("--max-turns", type=int, default=100, help="Maximum new turns per invocation.")
    result.add_argument("--setup", action="store_true", help="Create .venv-workflow, install requirements, and relaunch.")
    checks = result.add_mutually_exclusive_group()
    checks.add_argument("--check-case", action="store_true", help="Validate fixture/manifest only; no Codex or run creation.")
    checks.add_argument("--preflight", action="store_true", help="Also check Python dependencies, Codex CLI and login; no model call.")
    return result


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parser().parse_args(argv)
    engine = None
    try:
        require(math.isfinite(args.timeout) and args.timeout > 0 and args.max_turns > 0,
                "Timeout and max-turns must be positive finite values.")
        if args.setup:
            venv = REPO / ".venv-workflow"
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            if not python.is_file():
                subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
            subprocess.run([str(python), "-m", "pip", "install", "-r", str(REPO / "workflow/requirements.txt")], check=True)
            return subprocess.call([str(python), str(Path(__file__).resolve()),
                                    *[arg for arg in argv if arg != "--setup"]])
        case = load_case(args.case)
        print(f"Case: {case['spec']['case_id']}\nInput: {case['source_path']}")
        if args.check_case:
            print("Case definition and source hash verified; no run created.")
            return 0
        from workflow.src.engine import Engine
        from workflow.src.runtime import CodexRuntime
        if args.resume:
            engine = Engine(args.resume)
        needs_runtime = not engine or engine.state()["status"] not in ("COMPLETED", "CANCELLED")
        runtime_info = preflight(case, args.codex) if needs_runtime or args.preflight else engine.state()["e2e"]["runtime"]
        if args.preflight:
            print(f"Preflight passed: {runtime_info['version']}. DOCX extraction capability is verified by the preparation stage.")
            return 0
        if engine is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            run_dir = args.run_dir or REPO / ".workflow-runs/e2e" / f"{case['spec']['case_id']}-{timestamp}-{uuid.uuid4().hex[:6]}"
            run_dir = run_dir.resolve()
            require(not run_dir.exists(), "Run directory already exists; use --resume to continue it.")
            run_dir.parent.mkdir(parents=True, exist_ok=True)
            model = args.model or case["spec"]["input"]["runtime"].get("model")
            engine = Engine.create(run_dir, Path(case["source_path"]), case["spec"]["input"]["source_language"],
                                   definition=Path(case["definition_path"]), model=model)
            bind_case(engine, case, runtime_info, model)
        else:
            bind_case(engine, case, runtime_info, args.model, resume=True)
        print(f"Run: {engine.root}\nResume: python workflow/tests/run_e2e.py --case \"{case['case_path']}\" --resume \"{engine.root}\"")
        runtime = CaseRuntime(CodexRuntime([runtime_info["executable"], "app-server"], args.timeout),
                              engine.state()["e2e"]["case"]["task"])
        return drive(engine, case, runtime, max_turns=args.max_turns)
    except ModuleNotFoundError as exc:
        print(f"Missing Python dependency: {exc.name}. Rerun with --setup.", file=sys.stderr)
        return 1
    except (ValueError, OSError, RuntimeError, KeyError, TypeError, BadZipFile, subprocess.SubprocessError) as exc:
        print(f"E2E launcher: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted. Resume the printed run directory; no human approval was inferred.")
        return 130
    finally:
        if engine:
            engine.close()


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
