"""Workflow-owned approvals and artifacts over the standalone DOCX formatter API."""

from __future__ import annotations

import importlib
import json
import uuid

from .engine import WorkflowError
from .storage import digest, json_bytes, now, plain, read_bytes, write_new

PRODUCTION_STAGE = "produce-docx"
PRODUCTION_GATE = "docx_generation_review"
DOCX_NOTICE = (
    "Editable DOCX only. Content, structure and native settings are checked. "
    "No PDF, rendered-page review, calculated pagination, font resolution or print certification."
)


class DocxProductionPhase:
    def _approved_design(self, state):
        self.verify_design(state)
        approval = state.get("design_approval")
        if not approval or not state.get("manuscript_approval"):
            raise ValueError("Manuscript and design approval are required before DOCX production.")
        receipt = next((r for r in state["receipts"] if r["id"] == approval["receipt_id"]), None)
        if not receipt or receipt["decision_source"] != "human" \
                or receipt["parsed"]["type"] != "design-approval" \
                or receipt["gate"]["binding"]["sha256"] != approval["proposal"]["sha256"] \
                or state["design_draft"]["sha256"] != approval["proposal"]["sha256"]:
            raise ValueError("DOCX production requires the exact current human design-approval receipt.")
        proposal = json.loads(self.store.content(approval["proposal"]))
        self.interior_validator.validate(proposal, work_path=self.file(state["design_work_record"]))
        self.verify_proposal_profile(state, proposal)
        return proposal, receipt

    def _docx_plan(self, state):
        proposal, receipt = self._approved_design(state)
        try:
            formatter = importlib.import_module("book_formatter")
        except ImportError as exc:
            raise WorkflowError("formatter_unavailable", "Install the standalone tool from the repository root: "
                                "python -m pip install -e tools/formattor") from exc
        plan = formatter.prepare(
            self.root / "objects" / state["design_approval"]["proposal"]["sha256"],
            self.file(state["design_work_record"]),
            expected_edition_brief=proposal["edition_brief"], answers=receipt["parsed"]["answers"],
        )
        return formatter, plan

    def _save_production_plan(self, state, plan):
        previous = state.get("production")
        if previous:
            state.setdefault("production_history", []).append(previous)
        data = plan.to_dict()
        job = {"id": uuid.uuid4().hex, "status": "plan-review", "created_at": now(),
               "proposal_sha256": state["design_approval"]["proposal"]["sha256"],
               "design_receipt_id": state["design_approval"]["receipt_id"],
               "plan_sha256": plan.sha256, "authorization": None, "result": None, "attempts": 0,
               "summary": {"units": len(data["units"]),
                           "paragraphs": sum(len(u["paragraphs"]) for u in data["units"]),
                           "styles": ["BF." + s["id"] for s in data["styles"]],
                           "policy": data["policy"], "vendor_warnings": data["vendor_warnings"]}}
        folder = plain(self.root / "production" / job["id"])
        folder.mkdir(parents=True)
        path = folder / "plan.json"
        write_new(path, json_bytes({"plan_sha256": plan.sha256, "plan": data}))
        job["plan"] = self.store.snapshot(path, "docx_plan")
        state["production"] = job
        state.update(status="WAITING_FOR_HUMAN", error=None, next_input=None,
                     gate={"id": str(uuid.uuid4()), "kind": PRODUCTION_GATE, "stage": PRODUCTION_STAGE,
                           "chapter_id": None, "attempt": 0, "instance": job["id"],
                           "message": "Review and authorize this exact DOCX generation plan. " + DOCX_NOTICE,
                           "binding": job["plan"], "sheet": None})

    def authorize_docx(self, gate_id, expected_plan_sha256):
        with self.store.locked():
            revision, state = self.store.load()
            self._guard(state, "reply")
            gate, job = state.get("gate"), state.get("production")
            if state["status"] != "WAITING_FOR_HUMAN" or state["stage"] != PRODUCTION_STAGE \
                    or not gate or gate["id"] != gate_id or gate["kind"] != PRODUCTION_GATE \
                    or not job or job["status"] != "plan-review" or job["plan_sha256"] != expected_plan_sha256 \
                    or gate["binding"]["sha256"] != job["plan"]["sha256"]:
                raise ValueError("Stale or unavailable DOCX generation plan.")
            self.verify(state)
            self._approved_design(state)
            self.store.content(job["plan"])
            receipt = {"id": str(uuid.uuid4()), "created_at": now(), "gate": gate,
                       "text": "Authorize editable DOCX generation. " + DOCX_NOTICE,
                       "parsed": {"type": "docx-generation", "plan_sha256": expected_plan_sha256,
                                  "proposal_sha256": job["proposal_sha256"]}, "decision_source": "human"}
            state["receipts"].append(receipt)
            job.update(status="authorized", authorization=receipt["id"])
            state.update(status="READY", gate=None, error=None)
            self.store.save(revision, state, "docx.authorized", {"receipt_id": receipt["id"]})
            return state

    def production_step(self, revision, state):
        try:
            formatter, plan = self._docx_plan(state)
            plan_data = plan.to_dict()
            job = state.get("production")
            if not job or not job.get("authorization") or job["plan_sha256"] != plan.sha256:
                self._save_production_plan(state, plan)
                self.store.save(revision, state, "docx.plan_presented",
                                {"plan_sha256": plan.sha256, "build_id": state["production"]["id"]})
                return state
            envelope = json.loads(self.store.content(job["plan"]))
            if envelope["plan_sha256"] != plan.sha256 or envelope["plan"] != plan.to_dict():
                raise ValueError("The authorized DOCX plan snapshot does not match current inputs.")
            receipt = next((r for r in state["receipts"] if r["id"] == job["authorization"]), None)
            if not receipt or receipt["decision_source"] != "human" \
                    or receipt["parsed"] != {"type": "docx-generation", "plan_sha256": plan.sha256,
                                            "proposal_sha256": job["proposal_sha256"]} \
                    or receipt["gate"]["kind"] != PRODUCTION_GATE or receipt["gate"]["instance"] != job["id"] \
                    or receipt["gate"]["binding"]["sha256"] != job["plan"]["sha256"] \
                    or job["proposal_sha256"] != state["design_approval"]["proposal"]["sha256"] \
                    or job["design_receipt_id"] != state["design_approval"]["receipt_id"]:
                raise ValueError("DOCX generation authorization does not match the current design and plan.")
            job.update(status="building", attempts=job["attempts"] + 1, error=None)
            state.update(status="RUNNING", error=None)
            revision = self.store.save(revision, state, "docx.started", {"build_id": job["id"]})
            # Every attempt owns a new path; an interrupted build is never reused or overwritten.
            output = plain(self.root / "production" / job["id"] / (uuid.uuid4().hex + ".docx"))
            result = formatter.build(plan, output, approved_plan_sha256=plan.sha256)
            if result["output"] != str(output) or result["sha256"] != digest(read_bytes(output)):
                raise ValueError("The formatter result does not identify the actual owned DOCX.")
            if result["rendered"] or result["print_verified"] or result["plan_sha256"] != plan.sha256:
                raise ValueError("Unexpected formatter scope or plan identity.")
            self.verify(state)
            artifact = self.store.snapshot(output, "editable_docx")
            if artifact["sha256"] != result["sha256"]:
                raise ValueError("The DOCX changed between formatter verification and sealing.")
            manifest = {"contract": "workflow-docx-build/1", "build_id": job["id"],
                        "run_id": state["id"], "work_id": state["work_id"], "created_at": now(),
                        "host_engine": state["engine"], "document_file": "document.docx",
                        "plan_sha256": plan.sha256, "plan": job["plan"],
                        "proposal": state["design_approval"]["proposal"],
                        "design_receipt_id": job["design_receipt_id"],
                        "generation_receipt_id": job["authorization"],
                        "manuscript_receipt_id": state["manuscript_approval"]["id"],
                        "source_units": [{"chapter_id": u["chapter_id"], "sha256": u["sha256"]}
                                         for u in plan_data["units"]],
                        "runtime": plan_data["runtime"], "engine_sha256": plan_data["engine_sha256"],
                        "docx": artifact, "verification": result["verification"],
                        "rendered": False, "print_verified": False, "scope": DOCX_NOTICE}
            manifest_path = output.with_suffix(".json")
            write_new(manifest_path, json_bytes(manifest))
            job.update(status="candidate", result={"docx": artifact,
                                                  "manifest": self.store.snapshot(manifest_path, "docx_build")})
            self._advance_stage(state)
            self.store.save(revision, state, "docx.ready", {"build_id": job["id"], "sha256": artifact["sha256"]})
            return state
        except (Exception, KeyboardInterrupt) as exc:
            revision, saved = self.store.load()
            error = {"code": getattr(exc, "code", "docx_failed"), "message": str(exc)}
            if saved.get("production"):
                saved["production"].update(status="failed", error=error)
            saved.update(status="PAUSED" if isinstance(exc, KeyboardInterrupt) else "BLOCKED", error=str(exc))
            self.store.save(revision, saved, "docx.failed", error)
            raise

    def verify_docx_candidate(self, state):
        self._approved_design(state)
        job = state.get("production")
        if not job or job["status"] != "candidate" or not job.get("result") \
                or job["proposal_sha256"] != state["design_approval"]["proposal"]["sha256"] \
                or job["design_receipt_id"] != state["design_approval"]["receipt_id"]:
            raise ValueError("Final acceptance requires the current verified DOCX candidate.")
        result = job["result"]
        receipt = next((r for r in state["receipts"] if r["id"] == job["authorization"]), None)
        if not receipt or receipt["decision_source"] != "human" \
                or receipt["parsed"] != {"type": "docx-generation", "plan_sha256": job["plan_sha256"],
                                        "proposal_sha256": job["proposal_sha256"]} \
                or receipt["gate"]["instance"] != job["id"] \
                or receipt["gate"]["binding"]["sha256"] != job["plan"]["sha256"]:
            raise ValueError("The DOCX candidate has no matching exact-plan authorization.")
        self.store.content(result["docx"])
        manifest = json.loads(self.store.content(result["manifest"]))
        if manifest["docx"] != result["docx"] or manifest["plan_sha256"] != job["plan_sha256"] \
                or manifest["generation_receipt_id"] != job["authorization"] \
                or manifest["proposal"]["sha256"] != job["proposal_sha256"]:
            raise ValueError("The DOCX build manifest no longer matches its approval bindings.")
        return job

    def production_view(self, state):
        job = state.get("production")
        if not job:
            return None
        return {key: job.get(key) for key in ("id", "status", "plan_sha256", "proposal_sha256", "summary",
                                             "attempts", "error")} | {
            "notice": DOCX_NOTICE, "accepted": bool(state.get("acceptance")),
            "docx": job["result"]["docx"] if job.get("result") else None}

    def delivery_files(self, state):
        if not state.get("production"):
            return super().delivery_files(state)
        job = self.verify_docx_candidate(state)
        return {"document.docx": self.store.content(job["result"]["docx"]),
                "docx-build.json": self.store.content(job["result"]["manifest"]),
                "design-proposal.json": self.store.content(state["design_approval"]["proposal"])}
