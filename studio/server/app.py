"""Local web API over the workflow service: works, runs, gates, chapters, and the background worker."""

from __future__ import annotations

import base64
import binascii
import json
import re
import uuid
from pathlib import Path

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from workflow.src.engine import WorkflowError, finalization_notice
from workflow.src.prepared import WHOLE
from workflow.src.runtime import CodexRuntime
from workflow.src.service import WorkflowService
from workflow.src.storage import plain
from .worker import Workers

MAX_BODY = 48 * 1024 * 1024
MAX_TEXT = 4 * 1024 * 1024
FRONTEND = Path(__file__).resolve().parents[1] / "frontend" / "dist"
TEXT_SUFFIXES = (".md", ".txt", ".json")
HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": ("default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                                "img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
                                "form-action 'self'"),
}
QUIET_PREFIXES = ("item/", "thread/", "account/", "mcpServer/", "remoteControl/", "codex/", "test.")


def create_app(server_root, *, port=8765, runtime_factory=None, codex="codex", timeout=900, owner=None,
               extra_origins=()):
    server_root = plain(Path(server_root))
    WorkflowService(server_root, owner=owner).close()  # Create the root and index up front.
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    origins = {f"http://{host}" for host in hosts}
    for origin in extra_origins:
        # Only explicit loopback origins (e.g. a local preview proxy) may write.
        if not re.fullmatch(r"http://(127\.0\.0\.1|localhost):\d{1,5}", origin):
            raise ValueError(f"Only loopback http origins can be allowed: {origin}")
        origins.add(origin)
        hosts.add(origin.removeprefix("http://"))
    workers = Workers(server_root, runtime_factory or (lambda: CodexRuntime([codex, "app-server"], timeout)),
                      owner=owner)
    app = FastAPI(title="Manuscript Studio", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.workers = workers

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        # Localhost only: reject other Host headers (DNS rebinding) and cross-origin writes.
        if request.headers.get("host") not in hosts:
            return JSONResponse({"detail": "Unexpected host."}, status_code=421, headers=HEADERS)
        if request.method not in ("GET", "HEAD"):
            if request.headers.get("origin") not in origins:
                return JSONResponse({"detail": "Cross-origin request refused."}, status_code=403, headers=HEADERS)
            if int(request.headers.get("content-length") or 0) > MAX_BODY:
                return JSONResponse({"detail": "Request body too large."}, status_code=413, headers=HEADERS)
        response = await call_next(request)
        response.headers.update(HEADERS)
        return response

    @app.exception_handler(WorkflowError)
    async def workflow_error(request, exc):
        return JSONResponse({"detail": str(exc), "code": exc.code}, status_code=409)

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        status = 404 if str(exc).startswith(("Unknown run", "Unknown work", "Unknown publication")) else 400
        return JSONResponse({"detail": str(exc)}, status_code=status)

    def service():
        with WorkflowService(server_root, owner=owner) as value:
            yield value

    # ----- templates and works -------------------------------------------------------------

    @app.get("/api/templates")
    def templates(svc: WorkflowService = Depends(service)):
        return svc.list_templates()

    @app.get("/api/works")
    def works(svc: WorkflowService = Depends(service)):
        result = []
        for work in svc.list_works():
            detail = svc.get_work(work["id"])
            result.append({**work, "workflows": detail["workflows"], "unfinished_run": detail["unfinished_run"],
                           "runs": len(detail["runs"]), "artifacts": len(detail["heads"])})
        return result

    @app.post("/api/works")
    def create_work(payload: dict = Body(...), svc: WorkflowService = Depends(service)):
        """Manuscript intake happens on the Works page; workflows then start on the work."""
        upload = payload.get("upload") or {}
        name = Path(str(upload.get("name", ""))).name
        if not name or name in (".", ".."):
            raise HTTPException(400, "The upload needs a file name.")
        try:
            data = base64.b64decode(upload.get("data", ""), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(400, "The upload is not valid base64.") from exc
        folder = server_root / "uploads" / uuid.uuid4().hex
        folder.mkdir(parents=True)
        target = folder / name
        target.write_bytes(data)
        try:
            work_id = svc.create_work(target, payload.get("manuscript_language"))
        finally:
            target.unlink(missing_ok=True)
            folder.rmdir()
        return work(work_id, svc)

    @app.get("/api/works/{work_id}")
    def work(work_id: str, svc: WorkflowService = Depends(service)):
        detail = svc.get_work(work_id)
        try:
            detail["metadata"] = svc.get_work_metadata(work_id)
            detail["metadata_history"] = svc.work_metadata_history(work_id)
        except ValueError:
            detail["metadata"], detail["metadata_history"] = None, []
        detail["metadata_fields"] = svc.metadata_fields()
        detail["publications"] = [{key: record.get(key) for key in (
            "id", "created_at", "artifact", "version", "status", "review_status", "stage", "run_id", "workflow",
            "bytes", "contract")} for record in svc.work_publications(work_id)]
        return detail

    @app.post("/api/works/{work_id}/metadata")
    def edit_work_metadata(work_id: str, payload: dict = Body(...), svc: WorkflowService = Depends(service)):
        """Edit shared metadata on the work itself; refused while a run is unfinished on the work."""
        svc.edit_work_metadata(work_id, payload["field"], payload["value"],
                               payload.get("rationale") or "Explicit metadata edit.")
        return work(work_id, svc)

    @app.get("/api/works/{work_id}/artifact")
    def artifact(work_id: str, path: str, svc: WorkflowService = Depends(service)):
        library = svc.library(work_id)
        head = library.head(path)
        if head is None:
            raise HTTPException(404, "No published version of that artifact.")
        if not path.endswith(TEXT_SUFFIXES) or head["bytes"] > MAX_TEXT:
            raise HTTPException(415, "Only text artifacts up to 4 MiB can be viewed.")
        return PlainTextResponse(library.read(head).decode("utf-8"))

    # ----- runs ----------------------------------------------------------------------------

    def documents(engine, snapshots):
        """Presented workspace documents (e.g. a translation brief's glossary and voice) as text."""
        return [{"path": item["path"], "sha256": item["sha256"], "text": engine.store.content(item).decode("utf-8")}
                for item in snapshots or []]

    def run_detail(svc, run_id):
        detail = svc.get_run(run_id)
        detail["worker"] = workers.status(run_id)
        with svc.open_run(run_id) as engine:
            state = engine.state()
            detail["template_title"] = state.get("definition", {}).get("title")
            detail["stages"] = engine.stage_ids(state)
            detail["skipped_stages"] = state.get("skipped_stages") or []
            gate = state.get("gate")
            if gate:
                view = detail["gate"]
                view["sheet"] = json.loads(engine.store.content(gate["sheet"])) if gate.get("sheet") else None
                view["commands"] = engine.gate_commands(state, gate)
                # When this request follows the reviewer's feedback, the gate message is the answer to it.
                previous = next((r for r in reversed(state["receipts"]) if r["gate"]["kind"] == gate["kind"]
                                 and r["gate"].get("chapter_id") == gate.get("chapter_id")), None)
                view["answer_to"] = ({"text": previous["text"], "created_at": previous["created_at"]}
                                     if previous and previous["parsed"].get("type") == "feedback" else None)
                view["binding_text"] = None
                if gate.get("binding") and gate["kind"] != "metadata_review" and gate["binding"]["bytes"] <= MAX_TEXT:
                    try:
                        view["binding_text"] = engine.store.content(gate["binding"]).decode("utf-8")
                    except UnicodeDecodeError:
                        pass
                view["documents"] = documents(engine, gate.get("documents"))
                if gate["kind"] == "metadata_review":
                    detail["metadata"] = engine.metadata_view(state)
                    detail["metadata_fields"] = svc.metadata_fields()
            if state["status"] == "WAITING_FOR_ACCEPTANCE":
                detail["acceptance"] = {"acceptance_id": state["acceptance_id"],
                                        "notice": finalization_notice(state["workflow"]),
                                        "outputs": [{k: o.get(k) for k in ("chapter_id", "sha256", "bytes")}
                                                    for o in state["outputs"]]}
        return detail

    @app.get("/api/runs")
    def runs(work_id: str | None = None, svc: WorkflowService = Depends(service)):
        result = []
        for row in reversed(svc.list_runs(work_id=work_id)):
            summary = svc.get_run(row["id"])
            result.append({**summary, "created_at": row["created_at"], "updated_at": row["updated_at"],
                           "worker": workers.status(row["id"])})
        return result

    @app.post("/api/runs")
    def create(payload: dict = Body(...), svc: WorkflowService = Depends(service)):
        template_id = payload.get("template_id")
        if not isinstance(template_id, str):
            raise HTTPException(400, "template_id is required.")
        if payload.get("upload"):
            raise HTTPException(400, "Add manuscripts on the Works page, then start a workflow on the work.")
        if not payload.get("work_id"):
            raise HTTPException(400, "Select the work to run the workflow on.")
        if payload.get("derived"):
            run_id = svc.create_derived_run(payload["work_id"], template_id, publication_id=payload.get("publication_id"),
                                            options=payload.get("options") or {}, model=payload.get("model"))
        else:
            run_id = svc.create_run(template_id, work_id=payload.get("work_id"), model=payload.get("model"),
                                    skip_stages=payload.get("skip_stages") or (), settings=payload.get("settings"))
        if payload.get("start", True):
            workers.start(run_id)
        return run_detail(svc, run_id)

    @app.get("/api/runs/{run_id}")
    def run(run_id: str, svc: WorkflowService = Depends(service)):
        return run_detail(svc, run_id)

    @app.get("/api/runs/{run_id}/events")
    def events(run_id: str, after: int = 0, verbose: bool = False, svc: WorkflowService = Depends(service)):
        rows = svc.events(run_id, after)
        last = rows[-1]["id"] if rows else after
        if not verbose:
            rows = [e for e in rows if not e["kind"].startswith(QUIET_PREFIXES)
                    or e["kind"] in ("turn/started", "turn/completed")]
        return {"events": rows[-500:], "last_id": last}

    def act(svc, run_id, operation, resume=True):
        operation()
        if resume:
            workers.start(run_id)
        return run_detail(svc, run_id)

    @app.post("/api/runs/{run_id}/reply")
    def reply(run_id: str, payload: dict = Body(...), svc: WorkflowService = Depends(service)):
        return act(svc, run_id, lambda: svc.reply(run_id, payload["gate_id"], payload["text"]))

    @app.post("/api/runs/{run_id}/accept")
    def accept(run_id: str, payload: dict = Body(...), svc: WorkflowService = Depends(service)):
        return act(svc, run_id, lambda: svc.accept(run_id, payload["acceptance_id"],
                                                   confirm_final=payload.get("confirm_final") is True))

    @app.post("/api/runs/{run_id}/metadata")
    def metadata(run_id: str, payload: dict = Body(...), svc: WorkflowService = Depends(service)):
        return act(svc, run_id, lambda: svc.edit_metadata(run_id, payload["field"], payload["value"],
                                                          payload.get("rationale") or "Explicit metadata edit.",
                                                          gate_id=payload.get("gate_id")), resume=False)

    @app.post("/api/runs/{run_id}/metadata/confirm")
    def confirm_metadata(run_id: str, payload: dict = Body(...), svc: WorkflowService = Depends(service)):
        return act(svc, run_id, lambda: svc.confirm_metadata(run_id, payload["gate_id"], payload["record_revision"]))

    @app.get("/api/runs/{run_id}/metadata/history")
    def metadata_history(run_id: str, svc: WorkflowService = Depends(service)):
        return svc.metadata_history(run_id)

    @app.post("/api/runs/{run_id}/retry")
    def retry(run_id: str, payload: dict = Body(default={}), svc: WorkflowService = Depends(service)):
        return act(svc, run_id, lambda: svc.retry(run_id, confirm_stopped=payload.get("confirm_stopped") is True,
                                                  refresh_gate=payload.get("refresh_gate") is True))

    @app.post("/api/runs/{run_id}/restart-chapter")
    def restart_chapter(run_id: str, payload: dict = Body(...), svc: WorkflowService = Depends(service)):
        return act(svc, run_id, lambda: svc.restart_chapter(run_id, payload["chapter_id"], reason=payload["reason"]))

    @app.post("/api/runs/{run_id}/restart-stage")
    def restart_stage(run_id: str, payload: dict = Body(...), svc: WorkflowService = Depends(service)):
        return act(svc, run_id, lambda: svc.restart_stage(run_id, payload["stage"], reason=payload["reason"]))

    @app.post("/api/runs/{run_id}/restart")
    def restart_workflow(run_id: str, payload: dict = Body(...), svc: WorkflowService = Depends(service)):
        new_id = svc.restart_workflow(run_id, reason=payload["reason"],
                                      confirm_stopped=payload.get("confirm_stopped") is True)
        workers.start(new_id)
        return run_detail(svc, new_id)

    @app.post("/api/runs/{run_id}/stop")
    def stop(run_id: str, svc: WorkflowService = Depends(service)):
        return act(svc, run_id, lambda: svc.stop(run_id), resume=False)

    @app.post("/api/runs/{run_id}/pause")
    def pause(run_id: str, svc: WorkflowService = Depends(service)):
        workers.pause(run_id)
        return run_detail(svc, run_id)

    @app.post("/api/runs/{run_id}/resume")
    def resume(run_id: str, svc: WorkflowService = Depends(service)):
        workers.resume(run_id)
        return run_detail(svc, run_id)

    # ----- chapter browser (inside a run) --------------------------------------------------

    def chapter_records(engine, state):
        """Per-stage iteration records keyed by stage, including stages that already finished."""
        default = (engine.iterating_stage(state) or {}).get("id")
        groups = dict(state.get("stage_iterations") or {})
        for item in state.get("iterations") or []:
            groups.setdefault(item.get("stage") or default, [])
            if item not in groups[item.get("stage") or default]:
                groups[item.get("stage") or default].append(item)
        return groups

    @app.get("/api/runs/{run_id}/chapters")
    def chapters(run_id: str, svc: WorkflowService = Depends(service)):
        with svc.open_run(run_id) as engine:
            state = engine.state()
            groups = chapter_records(engine, state)
            stages = [s for s in engine.stage_ids(state) if s in groups] if groups else []
            result = []
            for chapter in state.get("chapters") or []:
                outputs = {}
                for stage in stages:
                    item = next((i for i in groups[stage] if i["chapter_id"] == chapter["chapter_id"]), None)
                    if item:
                        outputs[stage] = {"status": item["status"], "attempt": item["attempt"],
                                          "ready": bool(item["status"] == "completed" and item.get("output")),
                                          # Approved by the reviewer; the agent is saving the chapter.
                                          "saving": bool(item["status"] == "in_progress"
                                                         and "chapter_sanity" in (state.get("approvals") or {}))}
                result.append({key: chapter.get(key) for key in ("chapter_id", "order", "title", "role", "sha256")}
                              | {"outputs": outputs})
            return {"prepared": bool(state.get("prepared")), "stages": stages, "chapters": result,
                    "whole_book": {stage: next((i["status"] for i in groups[stage] if i["chapter_id"] == WHOLE), None)
                                   for stage in stages}}

    @app.get("/api/runs/{run_id}/chapters/{chapter_id}")
    def chapter(run_id: str, chapter_id: str, svc: WorkflowService = Depends(service)):
        with svc.open_run(run_id) as engine:
            state = engine.state()
            if not state.get("prepared"):
                raise HTTPException(409, "Chapters are available after preparation completes.")
            record = next((c for c in state["chapters"] if c["chapter_id"] == chapter_id), None)
            if record is None:
                raise HTTPException(404, "Unknown chapter.")
            prepared = engine.store.content(state["prepared"]["files"][record["path"]]).decode("utf-8")
            outputs = []
            for stage, items in chapter_records(engine, state).items():
                item = next((i for i in items if i["chapter_id"] == chapter_id), None)
                if item and item["status"] == "completed" and item.get("output"):
                    outputs.append({"stage": stage, "attempt": item["attempt"], "sha256": item["output"]["sha256"],
                                    "text": engine.store.content(item["output"]).decode("utf-8")})
            map_path = engine.workspace / "translation" / "maps" / f"{chapter_id}.json"
            passage_map = json.loads(map_path.read_text(encoding="utf-8")) if map_path.is_file() else None
            # Completed front-matter reviews: the shared metadata and each workflow's own (e.g. translation brief).
            reviews = []
            if record["role"] == "front_matter":
                if state.get("metadata_approval"):
                    reviews.append({"kind": "metadata_review", "record_revision": state["metadata_approval"]["record_revision"],
                                    "decision_source": state["metadata_approval"]["decision_source"], "documents": []})
                for kind, approval in (state.get("front_matter_approvals") or {}).items():
                    reviews.append({"kind": kind, "created_at": approval["created_at"],
                                    "decision_source": approval["decision_source"],
                                    "documents": documents(engine, approval["documents"])})
            return {"chapter": {k: record.get(k) for k in ("chapter_id", "order", "title", "role", "sha256")},
                    "prepared_text": prepared, "outputs": outputs, "passage_map": passage_map, "reviews": reviews}

    # ----- frontend ------------------------------------------------------------------------

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Unknown API route.")
        target = (FRONTEND / path).resolve()
        if path and target.is_file() and target.is_relative_to(FRONTEND):
            return FileResponse(target)
        index = FRONTEND / "index.html"
        if not index.is_file():
            return PlainTextResponse("Frontend not built: run `npm ci && npm run build` in studio/frontend.",
                                     status_code=503)
        return FileResponse(index)

    return app
