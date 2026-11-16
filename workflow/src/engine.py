"""Generic workflow engine: lifecycle, lock, stage walker, gates, receipts, acceptance, export, recovery."""

from __future__ import annotations

import copy
import functools
import importlib.util
import json
import re
import shutil
import uuid
from pathlib import Path

from jsonschema import Draft202012Validator

from . import registry
from .runtime import Request
from .storage import Store, digest, json_bytes, local_file, now, plain, read_bytes, write_new

WORKFLOW_ROOT = registry.WORKFLOW_ROOT
REPO = WORKFLOW_ROOT.parent
SKILLS = REPO / "plugins/manuscript-studio/skills"
TERMINAL = ("COMPLETED", "CANCELLED")
PASS_ACCEPT, PASS_FINISH = "accept pass", "finish"
SELECT_GATES = ("pass_review", "pass_choice")
LANGUAGE_TAG = re.compile(r"[a-z]{2,3}(-[A-Za-z0-9]{2,8})*")
WORK_ID = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
NULL_PATH = {"type": ["string", "null"]}
BASE_RESULT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["outcome", "message", "state_path", "work_record", "output_path",
                 "gate", "review_path", "binding_path"],
    "properties": {
        "outcome": {"enum": ["needs_human_input", "completed", "blocked"]},
        "message": {"type": "string", "minLength": 1},
        "state_path": NULL_PATH,
        "work_record": NULL_PATH,
        "output_path": NULL_PATH,
        "gate": {"enum": [None]},
        "review_path": NULL_PATH,
        "binding_path": NULL_PATH,
    },
}


class WorkflowError(ValueError):
    """A refusal with a stable code for clients (work_busy, run_finalized, engine_updated, ...)."""

    def __init__(self, code, message):
        super().__init__(f"{code}: {message}")
        self.code = code


def module_at(path):
    spec = importlib.util.spec_from_file_location("_workflow_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def result_schema(gates, fields=()):
    """The runtime result contract for one stage: its declared gates and any extra result paths."""
    schema = copy.deepcopy(BASE_RESULT_SCHEMA)
    schema["properties"]["gate"] = {"enum": [None, *gates]}
    for name in fields:
        schema["properties"][name] = NULL_PATH
        schema["required"].append(name)
    return schema


def item_signature(sheet, item, binding_hash):
    decisions = {d["id"]: d for d in sheet["decisions"]}
    # Status/date are domain-maintained; the reviewed proposal and options are not.
    value = {key: item[key] for key in ("id", "summary", "details", "dependencies", "allowed_decisions")}
    value["decisions"] = [decisions[key] for key in item["allowed_decisions"]]
    value["binding"] = binding_hash
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False).encode())


def finalization_notice(workflow):
    return (f"Accepting finalizes this run: its output is published as the next {workflow} version on this "
            "work and that version can never change. No chapter or stage of this run can be restarted afterwards; "
            "a later run on the work publishes a new version.")


def configure(template, model=None, agent_models=None):
    """Apply per-run model choices to a pinned copy of the template."""
    template = copy.deepcopy(template)
    for name, value in ({name: model for name in template["agents"]} if model else {}).items():
        template["agents"][name]["model"] = value
    for name, value in (agent_models or {}).items():
        if name not in template["agents"]:
            raise ValueError(f"Unknown agent for this template: {name}")
        template["agents"][name]["model"] = value
    for agent in template["agents"].values():
        if agent["model"] is not None and (not isinstance(agent["model"], str) or not agent["model"].strip()):
            raise ValueError("Model must be null or a nonempty model identifier.")
    return template


def pin_directories(directories):
    """Inventory complete skill directories, refusing links, before anything is copied."""
    inventory = {}
    for name, directory in directories.items():
        if not (directory / "SKILL.md").is_file():
            raise ValueError(f"Missing skill: {name}")
        for path in directory.rglob("*"):
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            plain(path)
            if path.is_file():
                if path.stat().st_nlink != 1:
                    raise ValueError(f"Linked skill resource: {path}")
                inventory[f"{name}/{path.relative_to(directory).as_posix()}"] = (path, digest(read_bytes(path)))
    return inventory


def engine_for_state(state):
    if state.get("template_id") not in registry.templates():
        return ArchivedEngine
    reference = state.get("definition", {}).get("engine")
    if reference is None:
        from .translation import TranslationEngine  # Pre-M1 translation runs.
        return TranslationEngine
    return registry.engine_class(reference)


class Engine:
    """Base engine. Subclasses implement prompts and domain completion through hooks."""

    result_fields = ()
    retired = False

    def __init__(self, root, *, library=None):
        self.store = Store(root)
        self.root = self.store.root
        self.workspace = self.root / "workspace"
        self.library = library

    @classmethod
    def open(cls, root, *, library=None):
        store = Store(root)
        try:
            state = store.load()[1]
        finally:
            store.close()
        return engine_for_state(state)(root, library=library)

    def close(self):
        self.store.close()

    @functools.cached_property
    def approval(self):
        return module_at(self.root / "skills/review-approval-sheet/scripts/approval_review.py")

    @functools.cached_property
    def preparation(self):
        return module_at(self.root / "skills/prepare-manuscript/scripts/validate_preparation.py")

    # ----- creation -------------------------------------------------------------------------

    @classmethod
    def preflight(cls, template):
        """Check dependencies before creating a run."""

    @classmethod
    def resolve_settings(cls, template, settings, manuscript_language):
        """Per-run settings chosen at creation, with template defaults applied; fixed for the run."""
        if settings:
            raise ValueError("This template has no run settings.")
        return {}

    @classmethod
    def skill_directories(cls, template):
        names = sorted({name for agent in template["agents"].values() for name in agent["skills"]})
        return {name: SKILLS / name for name in names}

    @classmethod
    def initial_state(cls, template, **fields):
        return {
            "id": str(uuid.uuid4()), "created_at": now(), "template_id": template["id"],
            "workflow": template["workflow"], "definition": template,
            "engine": registry.engine_identity(template["id"]),
            "status": "READY", "stage": template["stages"][0]["id"], "attempts": 0, "error": None,
            "thread_id": None, "gate": None, "receipts": [], "next_input": None, "domain_state": None,
            "approvals": {}, "outputs": [], "restarts": [], "stage_epochs": {}, "inputs": [],
            "library_heads": {}, "passes": [], **fields,
        }

    @classmethod
    def create(cls, root, template, *, source, manuscript_language, work_id, owner=None, source_name=None,
               model=None, agent_models=None, library=None, run_id=None, settings=None):
        root, source = plain(Path(root)), plain(Path(source))
        if not source.is_file() or source.stat().st_nlink != 1:
            raise ValueError("Designate one regular, non-linked source file.")
        if source.is_relative_to(root):
            raise ValueError("The run directory cannot contain the designated source.")
        if manuscript_language is not None and (
                not isinstance(manuscript_language, str) or not LANGUAGE_TAG.fullmatch(manuscript_language)):
            raise ValueError("Use a manuscript-language tag such as zh or zh-CN.")
        if not isinstance(work_id, str) or not WORK_ID.fullmatch(work_id) or len(work_id) > 100:
            raise ValueError("A lowercase work ID such as my-book-1a2b3c is required.")
        name = source_name or source.name
        if Path(name).name != name or name in ("", ".", ".."):
            raise ValueError("Invalid source file name.")
        template = configure(template, model, agent_models)
        source_data = read_bytes(source)
        settings = cls.resolve_settings(template, dict(settings or {}), manuscript_language)
        cls.preflight(template)
        inventory = pin_directories(cls.skill_directories(template))
        state = cls.initial_state(
            template, work_id=work_id, owner=owner, manuscript_language=manuscript_language,
            source_name=name, source_origin=str(source), source_hash=digest(source_data),
            skills={relative: sha for relative, (_, sha) in inventory.items()}, settings=settings,
            **({"id": run_id} if run_id else {}),
        )
        Store.create(root, state).close()
        engine = cls(root, library=library)
        engine._initialize(state, {name: source_data}, inventory, "original")
        return engine

    def _initialize(self, state, inputs, inventory, role):
        with self.store.locked():
            for relative, data in inputs.items():
                target = self.root / "input" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            for relative, (origin, sha) in inventory.items():
                target = self.root / "skills" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(origin, target)
                if digest(target.read_bytes()) != sha:
                    raise ValueError("Skill source changed during initialization.")
            state["source"] = self.store.snapshot(self.root / "input" / state["source_name"], role)
            self._checkout(state)
            self.after_checkout(state)
            self.store.save(0, state, "run.created", {"template": state["template_id"], "work_id": state["work_id"]})

    def format_path(self, state, text, **extra):
        passes = state.get("passes") or []
        label = f"{passes[-1]['number']:03d}-{passes[-1]['stage']}" if passes else "000"
        values = {"target": state.get("target_language"), "work_id": state["work_id"], "pass": label, **extra}
        return text.format_map(values)

    def _checkout(self, state):
        """Copy the latest published library versions into the workspace and record them as inputs."""
        if self.library is None:
            return
        for edit in self.library.detect_edits():
            self.store.event("library.user_edit_detected", edit)
        for entry in state["definition"].get("library", {}).get("checkout", []):
            artifact = self.format_path(state, entry["artifact"])
            head = self.library.head(artifact)
            if head is None:
                continue
            target = plain(self.workspace / entry["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.library.read(head))
            state["inputs"].append({"artifact": artifact, "path": entry["path"], "publication_id": head["id"],
                                    "sha256": head["sha256"], "review_status": head.get("review_status")})

    def after_checkout(self, state):
        """Hook after library checkout during creation."""

    def seed_workspace(self, files, origin):
        """Carry selected files (e.g. glossary/voice) into a new run before its first turn."""
        with self.store.locked():
            revision, state = self.store.load()
            if state["attempts"] or state["status"] != "READY":
                raise ValueError("Only a new run can be seeded.")
            for relative, data in files.items():
                target = plain(self.workspace / relative)
                if not target.is_relative_to(self.workspace):
                    raise ValueError("Seeded files must stay in the workspace.")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            state["carried_from"] = origin
            self.after_checkout(state)
            self.store.save(revision, state, "workspace.seeded", origin)
            return state

    # ----- state helpers --------------------------------------------------------------------

    def state(self):
        return self.store.load()[1]

    def events(self, after=0):
        return self.store.events(after)

    def file(self, relative):
        return local_file(self.workspace, relative)

    def checkpoint(self, relative, role):
        result = self.store.snapshot(self.file(relative), role)
        result["path"] = relative
        return result

    @staticmethod
    def stage_def(state, stage_id=None):
        stage_id = stage_id or state["stage"]
        stage = next((stage for stage in state["definition"]["stages"]
                      if stage["id"] == stage_id), None)
        if stage is None:
            raise ValueError(f"Unknown stage for this run: {stage_id}")
        return stage

    def _stage_or_empty(self, state):
        try:
            return self.stage_def(state)
        except ValueError:
            return {}  # Pre-M1 runs are readable but not executable.

    @staticmethod
    def option_stages(state):
        """Stages that run only when the user picks them at a select stage (e.g. editing passes)."""
        return {option["stage"] for stage in state["definition"]["stages"] if stage["kind"] == "select"
                for option in stage["options"]}

    @staticmethod
    def stage_ids(state):
        """The run's fixed stage sequence; option stages run in between, at their select stage."""
        options = Engine.option_stages(state)
        return [stage["id"] for stage in state["definition"]["stages"] if stage["id"] not in options]

    @staticmethod
    def select_of(state, stage_id):
        """The select stage offering stage_id as an option, or None for a stage of the fixed sequence."""
        return next((stage for stage in state["definition"]["stages"] if stage["kind"] == "select"
                     and any(option["stage"] == stage_id for option in stage["options"])), None)

    @staticmethod
    def open_pass(state):
        """The latest chosen pass while its output is not yet accepted."""
        passes = state.get("passes") or []
        return passes[-1] if passes and not passes[-1]["accepted"] else None

    def stage_of_kind(self, state, kind):
        return next((stage for stage in state["definition"]["stages"] if stage["kind"] == kind), None)

    def current_iteration(self, state):
        return None

    def instance(self, state):
        """The scope of gates and receipts: stage, restart epoch, and chapter attempt."""
        stage = state["stage"]
        epoch = state["stage_epochs"].get(stage, 1)
        iteration = self.current_iteration(state) if self.stage_def(state).get("iterate") else None
        chapter_id = iteration["chapter_id"] if iteration else None
        attempt = iteration["attempt"] if iteration else 0
        return {"stage": stage, "epoch": epoch, "chapter_id": chapter_id, "attempt": attempt,
                "key": f"{stage}/{epoch}/{chapter_id or '-'}/{attempt}"}

    def finalized(self, state):
        return bool(state.get("acceptance"))

    def engine_outdated(self, state):
        recorded = state.get("engine")
        if not recorded:
            return True
        try:
            return registry.engine_identity(state["template_id"]) != recorded
        except (KeyError, ValueError):
            return True

    def _guard(self, state, operation):
        if state["status"] in TERMINAL or operation == "stop" or not self.engine_outdated(state):
            return
        if self.finalized(state) and operation in ("step", "retry"):
            return  # A finalized run may still write its accepted snapshots.
        raise WorkflowError("engine_updated", "The workflow engine changed after this run was created; "
                                              "only reading, stopping and restarting the workflow are available.")

    def _require_mutable(self, state):
        if state["status"] == "CANCELLED":
            raise WorkflowError("run_cancelled", "This run was stopped.")
        if self.finalized(state) or state["status"] == "COMPLETED":
            raise WorkflowError("run_finalized", "This run is finalized; start a new run on the work to "
                                                 "publish a new version.")
        if state["status"] == "RUNNING":
            raise ValueError("An agent turn is running; interrupt it, or retry with --confirm-stopped after a crash.")

    def verify(self, state):
        if digest(read_bytes(plain(self.root / "input" / state["source_name"]))) != state["source_hash"]:
            raise ValueError("Original input snapshot changed.")
        for relative, sha in state["skills"].items():
            if digest(read_bytes(local_file(self.root / "skills", relative))) != sha:
                raise ValueError("Pinned skill bundle changed.")
        self.verify_extra(state)
        for artifact in state["outputs"]:
            self.store.content(artifact)
            if digest(read_bytes(self.file(artifact["path"]))) != artifact["sha256"]:
                raise ValueError("A completed chapter changed outside this run's approval lifecycle.")

    def verify_extra(self, state):
        """Hook for template-specific protected inputs."""

    # ----- hooks ----------------------------------------------------------------------------

    def stage_prompt(self, state, stage):
        raise NotImplementedError

    def result_fields_for(self, state):
        return self.result_fields

    def result_schema_for(self, state):
        return result_schema(self.stage_def(state).get("gates", []), self.result_fields_for(state))

    def check_result(self, state, stage, result):
        """Hook: reject results that violate the stage's domain contract."""

    def before_turn(self, state):
        """Hook before an agent turn is recorded as started."""

    def after_turn(self, state):
        """Hook after a successful agent turn result."""

    def on_waiting(self, state, stage, result):
        """Hook before a gate is recorded."""

    def on_gate(self, state, gate, result):
        """Hook after a gate is built."""

    def on_completed(self, state, stage, result):
        self._advance_stage(state)

    def gate_commands(self, state, gate):
        """Exact replies a client can offer as buttons for a gate without an approval sheet."""
        if gate.get("options"):
            return [option["command"] for option in gate["options"]]
        if gate.get("sheet"):
            return []
        if gate["kind"] == "metadata_review":
            return []
        rules = state["definition"]["gates"].get(gate["kind"], {})
        return [command for command in (rules.get("command"), rules.get("empty_command")) if command]

    def parse_free_reply(self, state, gate, text):
        """Without a sheet, only the gate's exact declared command closes it; anything else is feedback."""
        rules = state["definition"]["gates"].get(gate["kind"], {})
        command = rules.get("command") or rules.get("empty_command")
        if command and text.strip() == command:
            return {"type": "final-closure", "command": command}
        return {"type": "feedback", "text": text}

    def publish_accepted(self, state):
        """Hook: publish accepted artifacts at final acceptance. The base only records finalization."""
        if self.library is not None:
            areas = [self.format_path(state, area) for area in state["definition"].get("library", {}).get("areas", [])]
            self.library.publish_many([], run_id=state["id"], workflow=state["workflow"], stage="accept",
                                      receipts=[state["acceptance"]["id"]], finalize=areas)

    def export_files(self, state):
        files = {f"{index:04d}.md": self.store.content(artifact) for index, artifact in enumerate(state["outputs"], 1)}
        files["manifest.json"] = json_bytes({"run_id": state["id"], "work_id": state["work_id"],
                                             "template_id": state["template_id"], "acceptance": state["acceptance"],
                                             "source": state["source"], "chapters": state["outputs"]})
        return files

    def delivery_files(self, state):
        """Additional verified native outputs included in final publication/export."""
        return {}

    def production_step(self, revision, state):
        raise ValueError("This workflow has no deterministic production implementation.")

    def accepted_output(self, state):
        return None

    @classmethod
    def resolve_options(cls, options):
        """Derived templates: resolve creation options such as renderer choices."""
        raise ValueError("This template does not accept derived-run options.")

    @classmethod
    def derived_identity(cls, accepted, options, model):
        return None

    def carry_forward(self, state):
        return None

    def reset_stage(self, state, stage):
        """Hook: reset state produced by a stage that is being restarted."""

    def restart_restore(self, state, stage_ids):
        """Hook: workspace files to restore after a stage restart, as {path: snapshot or None}."""
        return {}

    def pass_result(self, state):
        """Hook: the protected result of a completed pass (e.g. chapter snapshots), checked until it is replaced."""
        return None

    def pass_summary(self, state, record):
        """Hook: a short description of a completed pass's result for its acceptance decision."""
        return ""

    def on_pass_accepted(self, state, record):
        """Hook after the user accepts a pass's output."""

    # ----- select stages: passes chosen by the user ---------------------------------------
    # The engine owns both decisions of a select stage: accepting the last pass's output, then choosing the
    # next pass or continuing with the fixed sequence. No agent reads them, so only exact commands count.

    def _present_choice(self, state):
        stage = self.stage_def(state)
        passes = state.setdefault("passes", [])
        current = self.open_pass(state)
        if current:
            title = next(o["title"] for o in stage["options"] if o["stage"] == current["stage"])
            kind = "pass_review"
            options = [{"command": PASS_ACCEPT, "title": f"Accept the {title.lower()} output"}]
            message = (f"Pass {current['number']}, {title.lower()}, is complete. "
                       f"{self.pass_summary(state, current)}".strip() + "\n\nAccept its output to continue: the "
                       "accepted text is the starting point for the next pass or final acceptance. To redo the pass "
                       "instead, restart its stage.")
        else:
            ids = self.stage_ids(state)
            following = ids[ids.index(stage["id"]) + 1] if ids.index(stage["id"]) + 1 < len(ids) else None
            finish = ("Proceed to final acceptance" if following and self.stage_def(state, following)["kind"]
                      == "acceptance" else "Finish")
            kind = "pass_choice"
            options = [{"command": f"run {o['stage']}", "stage": o["stage"], "title": o["title"],
                        "description": o.get("description")} for o in stage["options"]]
            options.append({"command": PASS_FINISH, "finish": True, "title": finish})
            message = (f"{len(passes)} pass{'es' if len(passes) != 1 else ''} accepted so far. " if passes else "") + \
                f"Choose the next pass, or {finish.lower()}."
        epoch = state["stage_epochs"].get(stage["id"], 1)
        state["gate"] = {"id": str(uuid.uuid4()), "kind": kind, "message": message, "stage": stage["id"],
                         "chapter_id": None, "attempt": len(passes), "instance": f"{stage['id']}/{epoch}/-/{len(passes)}",
                         "binding": None, "sheet": None, "options": options,
                         "pass": current["number"] if current else None}
        state["status"] = "WAITING_FOR_HUMAN"

    def _choose(self, revision, state, gate, text, decision_source):
        option = next((o for o in gate["options"] if o["command"] == text.strip()), None)
        if option is None:
            raise ValueError("Reply with exactly one of: " + ", ".join(f"'{o['command']}'" for o in gate["options"]) + ".")
        receipt = {"id": str(uuid.uuid4()), "created_at": now(), "gate": gate, "text": text,
                   "parsed": {"type": "final-closure", "command": option["command"]}, "decision_source": decision_source}
        state["receipts"].append(receipt)
        state.update(next_input=None, gate=None, status="READY")
        if gate["kind"] == "pass_review":
            record = self.open_pass(state)
            record["accepted"] = {"receipt_id": receipt["id"], "created_at": receipt["created_at"],
                                  "decision_source": decision_source}
            self.on_pass_accepted(state, record)
            self._present_choice(state)
            event, payload = "pass.accepted", {"pass": record["number"], "stage": record["stage"]}
        elif option.get("finish"):
            self._advance_stage(state)
            event, payload = "passes.finished", {"passes": len(state["passes"])}
        else:
            passes = state["passes"]
            if any(p["stage"] == option["stage"] for p in passes):
                # A repeated pass gets its own restart epoch, so its decisions never mix with an earlier pass.
                state["stage_epochs"][option["stage"]] = state["stage_epochs"].get(option["stage"], 1) + 1
            record = {"number": len(passes) + 1, "stage": option["stage"],
                      "epoch": state["stage_epochs"].get(option["stage"], 1), "receipt_id": receipt["id"],
                      "started_at": now(), "completed_at": None, "result": None, "accepted": None, "restarts": 0}
            passes.append(record)
            self._enter_stage(state, option["stage"])
            event, payload = "pass.started", {"pass": record["number"], "stage": record["stage"]}
        self.store.save(revision, state, event, {**payload, "receipt_id": receipt["id"], "gate_id": gate["id"]})
        return state

    def _present_metadata(self, state):
        raise ValueError("This template has no metadata review support.")

    def _confirm_metadata(self, revision, state, gate, text, decision_source):
        raise ValueError("This template has no metadata review support.")

    # ----- stage walker ---------------------------------------------------------------------

    def _enter_stage(self, state, stage_id):
        state.update(stage=stage_id, thread_id=None, domain_state=None, approvals={}, gate=None)
        kind = self.stage_def(state)["kind"]
        if kind == "metadata_review":
            self._present_metadata(state)
        elif kind == "select":
            self._present_choice(state)
        elif kind == "acceptance":
            state.update(status="WAITING_FOR_ACCEPTANCE", acceptance_id=str(uuid.uuid4()))
        else:
            state["status"] = "READY"

    def _advance_stage(self, state):
        select = self.select_of(state, state["stage"])
        if select:
            # A completed pass returns to its select stage, where the user accepts its output.
            self.open_pass(state).update(completed_at=now(), result=self.pass_result(state))
            self._enter_stage(state, select["id"])
            return
        ids = self.stage_ids(state)
        position = ids.index(state["stage"]) + 1
        if position == len(ids):
            state["status"] = "COMPLETED"
        else:
            self._enter_stage(state, ids[position])

    def advance(self, runtime):
        with self.store.locked():
            revision, state = self.store.load()
            self._guard(state, "step")
            if state["status"] != "READY":
                raise ValueError(f"Run is {state['status']}; resolve or retry it before advancing.")
            self.verify(state)
            stage = self.stage_def(state)
            if stage["kind"] == "production":
                return self.production_step(revision, state)
            if stage["kind"] == "export":
                return self._export(revision, state)
            if stage["kind"] in ("metadata_review", "select", "acceptance"):
                self._enter_stage(state, stage["id"])
                state["next_input"] = None
                if stage["kind"] == "metadata_review":
                    self.store.save(revision, state, "metadata.review_requested",
                                    {"gate_id": state["gate"]["id"], "record_revision": state["gate"]["record_revision"]})
                elif stage["kind"] == "select":
                    self.store.save(revision, state, "selection.requested",
                                    {"gate_id": state["gate"]["id"], "gate": state["gate"]["kind"]})
                else:
                    self.store.save(revision, state, "acceptance.requested", {"acceptance_id": state["acceptance_id"]})
                return state
            model = state["definition"]["agents"][stage["agent"]].get("model")
            if hasattr(runtime, "describe"):
                execution = runtime.describe(model, state["workflow"])
                if state.get("execution") != execution:
                    state["thread_id"] = None
                state["execution"] = execution
            elif state.get("execution"):
                raise ValueError("This run requires an execution profile; use --execution-profile to continue.")
            self.before_turn(state)
            state.update(status="RUNNING", attempts=state["attempts"] + 1, error=None)
            revision = self.store.save(revision, state, "execution.started",
                                       {"stage": state["stage"], "chapter_id": self.instance(state)["chapter_id"],
                                        "execution": state.get("execution")})

            def on_thread(thread_id):
                nonlocal revision
                state["thread_id"] = thread_id
                revision = self.store.save(revision, state, "execution.thread", {"thread_id": thread_id})

            try:
                schema = self.result_schema_for(state)
                result = runtime.run(Request(
                    self.workspace, self.stage_prompt(state, stage),
                    model,
                    state["thread_id"], schema,
                ), self.store.event, on_thread)
                error = next(Draft202012Validator(schema).iter_errors(result), None)
                if error:
                    raise ValueError(f"Invalid runtime result: {error.message}")
                self.verify(state)
                self._result(state, result)
                self.after_turn(state)
                state["next_input"] = None
                self.store.save(revision, state, "execution.result", result)
            except (Exception, KeyboardInterrupt) as exc:
                # Keep the last committed domain state, including any pending receipt.
                revision, saved = self.store.load()
                saved.update(status="PAUSED" if isinstance(exc, KeyboardInterrupt) else "FAILED",
                             error=str(exc) or type(exc).__name__)
                self.store.save(revision, saved, "execution.failed", {"error": saved["error"]})
                raise
            return state

    def _result(self, state, result):
        stage = self.stage_def(state)
        self.check_result(state, stage, result)
        if result["state_path"]:
            state["domain_state"] = self.checkpoint(result["state_path"], "domain_state")
        if result["outcome"] == "blocked":
            state.update(status="BLOCKED", error=result["message"])
            return
        if result["outcome"] == "needs_human_input":
            self._wait(state, result)
            return
        if result["gate"] is not None:
            raise ValueError("Completed results cannot carry an unresolved gate.")
        self.on_completed(state, stage, result)

    # ----- gates and receipts ---------------------------------------------------------------

    def _wait(self, state, result):
        kind = result["gate"]
        stage = self.stage_def(state)
        if kind is None:
            raise ValueError("A waiting result must identify its gate.")
        if kind not in stage.get("gates", []):
            raise ValueError(f"Stage {stage['id']} cannot request a {kind} gate.")
        rules = state["definition"]["gates"][kind]
        self.on_waiting(state, stage, result)
        instance = self.instance(state)
        gate = {"id": str(uuid.uuid4()), "kind": kind, "message": result["message"], "stage": stage["id"],
                "chapter_id": instance["chapter_id"], "attempt": instance["attempt"], "instance": instance["key"],
                "binding": None, "sheet": None}
        if result["binding_path"]:
            gate["binding"] = self.checkpoint(result["binding_path"], kind)
        if rules.get("binding") == "required" and not gate["binding"]:
            raise ValueError("This review requires an exact bound checkpoint.")
        if rules.get("documents"):
            paths = [self.format_path(state, path) for path in rules["documents"]]
            missing = [path for path in paths if not (self.workspace / path).is_file()]
            if missing:
                raise ValueError(f"The {kind} review presents {', '.join(paths)}; save {', '.join(missing)} first.")
            gate["documents"] = [self.checkpoint(path, "document") for path in paths]
        if result["review_path"]:
            gate["sheet"] = self.checkpoint(result["review_path"], "review_sheet")
            sheet = json.loads(self.store.content(gate["sheet"]))
            self.approval.validate_sheet(sheet)
            if rules.get("closure") == "required" and (
                not sheet["gate"]["closure_required"] or sheet["gate"]["final_closure"] != "pending"
            ):
                raise ValueError("Reviews with final closure require a pending separate final closure.")
            self._verify_dispositions(state, gate, sheet)
            for old in state["receipts"]:
                if old["gate"]["sheet"] and old["gate"].get("instance") == gate["instance"]:
                    previous = json.loads(self.store.content(old["gate"]["sheet"]))
                    if (previous["sheet_id"], previous["revision"]) == (sheet["sheet_id"], sheet["revision"]):
                        raise ValueError("A submitted sheet revision cannot be reused.")
        elif rules.get("sheet") == "required":
            raise ValueError(f"The {kind} gate requires an approval sheet, even for one item.")
        self.on_gate(state, gate, result)
        if rules.get("closure") in ("required", "implied"):
            state["approvals"].pop(kind, None)  # A new review invalidates an earlier closure.
        state.update(status="WAITING_FOR_HUMAN", gate=gate)

    def _verify_dispositions(self, state, gate, sheet):
        bound = state["definition"]["gates"].get(gate["kind"], {}).get("item_binding", False)
        for item in sheet["items"]:
            if item["status"] != "resolved":
                continue
            latest = None
            # Every claimed resolved item needs an actual user receipt for the same proposal and instance.
            for receipt in state["receipts"]:
                old_gate = receipt["gate"]
                if old_gate.get("instance") != gate["instance"] or old_gate["kind"] != gate["kind"]:
                    continue
                if not old_gate["sheet"] or receipt["parsed"].get("type") != "dispositions":
                    continue
                old_sheet = json.loads(self.store.content(old_gate["sheet"]))
                if old_sheet["sheet_id"] != sheet["sheet_id"]:
                    continue
                old_item = next((x for x in old_sheet["items"] if x["id"] == item["id"]), None)
                # Some entries survive changes elsewhere (maps); item-bound reviews bind all text.
                binding = gate["binding"]["sha256"] if bound else None
                old_binding = old_gate["binding"]["sha256"] if bound else None
                if not old_item or item_signature(old_sheet, old_item, old_binding) != item_signature(sheet, item, binding):
                    continue
                for decision in receipt["parsed"]["dispositions"]:
                    if decision["item_id"] == item["id"]:
                        latest = decision
            if (latest is None or latest["effect"] != "resolve"
                    or latest["decision"] != item["response"]["decision"]
                    or latest["note"] != item["response"]["note"]):
                raise ValueError(f"Resolved item {item['id']} has no matching human disposition.")

    def reply(self, gate_id, text, *, decision_source="human"):
        if decision_source not in ("human", "delegated-automation"):
            raise ValueError("Unknown decision source.")
        with self.store.locked():
            revision, state = self.store.load()
            self._guard(state, "reply")
            if state["status"] != "WAITING_FOR_HUMAN" or not state["gate"] or state["gate"]["id"] != gate_id:
                raise ValueError("Stale or already answered gate.")
            if not text.strip():
                raise ValueError("A response is required.")
            self.verify(state)
            gate = state["gate"]
            if gate["kind"] == "docx_generation_review":
                raise ValueError("Use the DOCX generation form to authorize this exact plan.")
            presented = [gate[key] for key in ("binding", "sheet", "settings") if gate.get(key)] + gate.get("documents", [])
            for item in presented:
                if digest(read_bytes(self.file(item["path"]))) != item["sha256"]:
                    raise ValueError("Review changed after presentation; retry and request a new revision.")
            if gate["kind"] == "metadata_review":
                return self._confirm_metadata(revision, state, gate, text, decision_source)
            if gate["kind"] in SELECT_GATES:
                return self._choose(revision, state, gate, text, decision_source)
            if gate["sheet"]:
                sheet = json.loads(self.store.content(gate["sheet"]))
                self._verify_dispositions(state, gate, sheet)
                parsed = self.approval.parse_response(sheet, text)
                if parsed["type"] == "dispositions":
                    # One complete submission per sheet revision: every open item must be decided together.
                    decided = {d["item_id"] for d in parsed["dispositions"]}
                    missing = [i["id"] for i in sheet["items"] if i["status"] != "resolved" and i["id"] not in decided]
                    if missing:
                        raise ValueError(f"Decide all open items before submitting; missing: {', '.join(missing)}.")
                    # Where a later step shows the full result, a complete resolving submission is the closure.
                    rules = state["definition"]["gates"].get(gate["kind"], {})
                    if rules.get("closure") == "implied" and all(d["effect"] == "resolve" for d in parsed["dispositions"]):
                        parsed = {**parsed, "implied_closure": True}
            else:
                parsed = self.parse_free_reply(state, gate, text)
            receipt = {"id": str(uuid.uuid4()), "created_at": now(), "gate": gate, "text": text,
                       "parsed": parsed, "decision_source": decision_source}
            state["receipts"].append(receipt)
            closed = parsed["type"] == "final-closure" or parsed.get("implied_closure")
            if closed:
                self._record_closure(state, gate)
            state.update(next_input=receipt, status="READY", gate=None)
            if closed:
                self.on_closure(state, gate, receipt)
            self.store.save(revision, state, "review.received", {"receipt_id": receipt["id"], "gate_id": gate_id})
            return state

    def _record_closure(self, state, gate):
        state["approvals"][gate["kind"]] = gate["binding"] or {"documents": gate.get("documents")}

    def on_closure(self, state, gate, receipt):
        """Hook after a gate closes; the run is READY with the receipt as the next input."""

    # ----- acceptance and export ------------------------------------------------------------

    def acceptance_details(self, state):
        return {"title": "Final acceptance", "action_label": "Accept and finalize", "finalizes": True,
                "notice": finalization_notice(state["workflow"])}

    def record_acceptance(self, state, receipt):
        state["acceptance"] = receipt
        self.publish_accepted(state)

    def prepare_acceptance(self, state, format_target):
        if format_target is not None:
            raise ValueError("This acceptance does not select a formatting target.")

    def accept(self, acceptance_id, *, confirm_final=False, decision_source="human", format_target=None):
        if decision_source not in ("human", "delegated-automation"):
            raise ValueError("Unknown decision source.")
        with self.store.locked():
            revision, state = self.store.load()
            self._guard(state, "accept")
            if state["status"] != "WAITING_FOR_ACCEPTANCE" or state.get("acceptance_id") != acceptance_id:
                raise ValueError("Stale or unavailable artifact acceptance.")
            details = self.acceptance_details(state)
            notice = details["notice"]
            if confirm_final is not True:
                raise WorkflowError("confirmation_required", notice + " Confirm the approval notice to accept.")
            self.verify(state)
            self.prepare_acceptance(state, format_target)
            receipt = {"id": acceptance_id, "created_at": now(), "decision_source": decision_source,
                       "hashes": [a["sha256"] for a in state["outputs"]],
                       "finalization" if details["finalizes"] else "confirmation": {"confirmed": True, "notice": notice}}
            try:
                self.record_acceptance(state, receipt)
            except WorkflowError as exc:
                # Publication is all-or-nothing; the run is not finalized.
                state.pop("acceptance", None)
                state.update(status="BLOCKED", error=str(exc))
                self.store.save(revision, state, "acceptance.blocked", {"error": state["error"]})
                raise
            self._advance_stage(state)
            self.store.save(revision, state, "artifacts.accepted" if details["finalizes"] else "manuscript.approved", receipt)
            return state

    def _export(self, revision, state):
        if state.get("acceptance", {}).get("hashes") != [a["sha256"] for a in state["outputs"]]:
            raise ValueError("Export requires acceptance of exactly these artifact versions.")
        target = plain(self.root / "export")
        target.mkdir(exist_ok=True)
        files = self.export_files(state)
        for name in files:
            path = plain(target / name)
            if path.exists() and path.read_bytes() != files[name]:
                raise ValueError("Export destination differs; refusing to overwrite it.")
        for name, data in files.items():
            write_new(target / name, data)
        state.update(status="COMPLETED", export_path=str(target))
        self.store.save(revision, state, "run.completed", {"export": str(target)})
        return state

    def mark_handed_off(self, work_id):
        """Record the work created from this completed run's document (see the template's hands_off)."""
        with self.store.locked():
            revision, state = self.store.load()
            if state["status"] != "COMPLETED":
                raise ValueError("Only a completed run can hand off its output.")
            state["handed_off_work"] = work_id
            self.store.save(revision, state, "work.handed_off", {"work_id": work_id})
            return state

    # ----- recovery -------------------------------------------------------------------------

    def retry(self, *, confirm_stopped=False, refresh_gate=False):
        with self.store.locked():
            revision, state = self.store.load()
            self._guard(state, "retry")
            allowed = {"FAILED", "BLOCKED", "PAUSED", "RUNNING"}
            if refresh_gate:
                allowed.add("WAITING_FOR_HUMAN")
            if state["status"] not in allowed:
                raise ValueError("This run does not need a retry.")
            if self.finalized(state) and self.stage_def(state)["kind"] != "export":
                raise WorkflowError("run_finalized", "This run is finalized; only a failed export can be retried.")
            if state["status"] == "RUNNING" and not confirm_stopped:
                raise ValueError("Stop the previous Codex process, then pass --confirm-stopped.")
            self.verify(state)
            if refresh_gate:
                state["next_input"] = {"type": "refresh_gate",
                                       "message": "Revalidate saved domain state and present a new review revision."}
                state["gate"] = None
            state.update(status="READY", thread_id=None, error=None)
            self.store.save(revision, state, "execution.retried")
            return state

    def cancel(self, *, superseded_by=None, confirm_stopped=False):
        with self.store.locked():
            revision, state = self.store.load()
            if state["status"] in TERMINAL:
                raise ValueError("Run is already terminal.")
            if superseded_by is None:
                self._guard(state, "stop")
            if self.finalized(state):
                raise WorkflowError("run_finalized", "A finalized run can only complete its export.")
            if state["status"] == "RUNNING" and not confirm_stopped:
                raise ValueError("Interrupt the active step first, or retry after confirming it stopped.")
            state["status"] = "CANCELLED"
            if superseded_by:
                state["superseded_by"] = superseded_by
            self.store.save(revision, state, "run.cancelled", {"superseded_by": superseded_by})
            return state

    def _archive(self, relative, archive):
        source = plain(self.workspace / relative.rstrip("/"))
        if not source.is_relative_to(self.workspace) or source == self.workspace:
            raise ValueError("Owned paths must be inside the workspace.")
        if not source.exists():
            return False
        target = plain(archive / relative.rstrip("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        return True

    def _restore(self, state, files, archive):
        for relative, snapshot in files.items():
            self._archive(relative, archive)
            if snapshot:
                target = plain(self.workspace / relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(self.store.content(snapshot))

    def _new_archive(self, name):
        base = plain(self.root / "archive")
        base.mkdir(exist_ok=True)
        path, number = base / name, 1
        while path.exists():
            number += 1
            path = base / f"{name}-{number}"
        path.mkdir()
        return path

    def restart_stage(self, stage_id, *, reason):
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("A restart reason is required.")
        with self.store.locked():
            revision, state = self.store.load()
            self._guard(state, "restart")
            self._require_mutable(state)
            ids = self.stage_ids(state)
            current = self.open_pass(state)
            select = self.select_of(state, state["stage"])
            position = ids.index(select["id"] if select else state["stage"])
            if self.select_of(state, stage_id):
                # A pass is redone only before its output is accepted; accepted passes are final.
                if not current or current["stage"] != stage_id:
                    raise ValueError("Only the pass in progress can be restarted; accepted passes are final.")
                reset = [stage_id]
            elif stage_id not in ids:
                raise ValueError(f"Unknown stage: {stage_id}")
            elif ids.index(stage_id) > position:
                raise ValueError("Only the current stage or an earlier one can be restarted.")
            else:
                reset = ids[ids.index(stage_id):]
                selects = [s for s in reset if self.stage_def(state, s)["kind"] == "select"]
                if state.get("passes") and any(s != stage_id for s in selects):
                    raise ValueError("Passes have already run after this stage; restart the workflow to start over.")
                if current and selects:
                    raise ValueError(f"Restart the pass in progress ({current['stage']}) instead.")
            restore = self.restart_restore(state, reset)
            number = len([r for r in state["restarts"] if r.get("kind") == "stage"]) + 1
            archive = self._new_archive(f"restart-{number}")
            for stage in reset:
                for relative in self.stage_def(state, stage).get("owns", []):
                    self._archive(self.format_path(state, relative), archive)
            # Receipts of an earlier pass of the same stage belong to that accepted pass and stay valid.
            scope = f"{stage_id}/{current['epoch']}/" if current and reset == [stage_id] else None
            superseded = [r["id"] for r in state["receipts"] if r["gate"].get("stage") in reset
                          and (scope is None or (r["gate"].get("instance") or "").startswith(scope))]
            for stage in reset:
                self.reset_stage(state, self.stage_def(state, stage))
                state["stage_epochs"][stage] = state["stage_epochs"].get(stage, 1) + 1
            if scope:
                current.update(epoch=state["stage_epochs"][stage_id], completed_at=None, result=None,
                               restarts=current["restarts"] + 1)
            state.pop("acceptance_id", None)
            state.update(next_input=None, error=None)
            self._restore(state, restore, archive)
            state["restarts"].append({
                "id": str(uuid.uuid4()), "kind": "stage", "stage": stage_id, "reason": reason, "created_at": now(),
                "archive": archive.relative_to(self.root).as_posix(), "superseded_receipt_ids": superseded,
            })
            self._enter_stage(state, stage_id)
            self.store.save(revision, state, "stage.restarted", {"stage": stage_id, "reason": reason})
            return state

    # ----- presentation ---------------------------------------------------------------------

    def summary(self, state):
        iteration = self.current_iteration(state) if self._stage_or_empty(state).get("iterate") else None
        result = {key: state.get(key) for key in (
            "id", "template_id", "workflow", "work_id", "owner", "status", "stage", "attempts", "error",
            "export_path", "document_path", "manuscript_language", "restart_of", "superseded_by", "settings",
            "handed_off_work", "execution")}
        result["chapter_id"] = iteration["chapter_id"] if iteration else None
        result["requires_runtime"] = self._stage_or_empty(state).get("kind") == "agent"
        result["production"] = self.production_view(state) if hasattr(self, "production_view") else None
        iterations = state.get("iterations") or []
        whole = next((item for item in iterations if item["chapter_id"] == "_whole"), None)
        result["whole_book_status"] = whole["status"] if whole else None
        iterations = [item for item in iterations if item["chapter_id"] != "_whole"]
        result["progress"] = {"completed": sum(item["status"] == "completed" for item in iterations),
                              "total": len(iterations)} if iterations else None
        result["passes"] = [{"number": p["number"], "stage": p["stage"], "completed": bool(p["completed_at"]),
                             "accepted": bool(p["accepted"])} for p in state.get("passes") or []]
        result["finalized"] = self.finalized(state)
        result["retired"] = self.retired
        result["engine_current"] = not self.engine_outdated(state)
        if state.get("gate"):
            result["gate_id"] = state["gate"]["id"]
            result["gate_kind"] = state["gate"]["kind"]
            result["gate_chapter_id"] = state["gate"].get("chapter_id")
            # Reviews present something to read and approve (metadata, documents); other gates ask for decisions.
            result["gate_review"] = state["gate"]["kind"] == "metadata_review" or bool(state["gate"].get("documents"))
            if state["gate"]["kind"] == "metadata_review":
                result["metadata_record_revision"] = state["gate"]["record_revision"]
        if state.get("acceptance_id") and state["status"] == "WAITING_FOR_ACCEPTANCE" and result["engine_current"]:
            result["acceptance_id"] = state["acceptance_id"]
            result["acceptance_title"] = self.acceptance_details(state)["title"]
        return result

    def available_actions(self, state):
        status, finalized = state["status"], self.finalized(state)
        terminal = status in TERMINAL
        outdated = not terminal and self.engine_outdated(state)
        iterating = any(stage.get("iteration", {}).get("restartable")
                        for stage in state["definition"]["stages"])
        locked_reason = ("run_cancelled: This run was stopped." if status == "CANCELLED" else
                         "run_finalized: This run is finalized; changes require adding the manuscript "
                         "again as a new work." if finalized else
                         "engine_updated: Restart the workflow to continue with the updated engine." if outdated else None)
        actions = []

        def add(name, enabled, reason=None, *, irreversible=False, confirmation=None):
            actions.append({"action": name, "enabled": bool(enabled), "reason": None if enabled else reason,
                            "irreversible": irreversible, "confirmation": confirmation})

        mutable = not (terminal or finalized or outdated)
        add("step", status == "READY" and (mutable or (finalized and not terminal)),
            locked_reason or f"Run is {status}.")
        add("reply", status == "WAITING_FOR_HUMAN" and mutable, locked_reason or "No gate is waiting.")
        add("edit_metadata", mutable and status != "RUNNING" and bool(state.get("prepared")),
            locked_reason or ("An agent turn is running." if status == "RUNNING" else
                              "Metadata is available after preparation."))
        acceptance = self.acceptance_details(state)
        add("accept", status == "WAITING_FOR_ACCEPTANCE" and mutable, locked_reason or "Nothing awaits acceptance.",
            irreversible=acceptance["finalizes"], confirmation=acceptance["notice"])
        retry_ok = status in ("FAILED", "BLOCKED", "PAUSED", "RUNNING") and (
            mutable or (finalized and not terminal and self._stage_or_empty(state).get("kind") == "export"))
        add("retry", retry_ok, locked_reason or "The run does not need a retry.",
            confirmation="Confirm the previous agent process has stopped." if status == "RUNNING" else None)
        restart_ok = mutable and status != "RUNNING"
        add("restart_chapter", restart_ok and iterating and bool(state.get("iterations")),
            locked_reason or ("An agent turn is running." if status == "RUNNING" else
                              "No restartable chapters are available."),
            confirmation="The chapter's work is archived and translated again.")
        add("restart_stage", restart_ok, locked_reason or "An agent turn is running.",
            confirmation="The stage's workspace is archived and its state reset.")
        add("restart_workflow", not terminal and not finalized and status != "RUNNING",
            locked_reason if (terminal or finalized) else "An agent turn is running.",
            confirmation="The current run is stopped and a new run of this workflow starts on the same work.")
        add("stop", not terminal and not finalized and status != "RUNNING",
            locked_reason if terminal or finalized else "An agent turn is running.",
            irreversible=True, confirmation="Stopping cancels the run permanently; its artifacts and history are kept.")
        return actions


class ArchivedEngine(Engine):
    """Read historical snapshots without retaining removed workflow executors."""

    retired = True

    def _guard(self, state, operation):
        raise WorkflowError("workflow_removed", "This workflow was removed. Its history and artifacts are read-only. "
                            "Start a supported workflow to continue.")

    def _stage_or_empty(self, state):
        return next((s for s in state.get("definition", {}).get("stages", [])
                     if s["id"] == state.get("stage")), {})

    @staticmethod
    def stage_ids(state):
        return [s["id"] for s in state.get("definition", {}).get("stages", [])]

    def summary(self, state):
        result = super().summary(state)
        result.update(recorded_status=state["status"], status="RETIRED", engine_current=False)
        return result

    def available_actions(self, state):
        return []
