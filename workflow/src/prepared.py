"""Shared prepared-manuscript engine: preparation, package verification, chapter iteration, metadata review."""

from __future__ import annotations

import copy
import json
import re
import sys
import uuid
from pathlib import Path

from .engine import SKILLS, Engine, WorkflowError, module_at
from .storage import digest, json_bytes, now, plain, read_bytes

METADATA_CONFIRMATION = "confirm metadata"
WHOLE = "_whole"  # Not a valid chapter ID, so it cannot collide with a prepared unit.
NOT_STARTED = {"status": "not_started", "basis_revision": None, "scope": None, "operation": None,
               "state_locator": None, "updated_at": None}


def load_metadata_helper(skill_root, contract):
    """Load prepare_metadata.py bound to a specific validate_preparation module."""
    previous = sys.modules.get("validate_preparation")
    sys.modules["validate_preparation"] = contract
    try:
        return module_at(skill_root / "scripts/prepare_metadata.py")
    finally:
        if previous is None:
            sys.modules.pop("validate_preparation", None)
        else:
            sys.modules["validate_preparation"] = previous


def language_key(work):
    return "manuscript_language"


def metadata_digest(work):
    value = {"metadata": work["metadata"], "metadata_provenance": work.get("metadata_provenance", {})}
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False).encode())


class PreparedManuscriptEngine(Engine):
    @classmethod
    def preflight(cls, template):
        module_at(SKILLS / "prepare-manuscript/scripts/validate_preparation.py").validators()

    @classmethod
    def initial_state(cls, template, **fields):
        state = super().initial_state(template, **fields)
        state.update(prepared=None, chapters=[], iterations=[], continuity={}, continuity_seed={},
                     metadata_approval=None, metadata_versions=[], front_matter_approvals={})
        return state

    # ----- front matter ---------------------------------------------------------------------
    # Every prepared revision starts with one front-matter unit. The engine-owned metadata review and each
    # workflow's own front-matter stages (template "front_matter": true, e.g. a translation brief) are
    # presented with it, so the studio shows them all on the front-matter page.

    @staticmethod
    def front_matter_id(state):
        return next(c["chapter_id"] for c in state["chapters"] if c["role"] == "front_matter")

    def instance(self, state):
        result = super().instance(state)
        if self.stage_def(state).get("front_matter") and state.get("chapters"):
            chapter_id = self.front_matter_id(state)
            result.update(chapter_id=chapter_id, key=f"{result['stage']}/{result['epoch']}/{chapter_id}/0")
        return result

    def document_gates(self, state, stage):
        rules = state["definition"]["gates"]
        return [kind for kind in stage.get("gates", []) if rules[kind].get("documents")]

    def on_closure(self, state, gate, receipt):
        stage = self.stage_def(state, gate["stage"])
        if not stage.get("front_matter") or gate["kind"] not in self.document_gates(state, stage):
            return
        approvals = state.setdefault("front_matter_approvals", {})
        approvals[gate["kind"]] = {"stage": stage["id"], "documents": gate["documents"], "receipt_id": receipt["id"],
                                   "decision_source": receipt["decision_source"], "created_at": receipt["created_at"]}
        if all(kind in approvals for kind in self.document_gates(state, stage)):
            # The approved documents are the chapter stage's starting point, also after a chapter-stage restart.
            iterating = self.iterating_stage(state)
            if iterating:
                state["continuity_seed"] = self.carry_snapshot(state, iterating)
            state["next_input"] = None
            self._advance_stage(state)

    def metadata_helper(self):
        """Load the pinned metadata helper bound to this run's pinned validator."""
        if not hasattr(self, "_metadata_helper"):
            self._metadata_helper = load_metadata_helper(self.root / "skills/prepare-manuscript", self.preparation)
        return self._metadata_helper

    # ----- chapters -------------------------------------------------------------------------

    def iterating_stage(self, state):
        """The chapter stage in progress, else the latest pass's or earlier chapter stage, else the first."""
        current = self._stage_or_empty(state)
        if current.get("iterate"):
            return current
        if state.get("passes"):
            return self.stage_def(state, state["passes"][-1]["stage"])
        ids = self.stage_ids(state)
        iterating = [stage for stage in ids if self.stage_def(state, stage).get("iterate")]
        position = ids.index(state["stage"]) if state["stage"] in ids else 0
        earlier = [stage for stage in iterating if ids.index(stage) < position]
        if earlier or iterating:
            return self.stage_def(state, earlier[-1] if earlier else iterating[0])
        options = [s for s in state["definition"]["stages"] if s["id"] in self.option_stages(state) and s.get("iterate")]
        return options[0] if options else None

    def on_pass_accepted(self, state, record):
        # The accepted pass keeps its chapter jobs; the next pass starts with fresh ones.
        record["iterations"] = state.get("iterations") or []
        state["iterations"] = []

    def build_iterations(self, state, stage):
        previous = {item["chapter_id"]: item["attempt"] for item in state.get("iterations", [])
                    if item.get("stage", stage["id"]) == stage["id"]}
        units = list(state["chapters"])
        if units and stage.get("iteration", {}).get("conclude"):
            # One whole-manuscript instance after the chapters, e.g. a synthesis or consistency pass.
            units.append({"chapter_id": WHOLE, "order": len(units) + 1})
        return [self._new_iteration(unit, previous.get(unit["chapter_id"], 0) + 1, stage["id"]) for unit in units]

    def on_enter_iterating(self, state, stage):
        """Hook when a chapter stage starts or restarts."""

    def _enter_stage(self, state, stage_id):
        stage = self.stage_def(state, stage_id)
        if stage.get("iterate") and state.get("chapters"):
            items = state.get("iterations") or []
            if not items or items[0].get("stage", stage_id) != stage_id:
                if items:
                    state.setdefault("stage_iterations", {})[items[0]["stage"]] = items
                state["iterations"] = self.build_iterations(state, stage)
            self.on_enter_iterating(state, stage)
        super()._enter_stage(state, stage_id)

    def current_iteration(self, state):
        return next((item for item in state.get("iterations", []) if item["status"] != "completed"), None)

    def carry_snapshot(self, state, stage):
        result = {}
        for relative in stage.get("iteration", {}).get("carry_forward", []):
            relative = self.format_path(state, relative)
            path = self.workspace / relative
            result[relative] = self.checkpoint(relative, Path(relative).stem) if path.is_file() else None
        return result

    def latest_continuity(self, state):
        """Glossary/voice of the last completed chapter, or the run's starting point if none completed."""
        done = [item for item in state.get("iterations", []) if item["status"] == "completed"]
        if done:
            return max(done, key=lambda item: item["completed_at"])["continuity_after"]
        return state.get("continuity_seed", {})

    def after_checkout(self, state):
        stage = self.iterating_stage(state)
        if stage:
            state["continuity_seed"] = self.carry_snapshot(state, stage)
        head = self.library.head("work.json") if self.library is not None else None
        if head is not None:
            # The work's latest shared record is the preparation agent's metadata input (consolidate only).
            path = plain(self.root / "input" / "prior-work.json")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.library.read(head))
            state["prior_work_record"] = {"path": str(path), "publication_id": head["id"], "sha256": head["sha256"]}
            state["library_heads"]["work.json"] = head["id"]

    def _verify_consolidation(self, state):
        """Preparation may only fill empty fields or mark existing ones stale; existing values must survive."""
        prior = state.get("prior_work_record")
        if not prior:
            return
        helper = self.metadata_helper()
        before = json.loads(read_bytes(Path(prior["path"])))
        after = json.loads(read_bytes(self._work_path(state)))
        changed = []
        for field in helper.FIELDS:
            old = helper.field_value(before["metadata"], field)
            if field in ("/extent", "/manuscript_language") or helper.missing(old):
                continue
            was, now = before["metadata_provenance"].get(field), after["metadata_provenance"].get(field)
            stale_only = bool(was and now and now.get("review_status") == "stale"
                              and {k: v for k, v in now.items() if k not in ("review_status", "updated_at", "rationale")}
                              == {k: v for k, v in was.items() if k not in ("review_status", "updated_at", "rationale")})
            if helper.field_value(after["metadata"], field) != old or (now != was and not stale_only):
                changed.append(field)
        if changed:
            raise ValueError("Preparation changed metadata the work already had (" + ", ".join(changed) + "). Start "
                             "from prior_work_record and only fill empty fields, per the prepare-manuscript "
                             "prior work record contract.")
        self.store.event("metadata.consolidated", {"prior_publication_id": prior["publication_id"]})

    def before_turn(self, state):
        stage = self.stage_def(state)
        if not stage.get("iterate"):
            return
        item = self.current_iteration(state)
        if item is None:
            raise ValueError("No chapter remains for this stage.")
        if item["status"] == "pending":
            # Equals the last completed chapter's snapshot plus user edits made between chapters.
            item.update(status="in_progress", started_at=now(), continuity_before=self.carry_snapshot(state, stage))

    def chapter_workdir(self, state, item):
        stage = self.stage_def(state, item["stage"]) if item.get("stage") else self.iterating_stage(state)
        owns = stage.get("iteration", {}).get("owns", [])
        return [self.format_path(state, path, chapter_id=item["chapter_id"]) for path in owns]

    def complete_chapter(self, state, result):
        raise NotImplementedError

    def on_completed(self, state, stage, result):
        if stage.get("preparation"):
            self._prepared(state, result["work_record"])
            self._verify_consolidation(state)
            self._advance_stage(state)
        elif stage.get("front_matter"):
            raise ValueError("A front-matter review completes when the user approves it; request its gate instead.")
        elif stage.get("iterate"):
            self._finish_chapter(state, stage, self.complete_chapter(state, result))
        else:
            super().on_completed(state, stage, result)

    def _finish_chapter(self, state, stage, artifact):
        item = self.current_iteration(state)
        chapter = next(c for c in state["chapters"] if c["chapter_id"] == item["chapter_id"])
        artifact.update(chapter_id=item["chapter_id"], source_sha256=chapter["sha256"], attempt=item["attempt"])
        if any(old["path"] == artifact["path"] for old in state["outputs"]):
            raise ValueError("A chapter output path cannot be reused for another chapter.")
        after = self.carry_snapshot(state, stage)
        item.update(status="completed", output=artifact, completed_at=now(), continuity_after=after)
        state["continuity"] = {Path(path).stem: snapshot for path, snapshot in after.items() if snapshot}
        self._refresh_outputs(state)
        state.update(thread_id=None, domain_state=None, approvals={})
        if self.current_iteration(state) is None:
            self._advance_stage(state)
        else:
            state["status"] = "READY"

    def _refresh_outputs(self, state):
        # Source order, not completion order, so a restarted chapter keeps its place.
        state["outputs"] = [item["output"] for item in state["iterations"]
                            if item["status"] == "completed" and item["output"]]

    @staticmethod
    def _new_iteration(chapter, attempt=1, stage=None):
        return {"chapter_id": chapter["chapter_id"], "order": chapter["order"], "stage": stage, "status": "pending",
                "attempt": attempt, "output": None, "continuity_before": None, "continuity_after": None,
                "started_at": None, "completed_at": None, "restarts": []}

    def reset_stage(self, state, stage):
        if stage.get("preparation"):
            state.update(prepared=None, chapters=[], iterations=[], outputs=[], continuity={},
                         metadata_approval=None, stage_iterations={}, front_matter_approvals={})
        elif stage["kind"] == "metadata_review":
            state["metadata_approval"] = None
        elif stage.get("front_matter"):
            for kind in self.document_gates(state, stage):
                state.get("front_matter_approvals", {}).pop(kind, None)
        elif stage.get("iterate"):
            state.get("stage_iterations", {}).pop(stage["id"], None)
            state["iterations"] = self.build_iterations(state, stage)
            state.update(outputs=[], continuity={})

    def restart_restore(self, state, stage_ids):
        stage = self.iterating_stage(state)
        if stage and stage["id"] in stage_ids:
            return dict(self.latest_continuity(state))
        return {}

    def on_restart_chapter(self, state, item):
        """Invalidate template-specific work that depends on a restarted chapter."""

    def restart_chapter(self, chapter_id, *, reason):
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("A restart reason is required.")
        with self.store.locked():
            revision, state = self.store.load()
            self._guard(state, "restart")
            self._require_mutable(state)
            stage = self.iterating_stage(state)
            if not stage or not stage.get("iteration", {}).get("restartable"):
                raise ValueError("This workflow has no restartable chapters.")
            acceptance = self.stage_of_kind(state, "acceptance")
            if self.select_of(state, stage["id"]):
                # A pass's chapters can be restarted until the user accepts the pass.
                current = self.open_pass(state)
                if not current or current["stage"] != stage["id"]:
                    raise ValueError("Chapters can be restarted only in the pass in progress.")
            elif state["stage"] not in (stage["id"], acceptance and acceptance["id"]):
                raise ValueError("Chapters can be restarted during the chapter stage or before final acceptance.")
            item = next((i for i in state["iterations"] if i["chapter_id"] == chapter_id), None)
            if item is None:
                raise ValueError(f"Unknown chapter: {chapter_id}")
            current = self.current_iteration(state)
            if item["status"] == "completed":
                if current and current["status"] == "in_progress" and current["chapter_id"] != WHOLE:
                    raise ValueError(f"Finish or restart chapter {current['chapter_id']} first.")
            elif item["status"] != "in_progress":
                raise ValueError(f"Chapter {chapter_id} has not started; there is nothing to restart.")
            key = f"{stage['id']}/{state['stage_epochs'].get(stage['id'], 1)}/{chapter_id}/{item['attempt']}"
            archive = self._new_archive(f"chapter-{chapter_id}-{item['attempt']}")
            for relative in self.chapter_workdir(state, item):
                self._archive(relative, archive)
            record = {"id": str(uuid.uuid4()), "kind": "chapter", "chapter_id": chapter_id,
                      "attempt": item["attempt"], "reason": reason, "created_at": now(),
                      "archive": archive.relative_to(self.root).as_posix(),
                      "superseded_receipt_ids": [r["id"] for r in state["receipts"]
                                                 if r["gate"].get("instance") == key]}
            if item["status"] == "in_progress":
                # Provisional glossary/voice changes from the abandoned attempt are discarded.
                self._restore(state, item["continuity_before"] or self.latest_continuity(state), archive)
                state.update(thread_id=None, domain_state=None, approvals={}, gate=None, next_input=None)
            else:
                if item["output"]:
                    self._archive(item["output"]["path"], archive)
                item["restarts"].append({"output": item["output"], "superseded_at": now(), "reason": reason})
                record["superseded_output"] = item["output"]
            item.update(status="pending", attempt=item["attempt"] + 1, output=None, continuity_before=None,
                        continuity_after=None, started_at=None, completed_at=None)
            self.on_restart_chapter(state, item)
            self._refresh_outputs(state)
            state.pop("acceptance_id", None)
            if self.select_of(state, stage["id"]):
                self.open_pass(state).update(completed_at=None, result=None)  # The pass is incomplete again.
            state.update(stage=stage["id"], status="READY", error=None, gate=None)
            state["restarts"].append(record)
            self.store.save(revision, state, "chapter.restarted", {"chapter_id": chapter_id, "reason": reason})
            return state

    def carry_forward(self, state):
        if "iterations" not in state:  # Pre-M1 runs kept one latest continuity snapshot.
            if not state.get("continuity") or not state.get("chapter_index"):
                return None
            files = {f"translation/{name}.md": self.store.content(snapshot)
                     for name, snapshot in state["continuity"].items()}
            return {"files": files, "origin": {"run_id": state["id"],
                                               "chapter_id": state["chapters"][state["chapter_index"] - 1]["chapter_id"]}}
        done = [item for item in state["iterations"] if item["status"] == "completed"]
        if not done:
            return None
        last = max(done, key=lambda item: item["completed_at"])
        files = {path: self.store.content(snapshot) for path, snapshot in last["continuity_after"].items() if snapshot}
        return {"files": files, "origin": {"run_id": state["id"], "chapter_id": last["chapter_id"]}}

    # ----- accepted output ------------------------------------------------------------------

    chapter_folder = "chapters"
    operation = "manuscript-workflow"

    def output_language(self, state):
        return state["manuscript_language"]

    def accepted_version(self, state):
        """The version folder for this run's accepted output: one more than the workflow's latest version."""
        if state.get("accepted_version"):
            return state["accepted_version"]
        pattern = re.compile(rf"^{re.escape(state['workflow'])}/v(\d{{3,}})/")
        numbers = [int(m.group(1)) for path in (self.library.heads() if self.library else {})
                   if (m := pattern.match(path))]
        return f"v{max(numbers, default=0) + 1:03d}"

    def run_record(self, state, version):
        """Important run information stored with the accepted Markdown."""
        receipts = {}
        for receipt in state["receipts"]:
            key = receipt["gate"]["kind"]
            entry = receipts.setdefault(key, {"replies": 0, "decided_by": {}})
            entry["replies"] += 1
            source = receipt.get("decision_source", "human")
            entry["decided_by"][source] = entry["decided_by"].get(source, 0) + 1
        attempts = {item["chapter_id"]: item["attempt"] for item in state.get("iterations") or []}
        return {
            "version": version, "workflow": state["workflow"], "template_id": state["template_id"],
            "run_id": state["id"], "work_id": state["work_id"], "owner": state.get("owner"),
            "engine": state.get("engine"), "created_at": state["created_at"],
            "accepted_at": state["acceptance"]["created_at"], "acceptance": state["acceptance"],
            "restart_of": state.get("restart_of"),
            "passes": [{"number": p["number"], "stage": p["stage"], "accepted_at": (p["accepted"] or {}).get("created_at")}
                       for p in state.get("passes") or []],
            "source": {"name": state["source_name"], "sha256": state["source"]["sha256"]},
            "manuscript_language": state["manuscript_language"], "output_language": self.output_language(state),
            "prepared_revision": state["prepared"]["base"]["preparation"]["current_revision"],
            "metadata_confirmed": state.get("metadata_approval"),
            "front_matter_reviews": {kind: {"receipt_id": a["receipt_id"], "decision_source": a["decision_source"],
                                            "documents": {d["path"]: d["sha256"] for d in a["documents"]}}
                                     for kind, a in (state.get("front_matter_approvals") or {}).items()},
            "chapters": [{"chapter_id": a["chapter_id"], "sha256": a["sha256"], "bytes": a["bytes"],
                          "attempts": attempts.get(a["chapter_id"])} for a in state["outputs"]],
            "decisions": receipts, "restarts": len(state.get("restarts") or []),
        }

    def export_files(self, state):
        files = {f"{index:04d}.md": self.store.content(artifact) for index, artifact in enumerate(state["outputs"], 1)}
        for name, artifact in state["continuity"].items():
            files[f"{name}.md"] = self.store.content(artifact)
        files["manifest.json"] = json_bytes({"run_id": state["id"], "work_id": state["work_id"],
                                             "acceptance": state["acceptance"], "source": state["source"],
                                             "chapters": state["outputs"], "continuity": state["continuity"]})
        return files

    def accepted_output(self, state):
        """The accepted-markdown-chapters/1 contract consumed by derived templates such as formatting."""
        if not state.get("acceptance"):
            return None
        version = self.accepted_version(state)
        prefix = f"{state['workflow']}/{version}"
        chapters = {c["chapter_id"]: c for c in state["chapters"]}
        return {
            "contract": state["definition"]["produces"], "workflow": state["workflow"], "version": version,
            "template_id": state["template_id"], "run_id": state["id"], "work_id": state["work_id"],
            "manuscript_language": self.output_language(state),
            "source_manuscript_language": state["manuscript_language"],
            "prepared_revision": state["prepared"]["base"]["preparation"]["current_revision"],
            "acceptance": state["acceptance"],
            "chapters": [{"chapter_id": a["chapter_id"], "order": chapters[a["chapter_id"]]["order"],
                          "title": chapters[a["chapter_id"]].get("title"), "sha256": a["sha256"],
                          "bytes": a["bytes"],
                          "artifact": f"{prefix}/chapters/{chapters[a['chapter_id']]['order']:04d}.md"}
                         for a in state["outputs"]],
            "continuity": {name: {"sha256": a["sha256"], "artifact": f"{prefix}/{name}.md"}
                           for name, a in state["continuity"].items()},
        }

    def publish_accepted(self, state):
        if self.library is None:
            return
        accepted = self.accepted_output(state)
        state["accepted_version"] = accepted["version"]
        prefix = f"{state['workflow']}/{accepted['version']}"
        expected = {item["artifact"]: item["publication_id"] for item in state["inputs"]}
        basis = {"prepared_revision": accepted["prepared_revision"]}
        entries = []
        for chapter, artifact in zip(accepted["chapters"], state["outputs"]):
            entries.append({"artifact": chapter["artifact"], "data": self.store.content(artifact),
                            "expected_head": expected.get(chapter["artifact"]), "basis": basis})
        for name, item in accepted["continuity"].items():
            entries.append({"artifact": item["artifact"], "data": self.store.content(state["continuity"][name]),
                            "expected_head": expected.get(item["artifact"]), "basis": basis})
        entries.append({"artifact": f"{prefix}/run.json", "data": json_bytes(self.run_record(state, accepted["version"])),
                        "expected_head": None, "basis": basis})
        entries.append({"artifact": f"{prefix}/manifest.json", "data": json_bytes(accepted),
                        "expected_head": None, "basis": basis, "contract": accepted["contract"]})
        summary = {"status": "completed", "basis_revision": accepted["prepared_revision"],
                   "scope": {"kind": "whole_work", "chapter_ids": [c["chapter_id"] for c in accepted["chapters"]]},
                   "operation": self.operation, "state_locator": f"run:{state['id']}", "updated_at": now()}
        entries.append(self.work_record_entry(state, "accept", summary))
        publications = self.library.publish_many(
            entries, run_id=state["id"], workflow=state["workflow"], stage="accept",
            receipts=[state["acceptance"]["id"]], finalize=[f"{prefix}/"],  # This version folder is immutable.
        )
        state["publications"] = {p["artifact"]: p["id"] for p in publications}
        state["library_heads"]["work.json"] = state["publications"]["work.json"]

    # ----- preparation ----------------------------------------------------------------------

    def verify_extra(self, state):
        prepared = state.get("prepared")
        if not prepared:
            return
        for relative, artifact in prepared["files"].items():
            if digest(read_bytes(self.file(relative))) != artifact["sha256"]:
                raise ValueError("Prepared source changed; cannot reuse approvals.")
        work = json.loads(self.file(prepared["work_record"]).read_text(encoding="utf-8"))
        source_keys = ("work_id", "discovery", "preparation")
        if {key: work[key] for key in source_keys} != {key: prepared["base"][key] for key in source_keys}:
            raise ValueError("Preparation identity changed.")
        self.preparation.validate(self.file(prepared["work_record"]), check_sources=True)
        if work["metadata"][language_key(work)] != state["manuscript_language"]:
            raise ValueError("Manuscript language metadata differs from the run; reconcile the configuration.")

    def _prepared(self, state, relative):
        path = self.file(relative)
        checked = self.preparation.validate(path, check_sources=True)
        if checked["preparation_status"] != "ready":
            raise ValueError("Preparation is not ready.")
        work = json.loads(path.read_text(encoding="utf-8"))
        if work["work_id"] != state["work_id"]:
            raise ValueError(f"Preparation must use the assigned work ID {state['work_id']}.")
        source = str(self.root / "input" / state["source_name"])
        if work["discovery"]["location_kind"] != "file" or work["discovery"]["location"] != source:
            raise ValueError("Preparation must bind the designated input snapshot.")
        if work["metadata"][language_key(work)] != state["manuscript_language"]:
            raise ValueError("Preparation manuscript language differs from the run.")
        manifest_path = path.parent / "revisions" / work["preparation"]["current_revision"] / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["scope"]["kind"] != "whole_work":
            raise ValueError("This iteration requires whole-file preparation.")
        files = [manifest_path]
        chapters = []
        for chapter in manifest["chapters"]:
            chapter_path = manifest_path.parent / chapter["file"]
            files.append(chapter_path)
            chapters.append({**chapter, "path": chapter_path.relative_to(self.workspace).as_posix()})
        files.extend(manifest_path.parent / asset["file"] for asset in manifest["assets"])
        state["prepared"] = {
            "work_record": relative,
            "base": {key: work[key] for key in ("work_id", "discovery", "preparation")},
            "files": {p.relative_to(self.workspace).as_posix(): self.store.snapshot(p, "prepared") for p in files},
        }
        state.update(chapters=chapters, thread_id=None, domain_state=None)
        first = next((self.stage_def(state, s) for s in self.stage_ids(state)
                      if self.stage_def(state, s).get("iterate")), None)
        state["iterations"] = self.build_iterations(state, first) if first else []

    # ----- metadata -------------------------------------------------------------------------

    def locked_metadata(self, state):
        return state["definition"].get("locked_metadata", [])

    def _work_path(self, state):
        return self.file(state["prepared"]["work_record"])

    def _record_metadata_version(self, state, actor):
        path = self._work_path(state)
        work = json.loads(read_bytes(path))
        fingerprint = metadata_digest(work)
        versions = state.setdefault("metadata_versions", [])
        if versions and versions[-1]["metadata_sha256"] == fingerprint:
            return None
        snapshot = self.store.snapshot(path, "metadata_record")
        entry = {"record_revision": work["record_revision"], "sha256": snapshot["sha256"],
                 "metadata_sha256": fingerprint, "schema_version": work["schema_version"],
                 "actor": actor, "created_at": now()}
        versions.append(entry)
        return entry

    def _present_metadata(self, state):
        """Engine-owned human gate: inspect, optionally edit, then confirm shared metadata."""
        stage = self.stage_of_kind(state, "metadata_review")
        state["stage"] = stage["id"]
        if self.library is not None:
            self._sync_metadata(state)
        relative = state["prepared"]["work_record"]
        work = json.loads(self.file(relative).read_text(encoding="utf-8"))
        self._record_metadata_version(state, "presented")
        instance = self.instance(state)
        # The shared metadata review is presented with the front-matter unit every prepared revision starts with.
        gate = {"id": str(uuid.uuid4()), "kind": "metadata_review", "message": self._metadata_message(state, work),
                "stage": stage["id"], "chapter_id": self.front_matter_id(state), "attempt": 0,
                "instance": instance["key"],
                "binding": self.checkpoint(relative, "metadata_record"), "sheet": None,
                "record_revision": work["record_revision"]}
        state.update(status="WAITING_FOR_HUMAN", gate=gate)

    def metadata_view(self, state):
        if not state.get("prepared"):
            raise ValueError("Metadata is available after preparation completes.")
        work = json.loads(self._work_path(state).read_text(encoding="utf-8"))
        view = {"record_revision": work["record_revision"], "schema_version": work["schema_version"],
                "metadata": work["metadata"], "provenance": work.get("metadata_provenance", {}),
                "locked": self.locked_metadata(state), "unknown": [], "stale": [],
                "confirmed": state.get("metadata_approval")}
        helper = self.metadata_helper()
        for field in helper.FIELDS:
            entry = view["provenance"].get(field)
            if entry is None and helper.missing(helper.field_value(work["metadata"], field)):
                view["unknown"].append(field)
            elif entry and entry["review_status"] == "stale":
                view["stale"].append(field)
        return view

    def _metadata_message(self, state, work):
        lines = [
            f"Inspect the shared manuscript metadata before the next stage (work.json record revision "
            f"{work['record_revision']}, schema version {work['schema_version']}).",
            "Edit a field through this gate's metadata command, or reply exactly "
            f"'{METADATA_CONFIRMATION}' to continue with these values.",
            "Locked for this run: " + ", ".join(self.locked_metadata(state)) + ".", "",
        ]
        helper = self.metadata_helper()
        provenance = work.get("metadata_provenance", {})
        unknown, stale = [], []
        for field in helper.FIELDS:
            value = helper.field_value(work["metadata"], field)
            entry = provenance.get(field)
            if entry is None:
                note = "unknown" if helper.missing(value) else "no provenance"
                if helper.missing(value):
                    unknown.append(field)
            else:
                note = f"{entry['origin']}, {entry['review_status']}"
                if entry["confidence"]:
                    note += f", confidence {entry['confidence']}"
                if entry["review_status"] == "stale":
                    stale.append(field)
            lines.append(f"{field}: {json.dumps(value, ensure_ascii=False)} [{note}]")
        lines.append("")
        lines.append("Unknown: " + (", ".join(unknown) or "none"))
        lines.append("Stale: " + (", ".join(stale) or "none"))
        return "\n".join(lines)

    def _sync_metadata(self, state):
        """Adopt the work library's latest shared metadata before the gate is presented."""
        head = self.library.head("work.json")
        if head is None or head["id"] == state["library_heads"].get("work.json"):
            return
        helper = self.metadata_helper()
        path = self._work_path(state)
        before = read_bytes(path)
        library = json.loads(self.library.read(head))
        merged = json.loads(before)
        if library["metadata"]["manuscript_language"] != merged["metadata"]["manuscript_language"]:
            raise ValueError("The work library's manuscript language differs from this run.")
        extent = merged["metadata"]["extent"], merged["metadata_provenance"].get("/extent")
        merged["metadata"] = copy.deepcopy(library["metadata"])
        merged["metadata_provenance"] = copy.deepcopy(library["metadata_provenance"])
        # Extent is computed from this run's own prepared revision.
        merged["metadata"]["extent"] = extent[0]
        merged["metadata_provenance"].pop("/extent", None)
        if extent[1]:
            merged["metadata_provenance"]["/extent"] = extent[1]
        merged["record_revision"] = max(merged["record_revision"], library["record_revision"])
        helper.save(path, before, merged)
        state["library_heads"]["work.json"] = head["id"]
        self._record_metadata_version(state, "library")
        self.store.event("metadata.synced", {"publication_id": head["id"]})

    def work_record_entry(self, state, stage, summary=None):
        """Whole-file work.json publication; other workflows' summaries come from the library head."""
        work = json.loads(read_bytes(self._work_path(state)))
        head = self.library.head("work.json")
        workflows = (json.loads(self.library.read(head))["workflows"] if head else
                     {name: dict(NOT_STARTED) for name in work["workflows"]})
        if summary is not None and state["workflow"] in workflows:
            workflows[state["workflow"]] = summary
        work["workflows"] = workflows
        return {"artifact": "work.json", "data": json_bytes(work), "stage": stage,
                "expected_head": state["library_heads"].get("work.json"),
                "basis": {"prepared_revision": work["preparation"]["current_revision"],
                          "metadata_record_revision": work["record_revision"]}}

    def _publish_metadata(self, state, stage, receipts=()):
        entry = self.work_record_entry(state, stage)
        [publication] = self.library.publish_many([entry], run_id=state["id"], workflow=state["workflow"],
                                                  receipts=list(receipts))
        state["library_heads"]["work.json"] = publication["id"]
        return publication

    def _library_changed(self, state):
        if self.library is None:
            return False
        for edit in self.library.detect_edits():  # A hand edit must become visible before any comparison.
            self.store.event("library.user_edit_detected", edit)
        head = self.library.head("work.json")
        return head is not None and head["id"] != state["library_heads"].get("work.json")

    def _confirm_metadata(self, revision, state, gate, text, decision_source):
        if text.strip() != METADATA_CONFIRMATION:
            # No agent consumes this gate; edits use edit_metadata, never free-text feedback.
            raise ValueError(f"Reply '{METADATA_CONFIRMATION}', or edit a field with the metadata command.")
        if self._library_changed(state):
            self._present_metadata(state)
            self.store.save(revision, state, "metadata.review_requested",
                            {"gate_id": state["gate"]["id"], "record_revision": state["gate"]["record_revision"],
                             "reason": "library_changed"})
            raise WorkflowError("metadata_conflict", "The work library's metadata changed; "
                                                     "review the newer record under the new gate ID.")
        receipt = {"id": str(uuid.uuid4()), "created_at": now(), "gate": gate, "text": text,
                   "parsed": {"type": "final-closure", "command": METADATA_CONFIRMATION},
                   "decision_source": decision_source}
        state["receipts"].append(receipt)
        state["metadata_approval"] = {**gate["binding"], "record_revision": gate["record_revision"],
                                      "receipt_id": receipt["id"], "decision_source": decision_source}
        if self.library is not None:
            self._publish_metadata(state, "metadata", [receipt["id"]])
        state["next_input"] = None
        self._advance_stage(state)
        self.store.save(revision, state, "metadata.confirmed", {"receipt_id": receipt["id"], "gate_id": gate["id"]})
        return state

    def edit_metadata(self, field, value, *, reason="Explicit metadata edit.", gate_id=None, actor="user"):
        with self.store.locked():
            revision, state = self.store.load()
            self._guard(state, "edit_metadata")
            if state["status"] == "RUNNING":
                raise ValueError("An agent turn is running; edit metadata after it ends.")
            self._require_mutable(state)
            if not state.get("prepared"):
                raise ValueError("Metadata can be edited after preparation completes.")
            if field in self.locked_metadata(state):
                raise ValueError(f"{field} is locked for this run.")
            gate = state["gate"]
            at_gate = state["status"] == "WAITING_FOR_HUMAN" and gate and gate["kind"] == "metadata_review"
            if (gate_id is not None and (not at_gate or gate["id"] != gate_id)) or (
                    not at_gate and not state.get("metadata_approval")):
                raise ValueError("Stale or unavailable metadata review gate.")
            self.verify(state)
            path = self._work_path(state)
            if at_gate and digest(read_bytes(path)) != gate["binding"]["sha256"]:
                raise ValueError("Metadata changed after presentation; retry with --refresh-gate to review it again.")
            if not at_gate and self._library_changed(state):
                raise WorkflowError("metadata_conflict", "The work library's metadata changed outside this run.")
            result = self.metadata_helper().update(path, "set", field=field, value=value, actor=actor, rationale=reason)
            self.verify(state)
            payload = {"field": field, "record_revision": result["record_revision"]}
            if at_gate:
                self._present_metadata(state)
                payload.update(previous_gate_id=gate["id"], gate_id=state["gate"]["id"])
            else:
                # After confirmation: history only, no re-confirmation.
                self._record_metadata_version(state, actor)
                if self.library is not None:
                    payload["publication_id"] = self._publish_metadata(state, "metadata_edit")["id"]
            self.store.save(revision, state, "metadata.edited", payload)
            return state

    def after_turn(self, state):
        if not state.get("prepared") or self.stage_def(state).get("preparation"):
            return
        entry = self._record_metadata_version(state, "agent")
        if entry is None:
            return
        self.store.event("metadata.changed_by_agent", {"record_revision": entry["record_revision"]})
        if self.library is not None and state.get("metadata_approval"):
            try:
                self._publish_metadata(state, "metadata_agent_edit")
            except WorkflowError as exc:
                state.update(status="BLOCKED", error=str(exc))

    def metadata_history(self, state):
        return list(state.get("metadata_versions", []))

    def metadata_version(self, state, record_revision):
        entry = next((v for v in reversed(state.get("metadata_versions", []))
                      if v["record_revision"] == record_revision), None)
        if entry is None:
            raise ValueError(f"No recorded metadata version {record_revision}.")
        return json.loads(self.store.content(entry))
