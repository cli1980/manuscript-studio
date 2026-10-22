import hmac
import json
import secrets
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import TypeAdapter

from .models import JudgmentCreate, Login, ReviewerLabel, Submit
from .repository import DataError, SKILLS
from .workspace import Workspace

MAX_BODY = 1024 * 1024
COOKIE = "eval_session"
STATIC = Path(__file__).resolve().parent / "static"
HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    ),
}


class Boundary:
    def __init__(self, app, origin):
        self.app = app
        self.origin = origin
        self.host = urlsplit(origin).netloc

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def secured(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [
                    (key.lower().encode(), value.encode()) for key, value in HEADERS.items()
                ]
            await send(message)

        async def reject(status, message):
            response = JSONResponse({"detail": message}, status_code=status)
            await response(scope, receive, secured)

        headers = {}
        for key, value in scope["headers"]:
            key = key.decode("latin-1").lower()
            if key in {"host", "origin", "content-length"} and key in headers:
                await reject(400, "Duplicate security header.")
                return
            headers[key] = value.decode("latin-1")
        if headers.get("host") != self.host:
            await reject(403, "Untrusted request host.")
            return
        if "origin" in headers and headers["origin"] != self.origin:
            await reject(403, "Cross-origin requests are not allowed.")
            return
        if scope["method"] not in {"GET", "HEAD"}:
            if headers.get("origin") != self.origin:
                await reject(403, "A matching Origin header is required.")
                return
            if headers.get("content-type", "").split(";")[0].strip() != "application/json":
                await reject(415, "Use application/json.")
                return
            try:
                declared = int(headers.get("content-length", "0"))
            except ValueError:
                await reject(400, "Invalid request size.")
                return
            if declared < 0 or declared > MAX_BODY:
                await reject(413, "Request body is too large.")
                return
            chunks = []
            total = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > MAX_BODY:
                    await reject(413, "Request body is too large.")
                    return
                chunks.append(chunk)
                if not message.get("more_body"):
                    break
            body = b"".join(chunks)
            delivered = False

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            await self.app(scope, replay, secured)
        else:
            await self.app(scope, receive, secured)


def create_app(data_root, origin="http://127.0.0.1:8765", *, reviewer_label=None):
    fixed_reviewer = TypeAdapter(ReviewerLabel).validate_python(reviewer_label) if reviewer_label is not None else None
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.path
        or parsed.query or parsed.fragment or parsed.username or parsed.password
    ):
        raise ValueError("Origin must contain only scheme, host, and optional port.")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Network-facing origins must use HTTPS.")
    workspace = Workspace(data_root)
    repository = workspace.repository

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            workspace.close()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.add_middleware(Boundary, origin=origin)
    app.state.access_key = secrets.token_urlsafe(32)
    app.state.repository = repository
    app.state.workspace = workspace
    sessions = {}
    attempts = {}

    def session(request, write=False):
        token = request.cookies.get(COOKIE, "")
        current = sessions.get(token)
        if current is None:
            raise HTTPException(401, "Sign in with the current startup key.")
        if write and not hmac.compare_digest(
            request.headers.get("x-csrf-token", "").encode(), current["csrf"].encode()
        ):
            raise HTTPException(403, "Missing or invalid CSRF token.")
        return current

    @app.exception_handler(DataError)
    async def data_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        errors = [{"field": ".".join(map(str, item["loc"])), "message": item["msg"]} for item in exc.errors()]
        return JSONResponse({"detail": "Check the submitted fields.", "errors": errors}, status_code=422)

    @app.exception_handler(OSError)
    async def filesystem_error(request, exc):
        return JSONResponse({"detail": "The data operation failed. No filesystem details are exposed."}, status_code=500)

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/static/app.js")
    def javascript():
        return FileResponse(STATIC / "app.js", media_type="text/javascript")

    @app.get("/static/style.css")
    def stylesheet():
        return FileResponse(STATIC / "style.css", media_type="text/css")

    @app.post("/auth/login")
    async def login(request: Request):
        nonlocal fixed_reviewer
        peer = request.client.host if request.client else "unknown"
        now = time.monotonic()
        if peer not in attempts:
            if len(attempts) >= 256:
                attempts.pop(next(iter(attempts)))
            attempts[peer] = deque()
        recent = attempts[peer]
        while recent and recent[0] < now - 60:
            recent.popleft()
        if len(recent) >= 20:
            raise HTTPException(429, "Too many attempts. Try again in one minute.")
        try:
            data = Login.model_validate_json(await request.body())
        except ValueError:
            recent.append(now)
            raise HTTPException(422, "Provide the access key and a nonblank reviewer label of at most 500 characters.")
        if not hmac.compare_digest(data.key.encode("utf-8"), app.state.access_key.encode()):
            recent.append(now)
            raise HTTPException(401, "Invalid access key.")
        if fixed_reviewer is not None and data.rater_id not in (None, fixed_reviewer):
            recent.append(now)
            raise HTTPException(422, "This server is already bound to a judge. Restart the server to change the reviewer label.")
        rater_id = fixed_reviewer if fixed_reviewer is not None else data.rater_id
        if rater_id is None:
            recent.append(now)
            raise HTTPException(422, "A reviewer label is required to sign in.")
        fixed_reviewer = rater_id
        recent.clear()
        sessions.pop(request.cookies.get(COOKIE), None)
        if len(sessions) >= 256:
            sessions.pop(next(iter(sessions)))
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        sessions[token] = {"csrf": csrf}
        response = JSONResponse({"csrf_token": csrf, "rater_id": rater_id})
        response.set_cookie(COOKIE, token, httponly=True, secure=parsed.scheme == "https", samesite="strict", path="/")
        return response

    @app.get("/auth/config")
    def login_configuration():
        return {"reviewer_label_required": fixed_reviewer is None}

    @app.get("/auth/session")
    def current_session(request: Request):
        current = session(request)
        return {"csrf_token": current["csrf"], "rater_id": fixed_reviewer}

    @app.post("/auth/logout")
    def logout(request: Request):
        session(request, write=True)
        sessions.pop(request.cookies.get(COOKIE), None)
        response = JSONResponse({"ok": True})
        response.delete_cookie(COOKIE, path="/", secure=parsed.scheme == "https", httponly=True, samesite="strict")
        return response

    @app.get("/api/skills")
    def skills(request: Request):
        session(request)
        return [{"id": key, "label": label, "supported": key == "literary-translation"} for key, label in SKILLS.items()]

    @app.get("/api/workspace")
    def workspace_status(request: Request):
        session(request)
        return workspace.status()

    @app.post("/api/workspace/submit")
    async def submit_workspace(request: Request):
        session(request, write=True)
        try:
            data = Submit.model_validate_json(await request.body())
        except ValueError:
            raise HTTPException(422, "Review the current workspace before submitting.")
        return workspace.submit(data.version)

    @app.get("/api/rubrics")
    def rubrics(request: Request):
        session(request)
        return repository.rubric_list()

    @app.get("/api/passages")
    def passages(request: Request):
        session(request)
        return [repository.review_source(item) for item in repository.list_passages()]

    @app.get("/api/passages/{passage_id}")
    def passage(request: Request, passage_id: str, revision: int = 1):
        session(request)
        item = repository.get_passage(passage_id, revision)
        return {"metadata": repository.review_source(item["metadata"]), "text": item["text"]}

    @app.get("/api/cases")
    def cases(request: Request, skill: str = "literary-translation"):
        session(request)
        return [repository.review_case_metadata(item) for item in repository.list_cases(skill)]

    @app.get("/api/cases/{case_id}")
    def case(request: Request, case_id: str, candidate_id: str | None = None):
        session(request)
        return repository.get_review_case(case_id, candidate_id)

    @app.post("/api/cases/{case_id}/judgments", status_code=201)
    async def judgment(request: Request, case_id: str):
        session(request, write=True)
        try:
            data = JudgmentCreate.model_validate_json(await request.body())
        except ValueError:
            raise HTTPException(422, "Check assessment fields. Scores must be whole numbers from 1 to 5 or unset.")
        data = data.model_copy(update={
            "candidate_id": repository.resolve_review_id(case_id, "candidate", data.candidate_id),
            "supersedes_judgment_id": repository.resolve_review_id(case_id, "judgment", data.supersedes_judgment_id),
        })
        return repository.review_view(repository.add_judgment(case_id, data, rater_id=fixed_reviewer))

    return app
