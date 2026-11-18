"""One service API for the CLI and the web application: works, runs, the index, and the work library."""

from __future__ import annotations

import contextlib
import getpass
import json
import re
import sqlite3
import tempfile
import uuid
from pathlib import Path

from . import registry
from .engine import LANGUAGE_TAG, SKILLS, TERMINAL, Engine, WorkflowError, module_at
from .library import WorkLibrary
from .prepared import METADATA_CONFIRMATION, load_metadata_helper
from .storage import Store, json_bytes, now, plain
from .usage import run_usage

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
    def __init__(self, server_root, *, owner=None, execution_profile=None):
        self.root = plain(Path(server_root))
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "works").mkdir(exist_ok=True)
        (self.root / "runs").mkdir(exist_ok=True)
        self.owner = owner or default_owner()
        self.execution_profile = execution_profile
        self.db = sqlite3.connect(self.root / "index.sqlite3", timeout=10, isolation_level=None,
                                  check_same_thread=False)  # One service per request, used sequentially across web threads.
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
                 "choices": {s["id"]: s["options"] for s in t["stages"] if s["kind"] == "select"},
                 "passage_size": t.get("passage_size")}
                for t in registry.templates().values()]

    def _work_row(self, work_id):
        row = self.db.execute("SELECT * FROM works WHERE id=?", (work_id,)).fetchone()
        if row is None:
            raise ValueError(f"Unknown work: {work_id}")
        result = dict(row)
        if result["manuscript_language"] == "und":
            result["manuscript_language"] = None
        library = WorkLibrary(self.root / "works" / work_id)
        head = library.head("work.json")
        if head:
            metadata = json.loads(library.read(head)).get("metadata", {})
            # The intake filename is only a display fallback, not another metadata authority.
            result["title"] = metadata.get("title") or result["title"]
            result["manuscript_language"] = metadata.get("manuscript_language") or result["manuscript_language"]
        return result

    def library(self, work_id):
        self._work_row(work_id)
        return WorkLibrary(self.root / "works" / work_id)

    def list_works(self, owner=None):
        rows = self.db.execute("SELECT * FROM works WHERE ?1 IS NULL OR owner=?1 ORDER BY created_at", (owner,))
        return [self._work_row(row["id"]) for row in rows]

    def get_work(self, work_id):
        work = self._work_row(work_id)
        library = self.library(work_id)
        workflows = {row["workflow"]: {"status": row["status"], "finalized_run_id": row["finalized_run_id"]}
                     for row in self.db.execute("SELECT * FROM work_workflows WHERE work_id=?", (work_id,))}
        for record in library.finalized():  # The latest accepted version of each workflow.
            workflows[record["workflow"]] = {"status": "completed", "finalized_run_id": record["run_id"],
                                             "version": next((a.split("/")[1] for a in record["areas"]), None)}
        info = library.info()
        work["origin"] = info.get("origin")
        work["handed_off"] = [{**self.library(row["id"]).info()["origin"], "work_id": row["id"], "title": row["title"]}
                              for row in self.list_works()
                              if (self.library(row["id"]).info().get("origin") or {}).get("work_id") == work_id]
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

    def create_work(self, upload, manuscript_language=None, *, owner=None):
        """Intake without a run: store the upload in a new work's library (always a new work)."""
        with self._transaction():
            return self._create_work(upload, manuscript_language, owner or self.owner)

    def _create_work(self, upload, manuscript_language, owner, *, origin=None, carried=None):
        upload = plain(Path(upload))
        if not upload.is_file():
            raise ValueError("Designate one regular source file.")
        manuscript_language = None if manuscript_language in ("", "und") else manuscript_language
        if manuscript_language is not None and (
                not isinstance(manuscript_language, str) or not LANGUAGE_TAG.fullmatch(manuscript_language)):
            raise ValueError("Use a manuscript-language tag such as zh or zh-CN.")
        # Every upload is a new work, even for an identical file.
        work_id = f"{slug(upload.name)}-{uuid.uuid4().hex[:6]}"
        info = {"work_id": work_id, "title": Path(upload.name).stem, "owner": owner,
                "manuscript_language": manuscript_language, "source_name": upload.name, "created_at": now()}
        if origin:
            info["origin"] = origin  # The work and run whose output this work was created from.
        library = WorkLibrary.create(self.root / "works" / work_id, source=upload, source_name=upload.name, info=info)
        _, record = library.source()
        # User-provided fields start empty so the user can fill them in right after intake.
        helper, contract = self._current_metadata_helper()
        work = helper.blank(work_id, manuscript_language, location=upload.name, actor=owner or "user")
        for field, (value, rationale) in (carried or {}).items():
            helper.put(work["metadata"], field, value)
            helper.record(work, field, "provided", actor=owner or "user", rationale=rationale)
        contract.schema_check(contract.validators()[0], work, "work")
        library.publish_many([{"artifact": "work.json", "data": json_bytes(work), "expected_head": None,
                               "review_status": "unreviewed", "basis": {"metadata_record_revision": 1}}],
                             run_id=None, workflow=None, stage="create")
        # The index uses BCP-47 "und" for an as-yet undetermined language; metadata/API use null.
        self.db.execute("INSERT INTO works VALUES (?,?,?,?,?,?,?)",
                        (work_id, info["title"], owner, record["sha256"], upload.name, manuscript_language or "und",
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
        if state.get("prepared") and state.get("manuscript_language"):
            self.db.execute("UPDATE works SET manuscript_language=? WHERE id=?",
                            (state["manuscript_language"], state["work_id"]))
        if state.get("acceptance"):
            row = self._run_row(run_id)
            self.db.execute("INSERT INTO work_workflows VALUES (?,?,?,?) ON CONFLICT(work_id, workflow) "
                            "DO UPDATE SET status=excluded.status, finalized_run_id=excluded.finalized_run_id",
                            (row["work_id"], row["workflow"], "completed", run_id))

    def _load_state(self, path):
        store = Store(Path(path))
        try:
            return store.load()[1]
        finally:
            store.close()

    def _unfinished(self, work_id):
        supported = registry.templates()
        for row in self.db.execute("SELECT id, path FROM runs WHERE work_id=? AND status NOT IN ('COMPLETED', 'CANCELLED')",
                                   (work_id,)).fetchall():
            state = self._load_state(row["path"])  # Per-run state is authoritative; the index is a cache.
            self._record_state(row["id"], state)
            if state["status"] not in TERMINAL and state.get("template_id") in supported:
                return row["id"]
        return None

    def _check_can_start(self, work_id, workflow):
        active = self._unfinished(work_id)
        if active:
            raise WorkflowError("work_busy", f"Run {active} is unfinished on this work; finish or stop it first.")

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
                    info["manuscript_language"] or "und", info["created_at"]))
            known = {row["id"]: row["path"] for row in self.db.execute("SELECT id, path FROM runs")}
            paths = {**{p.parent.name: str(p.parent) for p in (self.root / "runs").glob("*/state.sqlite3")}, **known}
            for run_id, path in paths.items():
                state = self._load_state(path)
                if run_id not in known:
                    self._insert_run(state, path)
                self._record_state(run_id, state)
        return self.list_runs()

    # ----- run creation ---------------------------------------------------------------------

    def _resolve_models(self, template, model, agent_models):
        if self.execution_profile:
            model = self.execution_profile.select(model, template["workflow"]).key
            for choice in (agent_models or {}).values():
                self.execution_profile.select(choice, template["workflow"])
        return model

    def create_run(self, template_id, *, upload=None, manuscript_language=None, work_id=None, owner=None,
                   model=None, agent_models=None, settings=None):
        """An upload creates a new work with an optional language hint; work_id uses an existing work."""
        template = registry.get(template_id)
        model = self._resolve_models(template, model, agent_models)
        if "consumes" in template:
            raise ValueError("This is a derived template; use create_derived_run with a publication.")
        if (upload is None) == (work_id is None):
            raise ValueError("Provide exactly one of an uploaded source (new work) or an existing work ID.")
        owner = owner or self.owner
        with self._transaction():
            if upload is not None:
                work_id = self._create_work(upload, manuscript_language, owner)
            else:
                if manuscript_language is not None:
                    raise ValueError("An existing work keeps its recorded manuscript language.")
                manuscript_language = self._work_row(work_id)["manuscript_language"]
                self._check_can_start(work_id, template["workflow"])
            return self._create(template, work_id, owner, manuscript_language, model, agent_models,
                                settings=settings)

    def _create(self, template, work_id, owner, manuscript_language, model, agent_models, restart_of=None,
                settings=None):
        model = self._resolve_models(template, model, agent_models)
        library = self.library(work_id)
        source, record = library.source()
        run_id = str(uuid.uuid4())
        root = self.root / "runs" / run_id
        engine = registry.engine_class(template["engine"]).create(
            root, template, source=source, manuscript_language=manuscript_language, work_id=work_id, owner=owner,
            source_name=record.get("source_name"), model=model, agent_models=agent_models, library=library,
            run_id=run_id, settings=settings,
        )
        try:
            if self.execution_profile:
                revision, state = engine.store.load()
                state["execution"] = self.execution_profile.describe(model)
                engine.store.save(revision, state, "execution.selected", state["execution"])
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
        model = self._resolve_models(template, model, agent_models)
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

    def get_run(self, run_id, *, include_usage=True):
        with self.open_run(run_id) as engine:
            return self.run_view(engine, engine.state(), include_usage=include_usage)

    def run_view(self, engine, state, *, include_usage=True):
        """Describe one state snapshot; callers may enrich it without re-reading a moving run."""
        row = self._run_row(state["id"])
        result = engine.summary(state)
        result.update(restart_of=row["restart_of"], path=row["path"],
                      available_actions=engine.available_actions(state))
        if include_usage:
            result["usage"] = run_usage(engine.store)
        if state.get("gate") and not engine.retired:
            result["gate"] = {key: state["gate"].get(key) for key in
                              ("id", "kind", "message", "stage", "chapter_id", "record_revision", "options", "pass")}
        return result

    def step(self, run_id, runtime):
        with self.open_run(run_id) as engine:
            summary = engine.summary(engine.advance(runtime))
        if summary["status"] == "COMPLETED" and registry.get(summary["template_id"]).get("hands_off"):
            self.hand_off(run_id)
            with self.open_run(run_id) as engine:
                summary = engine.summary(engine.state())
        return summary

    # A handed-off work is a new edition in another language, so its metadata is derived, not copied:
    # language-neutral facts carry over; the title comes from the translated front matter; free-text fields
    # in the original's language (subtitle, genres, keywords, description, series name, edition label) start
    # empty, so the new work's own preparation infers them in its language and the user reviews them.
    NEUTRAL_FIELDS = ("/work_type", "/form", "/audience", "/series/position", "/series/relationship")

    def _translated_title(self, library, publication_id):
        """The title in the output language, from the accepted version's translated front matter."""
        try:
            manifest = json.loads(library.read(library.publication(publication_id)))
            front = next(c for c in sorted(manifest["chapters"], key=lambda c: c["order"]))
            text = library.read(library.head(front["artifact"])).decode("utf-8")
        except (ValueError, KeyError, StopIteration, TypeError):
            return None
        # The front matter opens with the title: its first heading, else its first line.
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        heading = next((line for line in lines if re.match(r"^#{1,6}\s+\S", line)), lines[0] if lines else None)
        return re.sub(r"^#{1,6}\s+", "", heading).strip() if heading else None

    def _derived_metadata(self, row, state, metadata, language):
        helper, _ = self._current_metadata_helper()
        source = f"work {row['work_id']}, {state['source_version']}"
        carried = {field: (helper.field_value(metadata, field), f"Language-neutral; carried over from {source}.")
                   for field in self.NEUTRAL_FIELDS if not helper.missing(helper.field_value(metadata, field))}
        if metadata.get("contributors"):
            # Names stay as recorded in the original; their form in the new language is for the user to review.
            carried["/contributors"] = (metadata["contributors"], f"Carried over from {source}; review how the "
                                        "names should appear in this edition.")
        title = self._translated_title(self.library(row["work_id"]), state.get("publication_id"))
        if title:
            carried["/title"] = (title, f"First heading of the translated front matter of {source}.")
        original = metadata.get("original_language") or self._work_row(row["work_id"])["manuscript_language"]
        if original and original.split("-")[0] != language.split("-")[0]:
            carried["/original_language"] = (original, f"The language of {source}.")
        return carried, title

    def hand_off(self, run_id):
        """Create a new work from a completed run's document, with metadata derived from the original (idempotent)."""
        row = self._run_row(run_id)
        with self.open_run(run_id) as engine:
            state = engine.state()
            if engine.retired:
                engine._guard(state, "hand_off")
            if state.get("handed_off_work"):
                return state["handed_off_work"]
            if state["status"] != "COMPLETED" or not state.get("document_path"):
                raise ValueError("Only a completed run with a document can hand off its output.")
            document = Path(state["document_path"])
            language = state.get("manuscript_language") or row["manuscript_language"]
            source = self.library(row["work_id"])
            head = source.head("work.json")
            metadata = json.loads(source.read(head))["metadata"] if head else {}
            carried, title = self._derived_metadata(row, state, metadata, language)
            stem = re.sub(r'[\\/:*?"<>|]+', " ", title).strip() if title else \
                f"{Path(self._work_row(row['work_id'])['source_name']).stem}-{state['source_version']}"
            name = f"{stem}.docx"
            with tempfile.TemporaryDirectory() as folder:
                upload = Path(folder) / name
                upload.write_bytes(document.read_bytes())
                origin = {"work_id": row["work_id"], "workflow": row["workflow"], "run_id": run_id,
                          "source_version": state["source_version"], "publication_id": state.get("publication_id"),
                          "parent_run_id": state.get("parent_run_id")}
                with self._transaction():
                    work_id = self._create_work(upload, language, state.get("owner") or self.owner,
                                                origin=origin, carried=carried)
            engine.mark_handed_off(work_id)
            return work_id

    def reply(self, run_id, gate_id, text, *, decision_source="human"):
        with self.open_run(run_id) as engine:
            return engine.summary(engine.reply(gate_id, text, decision_source=decision_source))

    def review_interior_design(self, run_id, gate_id, expected_sha256, action, **fields):
        with self.open_run(run_id) as engine:
            if not hasattr(engine, "review_design"):
                raise ValueError("This workflow has no interior-design review phase.")
            return engine.summary(engine.review_design(gate_id, expected_sha256, action, **fields))

    def reopen_interior_design(self, run_id, acceptance_id, expected_docx_sha256):
        with self.open_run(run_id) as engine:
            if not hasattr(engine, "reopen_design"):
                raise ValueError("This workflow has no interior-design review phase.")
            return engine.summary(engine.reopen_design(acceptance_id, expected_docx_sha256))

    def docx_candidate(self, run_id, build_id):
        with self.open_run(run_id) as engine:
            state = engine.state()
            job = state.get("production")
            if state["status"] == "CANCELLED" or not job or job["id"] != build_id or not job.get("result"):
                raise ValueError("No current DOCX candidate with that build ID.")
            artifact = job["result"]["docx"]
            manifest = json.loads(engine.store.content(job["result"]["manifest"]))
            if manifest["docx"] != artifact or manifest["build_id"] != build_id:
                raise ValueError("The DOCX download does not match its build manifest.")
            return engine.store.content(artifact), artifact["sha256"]

    def accept(self, run_id, acceptance_id, *, confirm_final=False, decision_source="human", format_target=None):
        with self.open_run(run_id) as engine:
            return engine.summary(engine.accept(acceptance_id, confirm_final=confirm_final,
                                                decision_source=decision_source, format_target=format_target))

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

    def restart_workflow(self, run_id, *, reason, owner=None, confirm_stopped=False):
        """Stop an unfinished run and start the same template on the same work with the current engine."""
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("A restart reason is required.")
        row = self._run_row(run_id)
        with self.open_run(run_id) as engine:
            state = engine.state()
            if engine.retired:
                engine._guard(state, "restart")
            if engine.finalized(state) or state["status"] == "COMPLETED":
                raise WorkflowError("run_finalized", "A finalized run cannot be restarted; start a new run on "
                                                     "the work to publish a new version.")
            if state["status"] == "CANCELLED":
                raise WorkflowError("run_cancelled", "This run was already stopped.")
            if state["status"] == "RUNNING" and not confirm_stopped:
                # A server restart can strand a run as RUNNING; the user confirms no agent process remains.
                raise ValueError("An agent turn is running; interrupt it first, or confirm that no agent "
                                 "process remains.")
            carry = engine.carry_forward(state)
            template_id = state.get("template_id") or state["definition"]["id"]
            agents = state["definition"].get("agents", {})
            template = registry.get(template_id)
            agent_models = {name: agents[name].get("model") for name in template["agents"]
                            if name in agents and agents[name].get("model")}
            # Profile changes must be refused before the original run is irreversibly cancelled.
            model = self._resolve_models(template, None, agent_models)
            owner = owner or state.get("owner") or self.owner
            if "consumes" in template:
                options = state.get("options") or {}
                engine.cancel(superseded_by="pending", confirm_stopped=confirm_stopped)
                new_id = self.create_derived_run(row["work_id"], template_id, publication_id=state["publication_id"],
                                                 owner=owner, options=options, model=model, agent_models=agent_models,
                                                 restart_of=run_id)
            else:
                # The old run is cancelled first, so the one-run-per-work rule does not block the restart.
                engine.cancel(superseded_by="pending", confirm_stopped=confirm_stopped)
                with self._transaction():
                    new_id = self._create(template, row["work_id"], owner, state["manuscript_language"], model,
                                          agent_models, restart_of=run_id, settings=state.get("settings"))
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

    def metadata_editor_run(self, work_id):
        active = self._unfinished(work_id)
        if active:
            return active
        return next((row["id"] for row in reversed(self.list_runs(work_id=work_id))
                     if self._load_state(row["path"]).get("prepared")), None)

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

    def metadata_fields(self):
        """Every metadata field with its group, input kind, and allowed values, for clients to render."""
        helper, contract = self._current_metadata_helper()
        schema = contract.load_json(SKILLS / "prepare-manuscript/schemas/manuscript-metadata.schema.json")

        def spec(item):
            ref = item.get("$ref", "")
            return schema["$defs"][ref.rsplit("/", 1)[1]] if ref.startswith("#/$defs/") else item

        result = []
        for field in helper.FIELDS:
            parts = field.strip("/").split("/")
            item = schema["properties"][parts[0]]
            for part in parts[1:]:
                item = spec(item)["properties"][part]
            ref, item = item.get("$ref", ""), spec(item)
            kind = ("people" if field == "/contributors" else "extent" if field == "/extent" else "enum" if "enum" in item
                    else "list" if ref.endswith("/terms") else "language" if ref.endswith("/language")
                    else "number" if any(t in str(item.get("type")) for t in ("number", "integer")) else "text")
            group = "computed" if field in helper.COMPUTED else "suggested"
            options = item.get("enum") or (item["items"]["properties"]["roles"]["items"]["enum"] if kind == "people" else [])
            result.append({"field": field, "group": group, "kind": kind,
                           "options": [option for option in options if option is not None],
                           "pattern": item.get("pattern"), "minimum": item.get("minimum")})
        return result

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
        if field in helper.COMPUTED:
            raise ValueError(f"{field} is computed from the prepared manuscript and cannot be edited.")
        library = self.library(work_id)
        with self._transaction():
            active = self._unfinished(work_id)
            if active:
                raise WorkflowError("work_busy", f"Run {active} is unfinished; edit metadata through that run.")
            head = library.head("work.json")
            if head is None:
                raise ValueError("This work has no confirmed metadata yet; confirm it in a run first.")
            work = json.loads(library.read(head))
            if work["preparation"]["current_revision"] is None:
                raise ValueError("Prepare the manuscript first; enter metadata at the Overview audit.")
            helper.put(work["metadata"], field, value)
            helper.record(work, field, "user_edit", actor=actor or self.owner, rationale=rationale, review="confirmed")
            work["record_revision"] += 1
            work["updated_at"] = now()
            # New metadata revisions omit retired workflows; published history stays intact.
            workflow_fields = contract.validators()[0].schema["properties"]["workflows"]["properties"]
            work["workflows"] = {name: value for name, value in work["workflows"].items() if name in workflow_fields}
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
