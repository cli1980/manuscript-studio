"""Local web API over the workflow service: works, runs, gates, chapters, and the background worker."""

from __future__ import annotations

import asyncio
import base64
import binascii
import contextlib
import io
import json
import mimetypes
import re
import uuid
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import quote

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response, StreamingResponse

from workflow.src.engine import WorkflowError
from workflow.src.prepared import WHOLE
from workflow.src.runtime import CodexRuntime
from workflow.src.service import WorkflowService
from workflow.src.storage import digest, plain
from .live import Watcher, visible
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
KEEPALIVE = 15  # Seconds between stream pings, so a client can tell a quiet feed from a dead one.


def docx_disposition(data, version, *, build_id=None):
    # Use the delivered document's frozen title, not subsequently edited work metadata.
    with zipfile.ZipFile(io.BytesIO(data)) as document:
        core = ET.fromstring(document.read("docProps/core.xml"))
    title = core.findtext("{http://purl.org/dc/elements/1.1/}title") or "Manuscript"
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", title)
    title = re.sub(r"\s+", " ", title).strip(" .") or "Manuscript"
    # Bound the UTF-8 filename size while retaining multilingual titles.
    title = title.encode("utf-8")[:160].decode("utf-8", errors="ignore").rstrip(" .")
    suffix = f"-candidate-{build_id[:8]}" if build_id else ""
    name = f"{title}-{version}{suffix}.docx"
    fallback = re.sub(r'[^\w.\- ]', "_", name.encode("ascii", "replace").decode("ascii"))
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(name, safe='')}"


def create_app(server_root, *, port=8765, runtime_factory=None, codex="codex", timeout=900, owner=None,
               extra_origins=(), execution_profile=None):
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
    runtime_factory = runtime_factory or (execution_profile.runtime if execution_profile else
                                         lambda: CodexRuntime([codex, "app-server"], timeout))
    workers = Workers(server_root, runtime_factory, owner=owner, execution_profile=execution_profile)
    live = Watcher(server_root, workers)

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        yield
        live.stop()

    app = FastAPI(title="Manuscript Studio", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.workers = workers
    app.state.live = live

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
        with WorkflowService(server_root, owner=owner, execution_profile=execution_profile) as value:
            yield value

    # ----- templates and works -------------------------------------------------------------

    @app.get("/api/execution")
    def execution():
        return execution_profile.public() if execution_profile else {
            "name": "codex-default", "harness": "codex", "models": []}

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
        detail["metadata_editor_run"] = svc.metadata_editor_run(work_id)
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

    @app.get("/api/works/{work_id}/source")
    def source(work_id: str, svc: WorkflowService = Depends(service)):
        """Download the original upload under its uploaded name, from the checksum-verified library object."""
        library = svc.library(work_id)
        _, record = library.source()
        name = record.get("source_name") or Path(record["artifact"]).name
        fallback = re.sub(r'[^\w.\- ]', "_", name.encode("ascii", "replace").decode("ascii"))
        return Response(library.read(record), media_type=mimetypes.guess_type(name)[0] or "application/octet-stream",
                        headers={"Content-Disposition": f"attachment; filename=\"{fallback}\"; "
                                                        f"filename*=UTF-8''{quote(name)}"})

    # ----- runs ----------------------------------------------------------------------------

    def documents(engine, snapshots):
        """Presented workspace documents (e.g. a translation brief's glossary and voice) as text."""
        return [{"path": item["path"], "sha256": item["sha256"], "text": engine.store.content(item).decode("utf-8")}
                for item in snapshots or []]

    def current_documents(engine, state, approved):
        """Working documents can evolve after approval; finalized runs use their accepted snapshots."""
        accepted = {item["path"]: item for item in state.get("continuity", {}).values()}
        result = []
        for item in approved:
            content = (engine.store.content(accepted.get(item["path"], item)) if engine.finalized(state)
                       else engine.file(item["path"]).read_bytes())
            result.append({"path": item["path"], "sha256": digest(content), "text": content.decode("utf-8")})
        return result

    def run_detail(svc, run_id):
        with svc.open_run(run_id) as engine:
            state = engine.state()
            detail = svc.run_view(engine, state)
            detail["worker"] = workers.status(run_id)
            detail["template_title"] = state.get("definition", {}).get("title")
            detail["stages"] = engine.stage_ids(state)
            detail["stage_titles"] = {o["stage"]: o["title"] for s in state.get("definition", {}).get("stages", [])
                                      for o in s.get("options", [])}
            detail["viewer_target"] = viewer_target(state)
            if engine.retired or not detail["engine_current"] or state["status"] in ("COMPLETED", "CANCELLED"):
                detail.pop("gate", None)
                return detail
            gate = state.get("gate")
            if gate:
                view = detail["gate"]
                view["sheet"] = json.loads(engine.store.content(gate["sheet"])) if gate.get("sheet") else None
                if gate["kind"] == "translation_consistency" and view["sheet"]:
                    plan = json.loads(engine.store.content(gate["binding"]))
                    locations = {change["id"]: change["chapter_id"] for change in plan["changes"]}
                    for item in view["sheet"]["items"]:
                        item["chapter_id"] = locations[item["id"]]
                view["commands"] = engine.gate_commands(state, gate)
                if gate["kind"] == "interior_design_review":
                    view["design_review"] = engine.design_view(state)
                # When this request follows the reviewer's feedback, the gate message is the answer to it.
                previous = next((r for r in reversed(state["receipts"]) if r["gate"]["kind"] == gate["kind"]
                                 and r["gate"].get("chapter_id") == gate.get("chapter_id")), None)
                view["answer_to"] = ({"text": previous["text"], "created_at": previous["created_at"]}
                                     if previous and previous["parsed"].get("type") == "feedback" else None)
                view["binding_text"] = None
                if gate.get("binding") and gate["kind"] not in ("metadata_review", "docx_generation_review") \
                        and gate["binding"]["bytes"] <= MAX_TEXT:
                    try:
                        view["binding_text"] = engine.store.content(gate["binding"]).decode("utf-8")
                    except UnicodeDecodeError:
                        pass
                view["documents"] = documents(engine, gate.get("documents"))
                if gate["kind"] == "metadata_review":
                    detail["metadata"] = engine.metadata_view(state)
                    detail["metadata_fields"] = svc.metadata_fields()
            if state["status"] == "WAITING_FOR_ACCEPTANCE":
                detail["acceptance"] = {**engine.acceptance_details(state), "acceptance_id": state["acceptance_id"],
                                        "outputs": [{k: o.get(k) for k in ("chapter_id", "sha256", "bytes")}
                                                    for o in state["outputs"]]}
        return detail

    @app.get("/api/runs")
    def runs(work_id: str | None = None, svc: WorkflowService = Depends(service)):
        result = []
        for row in reversed(svc.list_runs(work_id=work_id)):
            with svc.open_run(row["id"]) as engine:
                state = engine.state()
                summary = svc.run_view(engine, state, include_usage=False)
                summary["viewer_target"] = viewer_target(state)
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
        if any(key in payload for key in ("derived", "publication_id", "options", "new_edition")):
            raise HTTPException(400, "Separate formatting runs were removed. Use the workflow's final formatting phase.")
        run_id = svc.create_run(template_id, work_id=payload.get("work_id"), model=payload.get("model"),
                                settings=payload.get("settings"))
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
            rows = [e for e in rows if visible(e["kind"])]
        return {"events": rows[-500:], "last_id": last}

    # ----- change feed ---------------------------------------------------------------------

    def live_payload():
        version, snapshot = live.current()
        return {"version": version, **(snapshot or {"runs": {}, "works": {}})}

    @app.get("/api/live")
    async def live_snapshot():
        """The current fingerprints, for clients that cannot keep a stream open."""
        live.start()
        for _ in range(50):  # The first scan runs on the watcher thread.
            if live.current()[0]:
                break
            await asyncio.sleep(0.1)
        return live_payload()

    @app.get("/api/live/stream")
    async def live_stream(request: Request):
        """Server-sent events: the fingerprints whenever they change, and a ping while nothing does."""
        live.start()

        async def feed():
            sent, quiet = 0, 0.0
            yield "retry: 3000\n\n"
            while not await request.is_disconnected():
                version = live.current()[0]
                if version != sent:
                    sent, quiet = version, 0.0
                    yield f"data: {json.dumps(live_payload(), ensure_ascii=False)}\n\n"
                elif quiet >= KEEPALIVE:
                    quiet = 0.0
                    yield "event: ping\ndata: {}\n\n"
                await asyncio.sleep(0.5)
                quiet += 0.5

        return StreamingResponse(feed(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

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
                                                   confirm_final=payload.get("confirm_final") is True,
                                                   format_target=payload.get("format_target")))

    @app.post("/api/runs/{run_id}/interior-design")
    def interior_design(run_id: str, payload: dict = Body(...), svc: WorkflowService = Depends(service)):
        action = payload["action"]
        return act(svc, run_id, lambda: svc.review_interior_design(
            run_id, payload["gate_id"], payload["expected_sha256"], action,
            spec=payload.get("spec"), answers=payload.get("answers"), feedback=payload.get("feedback")),
            resume=action in ("request-revision", "generate"))

    @app.post("/api/runs/{run_id}/interior-design/reopen")
    def reopen_interior_design(run_id: str, payload: dict = Body(...), svc: WorkflowService = Depends(service)):
        return act(svc, run_id, lambda: svc.reopen_interior_design(
            run_id, payload["acceptance_id"], payload["expected_docx_sha256"]), resume=False)

    @app.get("/api/runs/{run_id}/docx/{build_id}")
    def download_docx(run_id: str, build_id: str, svc: WorkflowService = Depends(service)):
        data, sha = svc.docx_candidate(run_id, build_id)
        with svc.open_run(run_id) as engine:
            state = engine.state()
            version = engine.accepted_version(state)
            candidate_id = None if engine.finalized(state) else build_id
        return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": docx_disposition(data, version, build_id=candidate_id),
                                 "X-Content-SHA256": sha})

    @app.get("/api/works/{work_id}/docx/{publication_id}")
    def download_published_docx(work_id: str, publication_id: str, svc: WorkflowService = Depends(service)):
        library = svc.library(work_id)
        record = library.publication(publication_id)
        if not record["artifact"].endswith("/document.docx"):
            raise ValueError("This publication is not an editable-DOCX delivery.")
        data = library.read(record)
        version = Path(record["artifact"]).parent.name
        return Response(data,
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": docx_disposition(data, version),
                                 "X-Content-SHA256": record["sha256"]})

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

    def viewer_target(state):
        """Presentation scope only; stored gates and their approval bindings stay unchanged."""
        gate = state.get("gate")
        if not gate:
            return None
        chapter_id = gate.get("chapter_id")
        front = next((c for c in state.get("chapters") or [] if c["role"] == "front_matter"), None)
        if not chapter_id or chapter_id == WHOLE or (front and chapter_id == front["chapter_id"]):
            return {"kind": "overview"}
        return {"kind": "chapter", "chapter_id": chapter_id}

    def overview_identity(svc, state, metadata):
        front = next((c for c in state.get("chapters") or [] if c["role"] == "front_matter"), None)
        # Review edits are run-local until confirmation publishes them to the work.
        title = metadata["metadata"].get("title") if metadata else None
        if (state.get("finalized") or state["status"] == "CANCELLED") and not svc._unfinished(state["work_id"]):
            title = svc.get_work(state["work_id"])["title"]
        return {"work_id": state["work_id"], "title": title or svc.get_work(state["work_id"])["title"],
                "source_unit_id": front["chapter_id"] if front else None}

    @app.get("/api/runs/{run_id}/overview")
    def overview(run_id: str, svc: WorkflowService = Depends(service)):
        with svc.open_run(run_id) as engine:
            state = engine.state()
            metadata = engine.metadata_view(state) if state.get("prepared") else None
            editor_run = svc.metadata_editor_run(state["work_id"])
            edit_target = None
            if metadata and editor_run == run_id:
                if svc._unfinished(state["work_id"]) == run_id:
                    if state["status"] != "RUNNING" and engine.summary(state)["engine_current"]:
                        edit_target = "run"
                else:
                    shared = svc.get_work_metadata(state["work_id"])
                    record = svc.work_metadata_version(state["work_id"], shared["record_revision"])
                    if record["preparation"]["current_revision"] is not None:
                        metadata = {**shared, "locked": metadata["locked"], "unknown": [], "stale": [],
                                    "source_differences": []}
                        edit_target = "work"
            identity = overview_identity(svc, state, metadata)
            source_id = identity["source_unit_id"]
            analysis = engine.analysis_handoff(state) if hasattr(engine, "analysis_handoff") else None
            return {**identity, "prepared": bool(state.get("prepared")),
                    "metadata": metadata,
                    "metadata_edit": {"target": edit_target, "run_id": editor_run},
                    "analysis": ({key: analysis[key] for key in (
                        "analysis_id", "approval_status", "qualifications", "coverage_verification",
                        "current_text_matches_source")} | {
                            "subject_proposals": analysis.get("subject_proposals"),
                            "documents": documents(engine, analysis["artifacts"].values())} if analysis else None),
                    "metadata_fields": svc.metadata_fields(),
                    "source": chapter_content(engine, state, source_id) if source_id else None}

    def pass_keys(state):
        """Chosen passes (e.g. editing) by key "<number>-<stage>", so a repeated pass gets its own entry."""
        titles = {o["stage"]: o["title"] for s in state["definition"].get("stages", []) for o in s.get("options", [])}
        return {f"{p['number']}-{p['stage']}": {"stage": p["stage"], "title": f"Pass {p['number']} · "
                                                f"{titles.get(p['stage'], p['stage'])}"} for p in state.get("passes") or []}

    def chapter_records(engine, state):
        """Per-stage (or per-pass) iteration records, including stages and passes that already finished."""
        default = (engine.iterating_stage(state) or {}).get("id")
        groups = dict(state.get("stage_iterations") or {})
        passes = state.get("passes") or []
        for record in passes:
            if "iterations" in record:  # Kept with the pass when it was accepted.
                groups[f"{record['number']}-{record['stage']}"] = record["iterations"]
        current = f"{passes[-1]['number']}-{passes[-1]['stage']}" if passes and "iterations" not in passes[-1] else None
        for item in state.get("iterations") or []:
            key = current or item.get("stage") or default
            groups.setdefault(key, [])
            if item not in groups[key]:
                groups[key].append(item)
        return groups

    def approved_sheet_receipts(state):
        """Closure receipts, not workspace files, establish which sheet revisions were approved."""
        starts = {p["receipt_id"]: p for p in state.get("passes") or []}
        current_pass = None
        result = []
        for receipt in state.get("receipts") or []:
            current_pass = starts.get(receipt["id"], current_pass)
            gate, parsed = receipt["gate"], receipt["parsed"]
            if gate.get("sheet") and (parsed["type"] == "final-closure" or parsed.get("implied_closure")):
                number = current_pass["number"] if current_pass and current_pass["stage"] == gate["stage"] else None
                result.append((receipt, number))
        return list(reversed(result))

    def approved_sheet_summary(engine, state, receipt, pass_number):
        gate = receipt["gate"]
        snapshot = gate["sheet"]
        sheet = json.loads(engine.store.content(snapshot))
        chapter_id = gate.get("chapter_id")
        unit = next((c for c in state.get("chapters") or [] if c["chapter_id"] == chapter_id), None)
        scope = ("Whole book" if chapter_id == WHOLE else "Overview"
                 if not chapter_id or (unit and unit.get("role") == "front_matter")
                 else (unit or {}).get("title") or chapter_id)
        stages = {s["id"]: s.get("title") or s["id"] for s in state["definition"]["stages"]}
        stages.update({o["stage"]: o["title"] for s in state["definition"]["stages"] for o in s.get("options", [])
                       if o.get("stage")})
        superseded = any(receipt["id"] in r.get("superseded_receipt_ids", []) for r in state.get("restarts") or [])
        return {"receipt_id": receipt["id"], "sheet_id": sheet["sheet_id"], "revision": sheet["revision"],
                "title": sheet["title"], "sha256": snapshot["sha256"], "created_at": receipt["created_at"],
                "decision_source": receipt["decision_source"], "kind": gate["kind"], "stage": gate["stage"],
                "stage_title": stages.get(gate["stage"], gate["stage"]), "chapter_id": chapter_id, "scope": scope,
                "pass_number": pass_number, "attempt": gate.get("attempt"), "superseded": superseded,
                "implied_closure": bool(receipt["parsed"].get("implied_closure"))}

    @app.get("/api/runs/{run_id}/approved-sheets")
    def approved_sheets(run_id: str, svc: WorkflowService = Depends(service)):
        with svc.open_run(run_id) as engine:
            state = engine.state()
            return [approved_sheet_summary(engine, state, receipt, number)
                    for receipt, number in approved_sheet_receipts(state)]

    @app.get("/api/runs/{run_id}/approved-sheets/{receipt_id}.md")
    def download_approved_sheet(run_id: str, receipt_id: str, svc: WorkflowService = Depends(service)):
        with svc.open_run(run_id) as engine:
            state = engine.state()
            selected = next(((r, n) for r, n in approved_sheet_receipts(state) if r["id"] == receipt_id), None)
            if selected is None:
                raise HTTPException(404, "Unknown approved sheet.")
            receipt, number = selected
            gate = receipt["gate"]
            summary = approved_sheet_summary(engine, state, receipt, number)
            binding = gate.get("binding")
            if binding and binding["path"].lower().endswith(".md"):
                # Download the exact approved document, never its evolving workspace copy.
                data = engine.store.content(binding)
            else:
                sheet = json.loads(engine.store.content(gate["sheet"]))
                decisions = {d["id"]: d["label"] for d in sheet["decisions"]}
                dispositions = {d["item_id"]: d for d in receipt["parsed"].get("dispositions", [])}
                lines = [f"# {sheet['title']}", "", f"Sheet: {sheet['sheet_id']}", f"Revision: {sheet['revision']}",
                         f"Approved: {receipt['created_at']}", f"Decision source: {receipt['decision_source']}",
                         f"Scope: {summary['scope']}", f"Stage: {summary['stage_title']}",
                         f"Approval receipt: {receipt['id']}", f"Sheet SHA-256: {summary['sha256']}", ""]
                if summary["pass_number"] is not None:
                    lines.extend([f"Pass: {summary['pass_number']}", ""])
                if summary["superseded"]:
                    lines.extend(["> Superseded by a restart. Historical reference only.", ""])
                for item in sheet["items"]:
                    lines.extend([f"## {item['id']}: {item['summary']}", ""])
                    for row in item["details"]:
                        lines.extend([f"### {row['label']}", "", row["value"], ""])
                    response = dispositions.get(item["id"]) or item.get("response") or {}
                    decision = response.get("decision")
                    lines.extend([f"Recorded decision: {decisions.get(decision, decision or 'See closure receipt')}", ""])
                    if response.get("note"):
                        lines.extend([response["note"], ""])
                lines.extend(["## Closure receipt", "", receipt["text"], ""])
                data = "\n".join(lines).encode("utf-8")
            name = re.sub(r"[^A-Za-z0-9_.-]", "_",
                          f"{summary['sheet_id']}-r{summary['revision']}-{receipt_id[:8]}")[:150] + ".md"
            return Response(data, media_type="text/markdown; charset=utf-8",
                            headers={"Content-Disposition": f'attachment; filename="{name}"',
                                     "X-Content-SHA256": digest(data)})

    @app.get("/api/runs/{run_id}/chapters")
    def chapters(run_id: str, svc: WorkflowService = Depends(service)):
        with svc.open_run(run_id) as engine:
            state = engine.state()
            groups = chapter_records(engine, state)
            keys = pass_keys(state)
            stages = [s for s in engine.stage_ids(state) + list(keys) if s in groups] if groups else []
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
            metadata = engine.metadata_view(state) if state.get("prepared") else None
            overview = overview_identity(svc, state, metadata)
            overview["outputs"] = next((c["outputs"] for c in result if c["role"] == "front_matter"), {})
            body = [c for c in result if c["role"] != "front_matter"]
            number = 0
            for record in body:
                if record["role"] in ("chapter", "standalone"):
                    number += 1
                    record["display_number"] = number
                else:
                    record["display_number"] = None
            return {"prepared": bool(state.get("prepared")), "stages": stages, "chapters": body,
                    "overview": overview,
                    "stage_info": {key: keys[key] for key in stages if key in keys},
                    "whole_book": {stage: next((i["status"] for i in groups[stage] if i["chapter_id"] == WHOLE), None)
                                   for stage in stages}}

    @app.get("/api/runs/{run_id}/chapters/{chapter_id}")
    def chapter(run_id: str, chapter_id: str, svc: WorkflowService = Depends(service)):
        with svc.open_run(run_id) as engine:
            return chapter_content(engine, engine.state(), chapter_id)

    def chapter_content(engine, state, chapter_id):
        if not state.get("prepared"):
            raise HTTPException(409, "Chapters are available after preparation completes.")
        record = next((c for c in state["chapters"] if c["chapter_id"] == chapter_id), None)
        if record is None:
            raise HTTPException(404, "Unknown chapter.")
        prepared = engine.store.content(state["prepared"]["files"][record["path"]]).decode("utf-8")
        outputs = []
        if state.get("manuscript"):
            # Editing works on one text: show it as it stands now, beside the original, once a pass changed it.
            current = engine.file(state["manuscript"][chapter_id]).read_bytes()
            if current.decode("utf-8") != prepared:
                outputs.append({"stage": "current", "title": "Edited text", "attempt": None,
                                "sha256": digest(current), "text": current.decode("utf-8")})
        else:
            for stage, items in chapter_records(engine, state).items():
                item = next((i for i in items if i["chapter_id"] == chapter_id), None)
                if item and item["status"] == "completed" and item.get("output"):
                    outputs.append({"stage": stage, "attempt": item["attempt"], "sha256": item["output"]["sha256"],
                                    "text": engine.store.content(item["output"]).decode("utf-8"),
                                    "consistency_changes": item["output"].get("consistency_changes", [])})
        map_path = engine.workspace / "translation" / "maps" / f"{chapter_id}.json"
        passage_map = json.loads(map_path.read_text(encoding="utf-8")) if map_path.is_file() else None
        reviews = []
        if record["role"] == "front_matter":
            if state.get("metadata_approval"):
                reviews.append({"kind": "metadata_review", "record_revision": state["metadata_approval"]["record_revision"],
                                "decision_source": state["metadata_approval"]["decision_source"], "documents": []})
            for kind, approval in (state.get("front_matter_approvals") or {}).items():
                reviews.append({"kind": kind, "created_at": approval["created_at"],
                                "decision_source": approval["decision_source"],
                                "current_documents": current_documents(engine, state, approval["documents"]),
                                "documents": documents(engine, approval["documents"])})
        return {"chapter": {k: record.get(k) for k in ("chapter_id", "order", "title", "role", "sha256", "supplied_title")},
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
