"""One service API for the CLI and the web application: works, runs, the index, and the work library."""

from __future__ import annotations

import contextlib
import getpass
import json
import re
import sqlite3
import uuid
from pathlib import Path

from . import registry
from .engine import LANGUAGE_TAG, SKILLS, TERMINAL, Engine, WorkflowError, engine_for_state, module_at
from .library import WorkLibrary
from .prepared import METADATA_CONFIRMATION, load_metadata_helper
from .storage import Store, digest, json_bytes, now, plain, read_bytes

SCHEMA = """
CREATE TABLE IF NOT EXISTS works (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, owner TEXT NOT NULL, source_sha256 TEXT NOT NULL,
    source_name TEXT NOT NULL, manuscript_language TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS work_workflows (
    work_id TEXT NOT NULL REFERENCES works(id), workflow TEXT NOT NULL, status TEXT NOT NULL,
    finalized_run_id TEXT, PRIMARY KEY (work_id, workflow));
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY, template_id TEXT NOT NULL, workflow TEXT NOT NULL,
    work_id TEXT NOT NULL REFERENCES works(id), owner TEXT NOT NULL, restart_of TEXT, path TEXT NOT NULL,
    status TEXT NOT NULL, stage TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
"""


def default_owner():
    try:
        return getpass.getuser() or "local"
    except (OSError, KeyError, ImportError):
        return "local"


def slug(name):
    value = re.sub(r"[^a-z0-9]+", "-", Path(name).stem.lower()).strip("-")[:40].strip("-")
    return value or "work"


class WorkflowService:
    def __init__(self, server_root, *, owner=None):
        self.root = plain(Path(server_root))
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "works").mkdir(exist_ok=True)
        (self.root / "runs").mkdir(exist_ok=True)
        self.owner = owner or default_owner()
        self.db = sqlite3.connect(self.root / "index.sqlite3", timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @contextlib.contextmanager
    def _transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        self.db.execute("COMMIT")

    # ----- templates and works --------------------------------------------------------------

    def list_templates(self):
        return [{"id": t["id"], "title": t["title"], "workflow": t["workflow"], "consumes": t.get("consumes"),
                 "produces": t.get("produces"), "stages": [s["id"] for s in t["stages"]],
                 "optional_stages": [s["id"] for s in t["stages"] if s.get("optional")]}
                for t in registry.templates().values()]

    def _work_row(self, work_id):
        row = self.db.execute("SELECT * FROM works WHERE id=?", (work_id,)).fetchone()
        if row is None:
            raise ValueError(f"Unknown work: {work_id}")
        return dict(row)

    def library(self, work_id):
        self._work_row(work_id)
        return WorkLibrary(self.root / "works" / work_id)

    def list_works(self, owner=None):
        rows = self.db.execute("SELECT * FROM works WHERE ?1 IS NULL OR owner=?1 ORDER BY created_at", (owner,))
        return [dict(row) for row in rows]

    def get_work(self, work_id):
        work = self._work_row(work_id)
        library = self.library(work_id)
        workflows = {row["workflow"]: {"status": row["status"], "finalized_run_id": row["finalized_run_id"]}
                     for row in self.db.execute("SELECT * FROM work_workflows WHERE work_id=?", (work_id,))}
        for record in library.finalized():
            workflows[record["workflow"]] = {"status": "read_only", "finalized_run_id": record["run_id"]}
        work.update(workflows=workflows, runs=self.list_runs(work_id=work_id),
                    unfinished_run=self._unfinished(work_id),
                    heads={artifact: {key: record.get(key) for key in (
                        "id", "version", "sha256", "status", "review_status", "created_at", "run_id", "contract")}
                        for artifact, record in library.heads().items()})
        return work

    def work_publications(self, work_id, artifact=None):
        return self.library(work_id).publications(artifact)

    def verify_work(self, work_id):
        return self.library(work_id).detect_edits()

    def _create_work(self, upload, manuscript_language, owner):
        upload = plain(Path(upload))
        if not upload.is_file():
            raise ValueError("Designate one regular source file.")
        if not isinstance(manuscript_language, str) or not LANGUAGE_TAG.fullmatch(manuscript_language):
            raise ValueError("Use a manuscript-language tag such as zh or zh-CN.")
        # Every upload is a new work, even for an identical file.
        work_id = f"{slug(upload.name)}-{uuid.uuid4().hex[:6]}"
        info = {"work_id": work_id, "title": Path(upload.name).stem, "owner": owner,
                "manuscript_language": manuscript_language, "source_name": upload.name, "created_at": now()}
        library = WorkLibrary.create(self.root / "works" / work_id, source=upload, source_name=upload.name, info=info)
        _, record = library.source()
        self.db.execute("INSERT INTO works VALUES (?,?,?,?,?,?,?)",
                        (work_id, info["title"], owner, record["sha256"], upload.name, manuscript_language,
                         info["created_at"]))
        return work_id

    # ----- index ----------------------------------------------------------------------------

    def _run_row(self, run_id):
        row = self.db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise ValueError(f"Unknown run: {run_id}")
        return dict(row)

    def _insert_run(self, state, path, restart_of=None):
        self.db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            state["id"], state["template_id"], state["workflow"], state["work_id"], state.get("owner") or self.owner,
            restart_of, str(path), state["status"], state["stage"], state["created_at"], now()))

    def _record_state(self, run_id, state):
        self.db.execute("UPDATE runs SET status=?, stage=?, updated_at=? WHERE id=?",
                        (state["status"], state["stage"], now(), run_id))
        if state.get("acceptance"):
            row = self._run_row(run_id)
            self.db.execute("INSERT INTO work_workflows VALUES (?,?,?,?) ON CONFLICT(work_id, workflow) "
                            "DO UPDATE SET status=excluded.status, finalized_run_id=excluded.finalized_run_id",
                            (row["work_id"], row["workflow"], "read_only", run_id))

    def _load_state(self, path):
        store = Store(Path(path))
        try:
            return store.load()[1]
        finally:
            store.close()

    def _unfinished(self, work_id):
        for row in self.db.execute("SELECT id, path FROM runs WHERE work_id=? AND status NOT IN ('COMPLETED', 'CANCELLED')",
                                   (work_id,)).fetchall():
            state = self._load_state(row["path"])  # Per-run state is authoritative; the index is a cache.
            self._record_state(row["id"], state)
            if state["status"] not in TERMINAL:
                return row["id"]
        return None

    def _check_can_start(self, work_id, workflow):
        active = self._unfinished(work_id)
        if active:
            raise WorkflowError("work_busy", f"Run {active} is unfinished on this work; finish or stop it first.")
        row = self.db.execute("SELECT status FROM work_workflows WHERE work_id=? AND workflow=?",
                              (work_id, workflow)).fetchone()
        if (row and row["status"] == "read_only") or self.library(work_id).finalized(workflow):
            raise WorkflowError("workflow_read_only", f"{workflow} is finalized on this work; changes require "
                                                      "adding the manuscript again as a new work.")

    @contextlib.contextmanager
    def open_run(self, run_id):
        row = self._run_row(run_id)
        library_root = self.root / "works" / row["work_id"]
        library = WorkLibrary(library_root) if (library_root / "publications.jsonl").is_file() else None
        engine = Engine.open(Path(row["path"]), library=library)
        try:
            yield engine
        finally:
            try:
                self._record_state(run_id, engine.state())
            finally:
                engine.close()

    def list_runs(self, owner=None, work_id=None):
        rows = self.db.execute("SELECT * FROM runs WHERE (?1 IS NULL OR owner=?1) AND (?2 IS NULL OR work_id=?2) "
                               "ORDER BY created_at", (owner, work_id)).fetchall()
        return [dict(row) for row in rows]

    def reindex(self):
        """Rebuild the cache from work libraries and per-run state."""
        with self._transaction():
            for path in sorted((self.root / "works").glob("*/library.json")):
                library = WorkLibrary(path.parent)
                info, (_, source) = library.info(), library.source()
                self.db.execute("INSERT OR IGNORE INTO works VALUES (?,?,?,?,?,?,?)", (
                    info["work_id"], info["title"], info["owner"], source["sha256"], info["source_name"],
                    info["manuscript_language"], info["created_at"]))
            known = {row["id"]: row["path"] for row in self.db.execute("SELECT id, path FROM runs")}
            paths = {**{p.parent.name: str(p.parent) for p in (self.root / "runs").glob("*/state.sqlite3")}, **known}
            for run_id, path in paths.items():
                state = self._load_state(path)
                if run_id not in known:
                    self._insert_run(state, path)
                self._record_state(run_id, state)
        return self.list_runs()

    # ----- run creation ---------------------------------------------------------------------

    def create_run(self, template_id, *, upload=None, manuscript_language=None, work_id=None, owner=None,
                   model=None, agent_models=None, skip_stages=()):
        """Exactly one of: upload (+ manuscript_language) creates a new work; work_id uses an existing work."""
        template = registry.get(template_id)
        if "consumes" in template:
            raise ValueError("This is a derived template; use create_derived_run with a publication.")
        if (upload is None) == (work_id is None):
            raise ValueError("Provide exactly one of an uploaded source (new work) or an existing work ID.")
        owner = owner or self.owner
        with self._transaction():
            if upload is not None:
                if manuscript_language is None:
                    raise ValueError("A new work requires a manuscript language.")
                work_id = self._create_work(upload, manuscript_language, owner)
            else:
                if manuscript_language is not None:
                    raise ValueError("An existing work keeps its recorded manuscript language.")
                manuscript_language = self._work_row(work_id)["manuscript_language"]
                self._check_can_start(work_id, template["workflow"])
            return self._create(template, work_id, owner, manuscript_language, model, agent_models,
                                skip_stages=skip_stages)

    def _create(self, template, work_id, owner, manuscript_language, model, agent_models, restart_of=None,
                skip_stages=()):
        library = self.library(work_id)
        source, record = library.source()
        run_id = str(uuid.uuid4())
        root = self.root / "runs" / run_id
        engine = registry.engine_class(template["engine"]).create(
            root, template, source=source, manuscript_language=manuscript_language, work_id=work_id, owner=owner,
            source_name=record.get("source_name"), model=model, agent_models=agent_models, library=library,
            run_id=run_id, skip_stages=skip_stages,
        )
        try:
            self._insert_run(engine.state(), root, restart_of)
        finally:
            engine.close()
        return run_id

    def accepted_publications(self, work_id, contract=None):
        return [r for r in self.library(work_id).publications()
                if r.get("contract") and (contract is None or r["contract"] == contract)]

    def create_derived_run(self, work_id, template_id, *, publication_id=None, owner=None, options=None, model=None,
                           agent_models=None, new_edition=False, restart_of=None):
        template = registry.get(template_id)
        if "consumes" not in template:
            raise ValueError("This template is not derived; use create_run.")
        library = self.library(work_id)
        if publication_id is None:
            candidates = self.accepted_publications(work_id, template["consumes"])
            if not candidates:
                raise ValueError(f"This work has no {template['consumes']} publication to derive from.")
            publication_id = candidates[-1]["id"]
        publication = library.publication(publication_id)
        if publication.get("contract") != template["consumes"]:
            raise ValueError(f"Publication {publication_id} does not provide {template['consumes']}.")
        accepted = json.loads(library.read(publication))
        data = [library.read({"sha256": chapter["sha256"]}) for chapter in accepted["chapters"]]
        cls = registry.engine_class(template["engine"])
        resolved = cls.resolve_options(options)
        identity = cls.derived_identity(accepted, resolved, model)
        owner = owner or self.owner
        with self._transaction():
            if not new_edition and restart_of is None:
                for row in self.db.execute("SELECT id, path FROM runs WHERE work_id=? AND template_id=? "
                                           "AND status != 'CANCELLED'", (work_id, template_id)).fetchall():
                    if self._load_state(row["path"]).get("edition") == identity:
                        return row["id"]  # An unchanged request reuses its edition.
            if restart_of is None:
                self._check_can_start(work_id, template["workflow"])
            run_id = str(uuid.uuid4())
            root = self.root / "runs" / run_id
            engine = cls.create_derived(root, template, accepted=accepted, chapter_data=data, work_id=work_id,
                                        owner=owner, publication_id=publication_id, options=resolved, model=model,
                                        agent_models=agent_models, library=library, run_id=run_id)
            try:
                self._insert_run(engine.state(), root, restart_of)
            finally:
                engine.close()
            return run_id

    # ----- run operations -------------------------------------------------------------------

    def get_run(self, run_id):
        row = self._run_row(run_id)
        with self.open_run(run_id) as engine:
            state = engine.state()
            result = engine.summary(state)
            result.update(restart_of=row["restart_of"], path=row["path"],
                          available_actions=engine.available_actions(state))
            if state.get("gate"):
                result["gate"] = {key: state["gate"].get(key) for key in
                                  ("id", "kind", "message", "stage", "chapter_id", "record_revision")}
            return result

    def step(self, run_id, runtime):
        with self.open_run(run_id) as engine:
            return engine.summary(engine.advance(runtime))

    def reply(self, run_id, gate_id, text, *, decision_source="human"):
        with self.open_run(run_id) as engine:
            return engine.summary(engine.reply(gate_id, text, decision_source=decision_source))

    def accept(self, run_id, acceptance_id, *, confirm_final=False, decision_source="human"):
        with self.open_run(run_id) as engine:
            return engine.summary(engine.accept(acceptance_id, confirm_final=confirm_final,
                                                decision_source=decision_source))

    def retry(self, run_id, *, confirm_stopped=False, refresh_gate=False):
        with self.open_run(run_id) as engine:
            return engine.summary(engine.retry(confirm_stopped=confirm_stopped, refresh_gate=refresh_gate))

    def restart_stage(self, run_id, stage, *, reason):
        with self.open_run(run_id) as engine:
            return engine.summary(engine.restart_stage(stage, reason=reason))

    def restart_chapter(self, run_id, chapter_id, *, reason):
        with self.open_run(run_id) as engine:
            if not hasattr(engine, "restart_chapter"):
                raise ValueError("This workflow has no restartable chapters.")
            return engine.summary(engine.restart_chapter(chapter_id, reason=reason))

    def stop(self, run_id):
        with self.open_run(run_id) as engine:
            return engine.summary(engine.cancel())

    def events(self, run_id, after=0):
        with self.open_run(run_id) as engine:
            return engine.events(after)

    def restart_workflow(self, run_id, *, reason, owner=None):
        """Stop an unfinished run and start the same template on the same work with the current engine."""
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("A restart reason is required.")
        row = self._run_row(run_id)
        with self.open_run(run_id) as engine:
            state = engine.state()
            if engine.finalized(state) or state["status"] == "COMPLETED":
                raise WorkflowError("run_finalized", "A finalized run cannot be restarted; changes require "
                                                     "adding the manuscript again as a new work.")
            if state["status"] == "CANCELLED":
                raise WorkflowError("run_cancelled", "This run was already stopped.")
            if state["status"] == "RUNNING":
                raise ValueError("An agent turn is running; interrupt it first.")
            carry = engine.carry_forward(state)
            template_id = state.get("template_id") or state["definition"]["id"]
            agents = state["definition"].get("agents", {})
            template = registry.get(template_id)
            agent_models = {name: agents[name].get("model") for name in template["agents"]
                            if name in agents and agents[name].get("model")}
            owner = owner or state.get("owner") or self.owner
            if "consumes" in template:
                options = state.get("options") or {}
                engine.cancel(superseded_by="pending")
                new_id = self.create_derived_run(row["work_id"], template_id, publication_id=state["publication_id"],
                                                 owner=owner, options=options, agent_models=agent_models,
                                                 restart_of=run_id)
            else:
                # The old run is cancelled first, so the one-run-per-work rule does not block the restart.
                engine.cancel(superseded_by="pending")
                with self._transaction():
                    new_id = self._create(template, row["work_id"], owner, state["manuscript_language"], None,
                                          agent_models, restart_of=run_id,
                                          skip_stages=state.get("skipped_stages") or ())
        self._mark_superseded(row["path"], new_id, reason)
        if carry:
            with self.open_run(new_id) as new:
                new.seed_workspace(carry["files"], carry["origin"])
        return new_id

    def _mark_superseded(self, path, new_id, reason):
        store = Store(Path(path))
        try:
            with store.locked():
                revision, state = store.load()
                state["superseded_by"] = new_id
                store.save(revision, state, "workflow.restarted", {"new_run_id": new_id, "reason": reason})
        finally:
            store.close()

    # ----- metadata -------------------------------------------------------------------------

    def get_metadata(self, run_id):
        with self.open_run(run_id) as engine:
            return engine.metadata_view(engine.state())

    def edit_metadata(self, run_id, field, value, rationale="Explicit metadata edit.", *, gate_id=None, actor=None):
        with self.open_run(run_id) as engine:
            return engine.summary(engine.edit_metadata(field, value, reason=rationale, gate_id=gate_id,
                                                       actor=actor or self.owner))

    def confirm_metadata(self, run_id, gate_id, record_revision, *, decision_source="human"):
        with self.open_run(run_id) as engine:
            gate = engine.state().get("gate")
            if not gate or gate["kind"] != "metadata_review" or gate["id"] != gate_id:
                raise ValueError("Stale or unavailable metadata review gate.")
            if gate["record_revision"] != record_revision:
                raise ValueError("Stale metadata revision; review the current record before confirming.")
            return engine.summary(engine.reply(gate_id, METADATA_CONFIRMATION, decision_source=decision_source))

    def metadata_history(self, run_id):
        with self.open_run(run_id) as engine:
            return engine.metadata_history(engine.state())

    def metadata_version(self, run_id, record_revision):
        with self.open_run(run_id) as engine:
            return engine.metadata_version(engine.state(), record_revision)

    @staticmethod
    def _current_metadata_helper():
        contract = module_at(SKILLS / "prepare-manuscript/scripts/validate_preparation.py")
        return load_metadata_helper(SKILLS / "prepare-manuscript", contract), contract

    def get_work_metadata(self, work_id):
        head = self.library(work_id).head("work.json")
        if head is None:
            raise ValueError("This work has no confirmed metadata yet.")
        work = json.loads(self.library(work_id).read(head))
        return {"publication_id": head["id"], "record_revision": work["record_revision"],
                "schema_version": work["schema_version"], "metadata": work["metadata"],
                "provenance": work.get("metadata_provenance", {}), "review_status": head.get("review_status")}

    def edit_work_metadata(self, work_id, field, value, rationale="Explicit metadata edit.", *, actor=None):
        """Edit shared metadata while no run is unfinished on the work; recorded as a library publication."""
        if field == "/manuscript_language":
            raise ValueError("/manuscript_language is fixed for a work; add the manuscript again as a new work.")
        helper, contract = self._current_metadata_helper()
        library = self.library(work_id)
        with self._transaction():
            active = self._unfinished(work_id)
            if active:
                raise WorkflowError("work_busy", f"Run {active} is unfinished; edit metadata through that run.")
            head = library.head("work.json")
            if head is None:
                raise ValueError("This work has no confirmed metadata yet; confirm it in a run first.")
            work = helper.migrate(json.loads(library.read(head)))
            helper.put(work["metadata"], field, value)
            helper.record(work, field, "user_edit", actor=actor or self.owner, rationale=rationale, review="confirmed")
            work["record_revision"] += 1
            work["updated_at"] = now()
            contract.schema_check(contract.validators()[0], work, "work")
            [publication] = library.publish_many(
                [{"artifact": "work.json", "data": json_bytes(work), "expected_head": head["id"],
                  "basis": {"metadata_record_revision": work["record_revision"]}}],
                run_id=None, workflow=None, stage="work_metadata_edit")
            return {"publication_id": publication["id"], "record_revision": work["record_revision"]}

    def work_metadata_history(self, work_id):
        library = self.library(work_id)
        result = []
        for record in library.publications("work.json"):
            work = json.loads(library.read(record))
            result.append({"publication_id": record["id"], "record_revision": work["record_revision"],
                           "created_at": record["created_at"], "run_id": record["run_id"], "stage": record["stage"],
                           "status": record["status"], "review_status": record.get("review_status")})
        return result

    def work_metadata_version(self, work_id, record_revision):
        library = self.library(work_id)
        for record in reversed(library.publications("work.json")):
            work = json.loads(library.read(record))
            if work["record_revision"] == record_revision:
                return work
        raise ValueError(f"No published metadata version {record_revision}.")

    # ----- import ---------------------------------------------------------------------------

    def import_run(self, path, *, owner=None):
        """Register an existing run directory; completed translations publish their accepted output."""
        path = plain(Path(path))
        state = self._load_state(path)
        if state.get("kind") == "manuscript-formatting":
            raise ValueError("Import translation runs; their nested formatting jobs stay readable on disk.")
        if self.db.execute("SELECT 1 FROM runs WHERE id=?", (state["id"],)).fetchone():
            raise ValueError(f"Run {state['id']} is already registered.")
        template_id = state.get("template_id") or state["definition"]["id"]
        template = registry.get(template_id)
        source = path / "input" / state["source_name"]
        if digest(read_bytes(plain(source))) != state["source_hash"]:
            raise ValueError("The run's input snapshot changed; it cannot be imported.")
        owner = owner or state.get("owner") or self.owner
        with self._transaction():
            work_id = self._create_work(source, state["manuscript_language"], owner)
            state.update(work_id=work_id, template_id=template_id, workflow=template["workflow"])
            self._insert_run(state, path)
            if state["status"] == "COMPLETED" and state.get("acceptance"):
                self._publish_imported(path, state, template)
            self.db.execute("UPDATE runs SET status=?, stage=? WHERE id=?", (state["status"], state["stage"], state["id"]))
        return state["id"]

    def _publish_imported(self, path, state, template):
        library = self.library(state["work_id"])
        engine = engine_for_state(state)(path)
        try:
            state.setdefault("target_language", template.get("target_language"))
            state["definition"] = {**state["definition"], "produces": template["produces"]}
            accepted = {**engine.accepted_output(state), "imported": True}
            entries = [{"artifact": c["artifact"], "data": engine.store.content(c), "expected_head": None}
                       for c in accepted["chapters"]]
            entries += [{"artifact": item["artifact"], "data": engine.store.content(item), "expected_head": None}
                        for item in accepted["continuity"].values()]
            entries.append({"artifact": f"accepted/{template['workflow']}.json", "data": json_bytes(accepted),
                            "expected_head": None, "contract": accepted["contract"]})
            if state.get("prepared"):
                work = json.loads(engine.file(state["prepared"]["work_record"]).read_text(encoding="utf-8"))
                work["work_id"] = state["work_id"]
                entries.append({"artifact": "work.json", "data": json_bytes(work), "expected_head": None})
            areas = [area.format(target=state["target_language"]) for area in template["library"]["areas"]]
            library.publish_many(entries, run_id=state["id"], workflow=template["workflow"], stage="import",
                                 receipts=[state["acceptance"]["id"]], finalize=areas)
        finally:
            engine.close()
        self.db.execute("INSERT INTO work_workflows VALUES (?,?,?,?) ON CONFLICT(work_id, workflow) DO UPDATE SET "
                        "status=excluded.status, finalized_run_id=excluded.finalized_run_id",
                        (state["work_id"], template["workflow"], "read_only", state["id"]))
