"""Launch the workflow E2E case, with interactive or explicitly delegated approvals."""

from __future__ import annotations

import argparse
import copy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from zipfile import BadZipFile, ZipFile

REPO = Path(__file__).resolve().parents[2]
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
    require(isinstance(spec, dict) and spec.get("schema_version") == 1
            and spec.get("task") in ("literary-translation-workflow", "literary-editing-workflow"),
            "Expected a version-1 workflow E2E manifest, not a quality-evaluation case.")
    require(isinstance(spec.get("case_id"), str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", spec["case_id"]),
            "Invalid case ID.")
    require(type(spec.get("revision")) is int and spec["revision"] > 0, "Invalid case revision.")
    inputs = spec["input"]
    require(inputs["scope"] == "whole_work" and inputs.get("target_language") in (None, "en-US"),
            "This launcher supports whole-work cases, translating only into US English.")
    require(inputs["runtime"]["adapter"] == "codex-app-server"
            and inputs["runtime"]["human_responses"] == "interactive",
            "This launcher requires Codex App Server and interactive human responses.")
    source = (path.parent / inputs["manuscript"]["file"]).resolve()
    require(sha(source.read_bytes()) == inputs["manuscript"]["sha256"], "Case manuscript hash mismatch.")
    if inputs["manuscript"]["format"] == "docx":
        with ZipFile(source) as archive:
            require("word/document.xml" in archive.namelist(), "DOCX has no main document part.")
            require(archive.testzip() is None, "DOCX archive integrity check failed.")
    from workflow.src import registry
    template = registry.get(inputs["template_id"])
    skipped = inputs.get("skip_stages", [])
    require([stage["id"] for stage in template["stages"] if stage["id"] not in skipped]
            == spec["expected_output"]["stage_sequence"], "Case stage sequence differs from the workflow template.")
    require(template.get("target_language") == inputs.get("target_language"), "Target-language mismatch.")
    task_path = (path.parent / inputs["task_specification"]).resolve()
    task_raw = task_path.read_bytes()
    require(task_raw.strip(), "Case task specification is empty.")
    ids = [check["id"] for check in spec["checks"]]
    require(len(set(ids)) == len(ids), "Case check IDs must be unique.")
    return {
        "case_path": str(path), "case_sha256": sha(raw), "spec": spec,
        "source_path": str(source), "template_id": template["id"],
        "template_sha256": fingerprint(template), "task_sha256": sha(task_raw),
        "task": task_raw.decode("utf-8"),
    }


def preflight(case, codex):
    from workflow.src import registry
    from workflow.src.engine import SKILLS, module_at
    config = registry.get(case["template_id"])
    module_at(SKILLS / "prepare-manuscript/scripts/validate_preparation.py").validators()
    for name in {skill for agent in config["agents"].values() for skill in agent["skills"]}:
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
    """Store the task/template identities before executing any case turn."""
    with engine.store.locked():
        revision, state = engine.store.load()
        require(state["source_hash"] == case["spec"]["input"]["manuscript"]["sha256"],
                "Run belongs to a different manuscript.")
        require(state["manuscript_language"] == case["spec"]["input"]["manuscript_language"],
                "Run manuscript language differs from the case.")
        require(state["template_id"] == case["template_id"], "Run uses a different workflow template.")
        if resume:
            saved = state.get("e2e")
            require(saved is not None, "This run was not created by the E2E launcher.")
            for field in ("case_sha256", "template_sha256", "task_sha256"):
                require(saved["case"][field] == case[field], f"Changed {field}; start a new test run.")
            require(model is None or model == saved["model_override"],
                    "Cannot change a pinned model on resume; start a new run.")
        else:
            require("e2e" not in state, "Run already bound to an E2E case.")
            state["e2e"] = {"case": case, "model_override": model, "runtime": runtime_info}
            engine.store.save(revision, state, "e2e.created", {"case_id": case["spec"]["case_id"]})
        engine.store.event("e2e.launch", {"runtime": runtime_info, "resume": resume})


RECOMMENDATION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["action", "response", "reason"],
    "properties": {
        "action": {"enum": ["accept", "needs_review"]},
        "response": {"type": "string"},
        "reason": {"type": "string", "minLength": 1},
    },
}


class CaseRuntime:
    def __init__(self, runtime, task, *, auto_approve_recommended=False, operation="translation"):
        self.runtime, self.task = runtime, task
        self.auto_approve_recommended = auto_approve_recommended
        self.operation = operation

    def run(self, request, on_event, on_thread):
        prompt = (
            request.prompt + "\n\nE2E CASE TASK (apply only to the current stage/chapter; "
            "preserve the skill gates and the structured return contract above; use the input "
            "snapshot/workspace paths in the execution context, while original fixture paths "
            "below are provenance rather than additional file-access requests):\n" + self.task
        )
        schema = copy.deepcopy(request.output_schema)
        if self.auto_approve_recommended:
            schema["required"].append("approval_recommendation")
            schema["properties"]["approval_recommendation"] = RECOMMENDATION_SCHEMA
            prompt += (
                "\n\nThe user explicitly enabled --auto-approve-recommended for this run. "
                "They delegate acceptance of your recommended editorial choices to the launcher. "
                "Keep every existing gate and separate final closure; do not self-approve in domain files. "
                "Return approval_recommendation with action='accept' only when accepting the current "
                "proposal/choice is your actual recommendation, and explain why in reason. response must "
                "be the EXACT response to the current gate: explicit item IDs and allowed resolve commands "
                "(with required notes), the separate closure command when available, 'approve chapter' "
                "for an empty sanity diff, 'approve brief' for a translation brief you recommend unchanged, "
                "'continue' for passage continuation, or the explicit recommended "
                "choice for a single translation issue. Never recommend reject/defer/reopen as acceptance. "
                "Use action='needs_review' for missing information, uncertainty requiring user judgment, "
                "or a recommendation to revise/reject. For a completed translation, recommend response='accept' "
                "only when you recommend accepting that exact final artifact. For completed preparation, "
                "recommend response='confirm metadata' only when you recommend confirming the saved shared "
                "metadata unchanged at the following metadata review gate; otherwise use needs_review. For "
                "a blocked result use needs_review with an explanatory reason. This is a user-authorized "
                "automation policy, not evidence that a human reviewed the text. Continue to use source-grounded "
                "fidelity review, not general stylistic polishing."
                " Finish the complete current passage's drafting and review before requesting editorial "
                "dispositions. When there are multiple independent issues, present one revision-bound issue "
                "sheet and include ALL independently recommended accepting dispositions in one response. "
                "Do not request a separate model exchange for each independent sheet item. Batch processing "
                "does not merge item dispositions with final closure, postpone passage-map approval until "
                "after drafting, or treat dependent choices as independent."
            )
            if self.operation == "editing":
                prompt += (
                    "\nFor this literary editing job, translation-only phase instructions (passage maps, "
                    "continuation, sanity diffs) do not apply. Present all proposals of a job in one "
                    "revision-bound decision sheet and recommend explicit item lines only for proposals you "
                    "recommend accepting; a recommendation to reject, defer, or query an item is needs_review, "
                    "so propose only changes you actually recommend and raise genuine author questions as "
                    "queries. Item dispositions, the separate closure command, and the apply authorization "
                    "remain separate responses: recommend exactly 'apply accepted changes' at the "
                    "apply_authorization gate only when you recommend applying exactly the accepted rows, and "
                    "exactly 'approve review' for an empty review. Editing a translation: never recommend a "
                    "change that could alter meaning. approval_recommendation is required in EVERY result, "
                    "including completed jobs: when a completed job leads to another editorial job, return "
                    "action='accept', response='continue', and a short reason (no gate follows, so it is not "
                    "used); when the completed job is the last one before final artifact acceptance, recommend "
                    "response='accept' only if you recommend accepting the complete edited manuscript."
                )
            if self.operation == "formatting":
                prompt += (
                    "\nFor this formatting job, translation-only phase instructions do not apply. "
                    "Recommend all independently acceptable FM items in one response, then request "
                    "separate format-specification closure. Never generate before closure or modify "
                    "the accepted prose. Missing adapter or render capability requires needs_review "
                    "and a blocked result, not a recommendation to accept an unverified file."
                )
        result = self.runtime.run(replace(request, prompt=prompt, output_schema=schema), on_event, on_thread)
        if self.auto_approve_recommended:
            from jsonschema import Draft202012Validator
            error = next(Draft202012Validator(schema).iter_errors(result), None)
            require(error is None, f"Invalid recommendation result: {error.message if error else ''}")
            result = dict(result)
            recommendation = result.pop("approval_recommendation")
            on_event("e2e.recommendation", {"result_sha256": fingerprint(result), **recommendation})
        return result


def recommended_response(engine):
    """Only use a recommendation from the current successfully committed turn."""
    events = engine.store.events()
    completed = next((e for e in reversed(events) if e["kind"] == "execution.result"), None)
    require(completed is not None, "No successful turn recommendation is available.")
    started = max(e["id"] for e in events if e["kind"] == "execution.started" and e["id"] < completed["id"])
    suggestion = next((e["payload"] for e in reversed(events)
                       if started < e["id"] < completed["id"] and e["kind"] == "e2e.recommendation"), None)
    require(suggestion and suggestion["result_sha256"] == fingerprint(completed["payload"]),
            "No recommendation bound to the current result; resume interactively.")
    require(suggestion["action"] == "accept", "Recommendation requires review: " + suggestion["reason"])
    response = suggestion["response"].strip()
    require(response, "Acceptance recommendation has no explicit response.")
    state = engine.state()
    if state["status"] == "WAITING_FOR_ACCEPTANCE":
        require(response == "accept" and completed["payload"]["outcome"] == "completed",
                "Final artifact acceptance was not recommended.")
    elif state["gate"]["kind"] == "metadata_review":
        require(completed["payload"]["outcome"] == "completed" and completed["payload"]["gate"] is None
                and next(e for e in events if e["id"] == started)["payload"]["stage"] == "prepare",
                "Metadata confirmation needs the completed preparation turn's recommendation.")
        require(not any(e["kind"] == "metadata.edited" and e["id"] > completed["id"] for e in events),
                "Metadata changed after the recommendation; resume interactively.")
        require(response == "confirm metadata", "Metadata confirmation was not recommended.")
    else:
        gate = state["gate"]
        rules = state["definition"]["gates"].get(gate["kind"], {})
        require(gate["kind"] == completed["payload"]["gate"], "Recommendation belongs to a different gate.")
        command = rules.get("command") or (None if gate["sheet"] else rules.get("empty_command"))
        if command:
            # Template-declared exact commands, such as an apply authorization or an empty-review approval.
            require(response == command, f"The {gate['kind']} command was not recommended.")
        elif gate["sheet"]:
            sheet = json.loads(engine.store.content(gate["sheet"]))
            parsed = engine.approval.parse_response(sheet, response)
            if parsed["type"] == "dispositions":
                for disposition in parsed["dispositions"]:
                    require(disposition["effect"] == "resolve"
                            and not re.search(r"\b(reject|defer|revise|reopen|decline)\b",
                                              disposition["decision"] + " " + disposition["command"], re.I),
                            "Recommendation contains a non-accepting disposition.")
        elif gate["kind"] == "chapter_sanity":
            require(response == "approve chapter", "Chapter completion approval was not recommended.")
        elif gate["kind"] == "continuation":
            require(response == "continue", "Passage continuation was not recommended.")
        else:
            require(gate["kind"] == "translation_issue",
                    "Questions require a real user response; automation will not invent missing input.")
    return response, suggestion


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
        "e=Engine.open(Path(sys.argv[1])); "
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
                         {"metadata.confirmed": "metadata", "artifacts.accepted": "accept",
                          "run.completed": "export"}.get(event["kind"]))
                if stage and (not stages or stages[-1] != stage):
                    stages.append(stage)
            require(stages == case["spec"]["expected_output"]["stage_sequence"],
                    f"Unexpected executed stage sequence: {stages}")
            return stages

        check("stage-order", stage_order, ready=state["status"] == "COMPLETED")

        def editorial_receipts():
            items = [i for group in state.get("stage_iterations", {}).values() for i in group] + state["iterations"]
            closed = {(r["gate"].get("instance"), r["gate"]["kind"]) for r in state["receipts"]
                      if r["parsed"]["type"] in ("final-closure",)}
            jobs = 0
            for item in items:
                stage = next(s for s in state["definition"]["stages"] if s["id"] == item["stage"])
                if item["status"] != "completed" or (not stage.get("edits_text", True) and item["chapter_id"] != "_whole"):
                    continue
                key = f"{item['stage']}/{state['stage_epochs'].get(item['stage'], 1)}/{item['chapter_id']}/{item['attempt']}"
                require((key, "editorial_review") in closed, f"Missing decision closure for {key}.")
                if item.get("changed"):
                    require((key, "apply_authorization") in closed, f"Text changed without apply authorization: {key}.")
                jobs += 1
            return f"{jobs} editorial jobs have decision closure, and every text change has an apply authorization."

        def receipts():
            if state["workflow"] == "literary-editing":
                return editorial_receipts()
            reviewed = 0
            for output in state["outputs"]:
                chapter_id = output["chapter_id"]
                # Closure is an explicit closure command, or a complete resolving submission where it is implied.
                closures = [(number, receipt["gate"]) for number, receipt in enumerate(state["receipts"])
                            if receipt["gate"].get("chapter_id") == chapter_id
                            and receipt["gate"].get("attempt") == output.get("attempt")
                            and (receipt["parsed"]["type"] == "final-closure" or receipt["parsed"].get("implied_closure"))]
                sanity = [number for number, gate in closures if gate["kind"] == "chapter_sanity"
                          and gate["binding"]["sha256"] == output["sanity_review_sha256"]]
                require(sanity, f"Missing chapter approval bound to the reviewed text for {chapter_id}.")
                # The passage map is internal; only a map with exceptions needs the user's closure, before approval.
                path = engine.workspace / "translation/maps" / f"{chapter_id}.json"
                require(path.is_file(), f"Missing passage map for {chapter_id}.")
                if json.loads(path.read_text(encoding="utf-8")).get("exceptions"):
                    maps = [number for number, gate in closures if gate["kind"] == "map_exceptions"]
                    require(maps and min(maps) < max(sanity),
                            f"Passage-map exceptions for {chapter_id} lack a closure before chapter approval.")
                    reviewed += 1
            return (f"Every completed chapter has a bound chapter approval; {reviewed} chapter(s) with passage-map "
                    "exceptions closed them first. Drafting behavior needs domain review.")

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
            for name in state["continuity"]:
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
            "delegated_decisions": sum(r.get("decision_source") == "delegated-automation" for r in state["receipts"]),
            "artifact_acceptance_source": state.get("acceptance", {}).get("decision_source"),
            "error": state.get("error"),
        }
        report["formatting_jobs"] = {}
        previous = engine.root / "e2e-report.json"
        jobs = json.loads(previous.read_text(encoding="utf-8")).get("formatting_jobs", {}) if previous.exists() else {}
        for job_id, job in jobs.items():
            # Derived formatting runs live under the server root; refresh their recorded status read-only.
            try:
                database = Path(job["path"]) / "state.sqlite3"
                connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
                try:
                    job_state = json.loads(connection.execute("SELECT state FROM run WHERE id=1").fetchone()[0])
                finally:
                    connection.close()
                report["formatting_jobs"][job_id] = {
                    "path": job["path"], "status": job_state["status"],
                    "backend": job_state.get("backend"), "document_path": job_state.get("document_path"),
                    "error": job_state.get("error"),
                }
            except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
                report["formatting_jobs"][job_id] = {"status": "UNAVAILABLE", "error": str(exc)}
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


def drive(engine, case, runtime, *, max_turns=100, input_fn=input, auto_approve_recommended=False):
    from workflow.src.cli import display
    turns = 0
    try:
        while True:
            state = engine.state()
            report = write_report(engine, case)
            if report["automated_checks"]["source-integrity"]["status"] == "failed":
                raise ValueError(report["automated_checks"]["source-integrity"]["evidence"])
            progress = engine.summary(state)["progress"] or {"completed": 0, "total": len(state["chapters"])}
            print(f"\n[{state['stage']}] {state['status']} — completed units {progress['completed']}/{progress['total']}")
            if state["status"] == "COMPLETED":
                collect_candidate(engine, report)
                if not auto_approve_recommended:
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
                    if auto_approve_recommended:
                        try:
                            response, suggestion = recommended_response(engine)
                        except ValueError as exc:
                            print(f"Automation stopped: {exc}")
                            return 2
                        action = "reply"
                        print("Delegated acceptance: " + suggestion["reason"])
                        engine.store.event("e2e.delegated_approval", {"gate_id": state["gate"]["id"], **suggestion})
                    else:
                        action, response = read_response(input_fn)
                    if action == "/pause":
                        return 2
                    if action == "/cancel":
                        engine.cancel()
                    elif action == "/refresh":
                        engine.retry(refresh_gate=True)
                    else:
                        engine.reply(state["gate"]["id"], response,
                                     decision_source="delegated-automation" if auto_approve_recommended else "human")
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
                if auto_approve_recommended:
                    try:
                        action, suggestion = recommended_response(engine)
                    except ValueError as exc:
                        print(f"Automation stopped: {exc}")
                        return 2
                    engine.store.event("e2e.delegated_approval", {"acceptance_id": state["acceptance_id"], **suggestion})
                else:
                    action = input_fn("Type 'accept' to accept these exact artifacts and confirm the finalization "
                                      "notice above, 'cancel', or 'pause': ").strip()
                if action == "accept":
                    # Typing 'accept' after the displayed notice, or the explicit automation opt-in, confirms it.
                    engine.accept(state["acceptance_id"], confirm_final=True,
                                  decision_source="delegated-automation" if auto_approve_recommended else "human")
                elif action == "cancel":
                    engine.cancel()
                elif action == "pause":
                    return 2
                continue
            if state["status"] in ("FAILED", "BLOCKED", "PAUSED", "RUNNING"):
                print(state.get("error") or "An earlier execution needs reconciliation.")
                if auto_approve_recommended:
                    print("Automation stopped; resolve the failure/blocker before recovery.")
                    return 1 if state["status"] == "FAILED" else 2
                print("Resolve the cause before recovery. For RUNNING, stop any surviving Codex processes first.")
                action = input_fn("retry / retry-stopped / cancel / pause: ").strip()
                if action == "pause":
                    return 2
                try:
                    if action == "cancel":
                        engine.cancel()
                    elif action in ("retry", "retry-stopped"):
                        engine.retry(confirm_stopped=action == "retry-stopped")
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
    result.add_argument("--case", type=Path, required=True, help="Explicit case manifest; long local tests are never selected by default.")
    result.add_argument("--server-root", type=Path, default=REPO / ".workflow-runs/e2e",
                        help="Workflow server root for E2E works and runs.")
    result.add_argument("--resume", help="Resume a run ID created by this launcher under the server root.")
    result.add_argument("--codex", default="codex", help="Codex executable, not a shell command.")
    result.add_argument("--model", help="Override both agents' models on creation.")
    result.add_argument("--format-docx", action="store_true",
                        help="After translation export, run the optional final manuscript-formatting agent.")
    backend = result.add_mutually_exclusive_group()
    backend.add_argument("--documents-skill", type=Path, help="Optional external Documents skill instead of built-in adapters.")
    backend.add_argument("--renderer", choices=("word", "libreoffice"),
                         help="DOCX renderer; defaults to Word on Windows, LibreOffice elsewhere.")
    result.add_argument("--format-purpose", choices=("reader-facing", "editorial-review", "submission"),
                        default="reader-facing")
    result.add_argument("--auto-approve-recommended", action="store_true",
                        help="Explicitly delegate acceptance of structured accept recommendations; stop on review/blockers.")
    result.add_argument("--timeout", type=float, default=900, help="Active-turn timeout; human waits do not count.")
    result.add_argument("--max-turns", type=int, default=100, help="Maximum new turns per invocation.")
    result.add_argument("--setup", action="store_true", help="Create .venv-workflow, install requirements, and relaunch.")
    checks = result.add_mutually_exclusive_group()
    checks.add_argument("--check-case", action="store_true", help="Validate fixture/manifest only; no Codex or run creation.")
    checks.add_argument("--preflight", action="store_true", help="Also check Python dependencies, Codex CLI and login; no model call.")
    return result


def format_document(service, parent, runtime, *, documents_skill=None, renderer=None, purpose="reader-facing",
                    model=None, auto_approve_recommended=False, max_turns=100, input_fn=input):
    """Optional derived operation; the translation run's result remains independently recorded."""
    work_id = parent.state()["work_id"]
    run_id = service.create_derived_run(work_id, "manuscript-formatting-v1", model=model, options={
        "documents_skill": documents_skill, "renderer": renderer, "purpose": purpose})
    with service.open_run(run_id) as job:
        return drive_formatting(parent, job, runtime, auto_approve_recommended=auto_approve_recommended,
                                max_turns=max_turns, input_fn=input_fn)


def drive_formatting(parent, job, runtime, *, auto_approve_recommended, max_turns, input_fn):
    from workflow.src.cli import display
    print(f"Formatting run: {job.state()['id']}\nPath: {job.root}")
    try:
        for _ in range(max_turns):
            state = job.state()
            display(job, state, review=state["status"] == "WAITING_FOR_HUMAN")
            if state["status"] == "COMPLETED":
                print(f"Verified DOCX: {state['document_path']}")
                return 0
            if state["status"] == "READY":
                job.advance(runtime)
            elif state["status"] == "WAITING_FOR_HUMAN":
                if auto_approve_recommended:
                    try:
                        response, suggestion = recommended_response(job)
                    except ValueError as exc:
                        print(f"Formatting needs review: {exc}")
                        return 2
                    job.store.event("e2e.delegated_approval", {"gate_id": state["gate"]["id"], **suggestion})
                    action = "reply"
                else:
                    action, response = read_response(input_fn)
                if action == "/pause":
                    return 2
                if action == "/cancel":
                    job.cancel()
                    return 2
                if action == "/refresh":
                    job.retry(refresh_gate=True)
                else:
                    job.reply(state["gate"]["id"], response,
                              decision_source="delegated-automation" if auto_approve_recommended else "human")
            else:
                print(f"Formatting stopped: {state.get('error') or state['status']}")
                print(f"Retry/review the run with: python -m workflow status {state['id']}")
                return 1 if state["status"] == "FAILED" else 2
        print("Formatting turn limit reached; resume the same parent with --format-docx.")
        return 2
    except EOFError:
        return 2
    finally:
        report_path = parent.root / "e2e-report.json"
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            state = job.state()
            report.setdefault("formatting_jobs", {}).setdefault(state["id"], {}).update({
                "path": str(job.root), "status": state["status"],
                "document_path": state.get("document_path"), "error": state.get("error"),
                "backend": state.get("backend"),
            })
            atomic_json(report_path, report)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parser().parse_args(argv)
    service = None
    try:
        require(math.isfinite(args.timeout) and args.timeout > 0 and args.max_turns > 0,
                "Timeout and max-turns must be positive finite values.")
        if args.setup:
            venv = REPO / ".venv-workflow"
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            if not python.is_file():
                subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
            requirements = "requirements-docx.txt" if args.format_docx and args.documents_skill is None else "requirements.txt"
            subprocess.run([str(python), "-m", "pip", "install", "-r", str(REPO / "workflow" / requirements)], check=True)
            return subprocess.call([str(python), str(Path(__file__).resolve()),
                                    *[arg for arg in argv if arg != "--setup"]])
        case = load_case(args.case)
        print(f"Case: {case['spec']['case_id']}\nInput: {case['source_path']}")
        if args.check_case:
            print("Case definition and source hash verified; no run created.")
            return 0
        from workflow.src.runtime import CodexRuntime
        from workflow.src.service import WorkflowService
        if args.format_docx:
            from workflow.src.formatting import manuscript_paragraphs
            manuscript_paragraphs("# Dependency preflight\n\nText.\n")
            if args.documents_skill:
                adapter = args.documents_skill if args.documents_skill.is_dir() else args.documents_skill.parent
                require((adapter / "SKILL.md").is_file(), "Documents skill is unavailable.")
            else:
                from workflow.src.document_adapters import preflight as document_preflight
                from workflow.src.formatting import select_renderer
                document_preflight(select_renderer(args.renderer))
        service = WorkflowService(args.server_root)
        run_id = args.resume
        if run_id:
            with service.open_run(run_id) as engine:
                status, saved = engine.state()["status"], engine.state().get("e2e")
        needs_runtime = args.format_docx or not run_id or status not in ("COMPLETED", "CANCELLED")
        runtime_info = preflight(case, args.codex) if needs_runtime or args.preflight else saved["runtime"]
        if args.preflight:
            print(f"Preflight passed: {runtime_info['version']}. DOCX extraction capability is verified by the preparation stage.")
            return 0
        model = args.model or case["spec"]["input"]["runtime"].get("model")
        if run_id is None:
            # Each launch uploads the case manuscript, which always creates a new work.
            run_id = service.create_run(case["template_id"], upload=Path(case["source_path"]),
                                        manuscript_language=case["spec"]["input"]["manuscript_language"], model=model,
                                        skip_stages=case["spec"]["input"].get("skip_stages", ()))
        with service.open_run(run_id) as engine:
            bind_case(engine, case, runtime_info, model if not args.resume else args.model, resume=bool(args.resume))
            print(f"Run: {run_id}\nPath: {engine.root}\nResume: python workflow/tests/run_e2e.py --case "
                  f"\"{case['case_path']}\" --server-root \"{service.root}\" --resume {run_id}")
            engine.store.event("e2e.approval_policy", {"auto_approve_recommended": args.auto_approve_recommended,
                                                    "authorization": "explicit command-line opt-in"})
            runtime = CaseRuntime(CodexRuntime([runtime_info["executable"], "app-server"], args.timeout),
                                  engine.state()["e2e"]["case"]["task"],
                                  auto_approve_recommended=args.auto_approve_recommended,
                                  operation="editing" if engine.state()["workflow"] == "literary-editing" else "translation")
            code = drive(engine, case, runtime, max_turns=args.max_turns,
                         auto_approve_recommended=args.auto_approve_recommended)
            if args.format_docx and engine.state()["status"] == "COMPLETED" and code != 1:
                format_runtime = CaseRuntime(
                    CodexRuntime([runtime_info["executable"], "app-server"], args.timeout),
                    "Consolidate the accepted English chapters into one readable DOCX without editorial changes.",
                    auto_approve_recommended=args.auto_approve_recommended, operation="formatting",
                )
                formatted = format_document(
                    service, engine, format_runtime, documents_skill=args.documents_skill, renderer=args.renderer,
                    purpose=args.format_purpose, model=args.model,
                    auto_approve_recommended=args.auto_approve_recommended, max_turns=args.max_turns,
                )
                if formatted:
                    return formatted
            return code
    except ModuleNotFoundError as exc:
        print(f"Missing Python dependency: {exc.name}. Rerun with --setup.", file=sys.stderr)
        return 1
    except (ValueError, OSError, RuntimeError, KeyError, TypeError, BadZipFile, subprocess.SubprocessError) as exc:
        print(f"E2E launcher: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted. Resume the printed run ID; no human approval was inferred.")
        return 130
    finally:
        if service:
            service.close()


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
