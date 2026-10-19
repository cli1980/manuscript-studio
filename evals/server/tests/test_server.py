import contextlib
import io
import json
import os
import shutil
import stat
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from evals.server.app import COOKIE, MAX_BODY, create_app
from evals.server.repository import DataError, plain_path
from evals.server.workspace import snapshot

EVALS = Path(__file__).resolve().parents[2]
ORIGIN = "http://127.0.0.1:8765"
CASE_ID = "zh-en-000001"
PASSAGE_ID = "work-001-passage-001"
RUBRIC = "literary-translation-quality-v1"


def sample_copy(root):
    if root.resolve() == EVALS.resolve():
        raise ValueError("Tests must not write to real evaluation data.")
    for relative in ("cases", "fixtures/manuscripts", "rubrics"):
        shutil.copytree(EVALS / relative, root / relative)
    case_root = root / f"cases/literary-translation/{CASE_ID}"
    case = json.loads((case_root / "case.json").read_text(encoding="utf-8"))
    pending = {
        "judgment_id": f"{CASE_ID}-judgment-001", "case_id": CASE_ID,
        "case_revision": case["revision"], "passage_id": case["passage_id"],
        "source_revision": case["source_revision"], "rater_id": None,
        "rubric_version": None, "status": "pending", "overall_score": None,
        "dimension_scores": {"fidelity": None, "english_naturalness": None, "literary_voice": None},
        "rationale": None, "issues": [],
    }
    (case_root / "judgments.jsonl").write_text(json.dumps(pending) + "\n", encoding="utf-8")


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.source_root = Path(self.temporary.name).resolve() / "evals"
        sample_copy(self.source_root)
        self.app = create_app(self.source_root)
        self.addCleanup(self.app.state.workspace.close)
        self.root = self.app.state.repository.root
        self.client = TestClient(self.app, base_url=ORIGIN, headers={"Origin": ORIGIN})
        self.addCleanup(self.client.close)
        self.login()

    def login(self, rater_id="test-reviewer"):
        response = self.client.post("/auth/login", json={"key": self.app.state.access_key, "rater_id": rater_id})
        self.assertEqual(response.status_code, 200, response.text)
        self.csrf = response.json()["csrf_token"]
        self.headers = {"X-CSRF-Token": self.csrf}
        return response

    def get_case(self):
        response = self.client.get(f"/api/cases/{CASE_ID}")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def judgment(self, **changes):
        case = self.get_case()
        body = {
            "version": case["version"],
            "status": "complete", "overall_score": 4,
            "dimension_scores": {"fidelity": 4, "english_naturalness": 4, "literary_voice": 3},
            "rationale": "Test assessment on a disposable copy, not human ground truth.",
            "issues": [],
        }
        body.update(changes)
        return self.client.post(f"/api/cases/{CASE_ID}/judgments", json=body, headers=self.headers)

    def test_sample_read_is_exact_and_has_no_generated_score(self):
        case = self.get_case()
        self.assertEqual(case["source"]["text"], (EVALS / "fixtures/manuscripts/work-001/passage-001/source.zh.txt").read_bytes().decode("utf-8"))
        self.assertEqual(case["translation"], (EVALS / f"cases/literary-translation/{CASE_ID}/translation.en.txt").read_bytes().decode("utf-8"))
        self.assertIsNone(case["judgments"][0]["overall_score"])
        self.assertEqual(case["judgments"][0]["status"], "pending")
        self.assertIn("was nor in the least", case["translation"])

    def test_authentication_required_on_every_data_route(self):
        self.client.cookies.clear()
        for route in ("/api/skills", "/api/passages", f"/api/passages/{PASSAGE_ID}", "/api/cases", f"/api/cases/{CASE_ID}", "/api/rubrics", "/api/workspace"):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 401)
                self.assertNotIn("Braving", response.text)
        self.assertEqual(self.client.post(f"/api/cases/{CASE_ID}/judgments", json={}, headers=self.headers).status_code, 401)
        self.assertEqual(self.client.post("/api/workspace/submit", json={}, headers=self.headers).status_code, 401)

    def test_key_and_sessions_are_invalid_after_restart(self):
        token = self.client.cookies.get(COOKIE)
        old_key = self.app.state.access_key
        other = create_app(self.source_root)
        with TestClient(other, base_url=ORIGIN, headers={"Origin": ORIGIN}) as client:
            client.cookies.set(COOKIE, token)
            self.assertEqual(client.get("/api/cases").status_code, 401)
            self.assertEqual(client.post("/auth/login", json={"key": old_key, "rater_id": "test-reviewer"}).status_code, 401)
            self.assertNotEqual(old_key, other.state.access_key)

    def test_cookie_flags_logout_and_security_headers(self):
        response = self.login()
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=strict", cookie)
        page = self.client.get("/")
        self.assertEqual(page.headers["cache-control"], "no-store")
        self.assertIn("frame-ancestors 'none'", page.headers["content-security-policy"])
        self.assertEqual(page.headers["x-content-type-options"], "nosniff")
        self.assertNotIn(self.app.state.access_key, page.text)
        self.assertEqual(self.client.post("/auth/logout", json={}, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get("/api/cases").status_code, 401)

    def workspace_status(self):
        response = self.client.get("/api/workspace")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_first_successful_signin_binds_the_judge_until_restart(self):
        app = create_app(self.source_root)
        with TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN}) as client:
            self.assertEqual(client.get("/auth/config").json(), {"reviewer_label_required": True})
            self.assertEqual(client.post("/auth/login", json={"key": "wrong", "rater_id": "wrong-judge"}).status_code, 401)
            for label in (None, "", " \t\n", "x" * 501):
                self.assertEqual(client.post("/auth/login", json={"key": app.state.access_key, "rater_id": label}).status_code, 422)
            self.assertEqual(client.get("/auth/config").json(), {"reviewer_label_required": True})
            login = client.post("/auth/login", json={"key": app.state.access_key, "rater_id": "judge-01"})
            self.assertEqual(login.status_code, 200)
            self.assertEqual(client.get("/auth/config").json(), {"reviewer_label_required": False})
            client.post("/auth/logout", json={}, headers={"X-CSRF-Token": login.json()["csrf_token"]}).raise_for_status()
            self.assertEqual(client.post("/auth/login", json={"key": app.state.access_key, "rater_id": "judge-02"}).status_code, 422)
            self.assertEqual(client.post("/auth/login", json={"key": app.state.access_key}).json()["rater_id"], "judge-01")

    def test_startup_label_allows_key_only_login_and_cannot_be_overridden(self):
        app = create_app(self.source_root, reviewer_label="  configured-judge  ")
        with TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN}) as client:
            self.assertEqual(client.get("/auth/config").json(), {"reviewer_label_required": False})
            self.assertEqual(client.post("/auth/login", json={"key": "incorrect"}).status_code, 401)
            auth = client.post("/auth/login", json={"key": app.state.access_key})
            self.assertEqual(auth.status_code, 200)
            self.assertEqual(auth.json()["rater_id"], "configured-judge")
            overridden = client.post("/auth/login", json={"key": app.state.access_key, "rater_id": "another-judge"})
            self.assertEqual(overridden.status_code, 422)
            self.assertEqual(client.get("/auth/session").json()["rater_id"], "configured-judge")
            case = client.get(f"/api/cases/{CASE_ID}").json()
            saved = client.post(f"/api/cases/{CASE_ID}/judgments",
                                json={"version": case["version"], "overall_score": 4, "status": "complete"},
                                headers={"X-CSRF-Token": auth.json()["csrf_token"]})
            self.assertEqual(saved.status_code, 201, saved.text)
            self.assertEqual(saved.json()["judgments"][-1]["rater_id"], "configured-judge")

    def test_invalid_startup_labels_are_rejected(self):
        for label in ("", " \t\n ", "x" * 501):
            with self.subTest(length=len(label)), self.assertRaises(ValueError):
                create_app(self.source_root, reviewer_label=label)

    def test_cli_passes_normalized_startup_label(self):
        from evals.server import __main__ as cli
        fake = SimpleNamespace(state=SimpleNamespace(access_key="test-key"))
        output = io.StringIO()
        with patch.object(cli, "create_app", return_value=fake) as create:
            with patch.object(cli.uvicorn, "run") as run, contextlib.redirect_stdout(output):
                cli.main(["--data-dir", str(self.source_root), "--reviewer-label", "  judge-01  "])
        self.assertEqual(create.call_args.kwargs["reviewer_label"], "judge-01")
        self.assertIs(run.call_args.args[0], fake)
        self.assertIn("Reviewer label: judge-01", output.getvalue())

    def test_session_label_is_trimmed_preserved_and_stamped_on_all_saves(self):
        auth = self.login("  test-reviewer  ").json()
        self.assertEqual(auth["rater_id"], "test-reviewer")
        self.assertEqual(self.client.get("/auth/session").json()["rater_id"], "test-reviewer")
        first = self.judgment(status="pending", overall_score=None)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["judgments"][-1]["rater_id"], "test-reviewer")
        second = self.judgment(supersedes_judgment_id=first.json()["judgments"][-1]["judgment_id"])
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.json()["judgments"][-1]["rater_id"], "test-reviewer")
        self.assertEqual(self.judgment(rater_id="someone-else").status_code, 422)
        self.assertEqual(self.client.get("/auth/session").json()["rater_id"], "test-reviewer")

    def test_multiple_browser_sessions_share_one_judge_and_logout_is_local(self):
        first = self.judgment()
        first_id = first.json()["judgments"][-1]["judgment_id"]
        other = TestClient(self.app, base_url=ORIGIN, headers={"Origin": ORIGIN})
        self.addCleanup(other.close)
        rejected = other.post("/auth/login", json={
            "key": self.app.state.access_key, "rater_id": "second-reviewer",
        })
        self.assertEqual(rejected.status_code, 422)
        auth = other.post("/auth/login", json={"key": self.app.state.access_key}).json()
        headers = {"X-CSRF-Token": auth["csrf_token"]}
        body = {"version": self.get_case()["version"], "overall_score": 3, "status": "complete"}
        created = other.post(f"/api/cases/{CASE_ID}/judgments",
                             json={**body, "supersedes_judgment_id": first_id}, headers=headers)
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["judgments"][-1]["rater_id"], "test-reviewer")
        self.assertEqual(self.client.get("/auth/session").json()["rater_id"], "test-reviewer")
        self.assertEqual(other.get("/auth/session").json()["rater_id"], "test-reviewer")
        self.client.post("/auth/logout", json={}, headers=self.headers).raise_for_status()
        self.assertEqual(self.client.get("/auth/session").status_code, 401)
        self.assertEqual(other.get("/auth/session").status_code, 200)

    def test_reauthentication_rotates_session_but_keeps_the_same_judge(self):
        token, csrf = self.client.cookies.get(COOKIE), self.csrf
        self.assertEqual(self.client.post("/auth/login", json={
            "key": self.app.state.access_key, "rater_id": "new-reviewer",
        }).status_code, 422)
        self.login()
        self.assertNotEqual(token, self.client.cookies.get(COOKIE))
        other = TestClient(self.app, base_url=ORIGIN, headers={"Origin": ORIGIN})
        self.addCleanup(other.close)
        other.cookies.set(COOKIE, token)
        self.assertEqual(other.get("/auth/session").status_code, 401)
        self.assertEqual(self.client.post(f"/api/cases/{CASE_ID}/judgments", json={},
                                         headers={"X-CSRF-Token": csrf}).status_code, 403)
        self.assertEqual(self.judgment().json()["judgments"][-1]["rater_id"], "test-reviewer")

    def test_unchanged_reviews_do_not_add_history_or_pending_changes(self):
        first = self.judgment().json()
        saved = first["judgments"][-1]
        self.assertEqual(self.submit().status_code, 200)
        path = self.root / f"cases/literary-translation/{CASE_ID}/judgments.jsonl"
        before, modified = path.read_bytes(), path.stat().st_mtime_ns
        for supersedes in (saved["judgment_id"], None):
            repeated = self.judgment(supersedes_judgment_id=supersedes)
            self.assertEqual(repeated.status_code, 201)
            self.assertEqual(repeated.json()["version"], first["version"])
            self.assertEqual(repeated.json()["judgments"], first["judgments"])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(path.stat().st_mtime_ns, modified)
        self.assertEqual(self.workspace_status()["pending_files"], 0)
        edited = self.judgment(rationale="A revised comment.").json()
        self.assertEqual(len(edited["judgments"]), len(first["judgments"]) + 1)
        self.assertEqual(edited["judgments"][-1]["supersedes_judgment_id"], saved["judgment_id"])

    def test_unchanged_drafts_are_noops_but_completion_is_a_change(self):
        first = self.judgment(status="pending").json()
        self.assertEqual(self.judgment(status="pending").json()["version"], first["version"])
        completed = self.judgment().json()
        self.assertEqual(len(completed["judgments"]), len(first["judgments"]) + 1)
        self.assertEqual(completed["judgments"][-1]["status"], "complete")

    def submit(self, version=None):
        return self.client.post("/api/workspace/submit", json={
            "version": version or self.workspace_status()["version"],
        }, headers=self.headers)

    def test_saved_judgment_only_reaches_original_on_submit(self):
        workspace = self.app.state.workspace
        baseline = snapshot(workspace.source)
        self.assertNotEqual(self.root, self.source_root)
        self.assertEqual(self.judgment().status_code, 201)
        self.assertEqual(snapshot(workspace.source), baseline)
        status = self.workspace_status()
        self.assertEqual(status["pending_files"], 1)
        self.assertEqual(status["cases"], [CASE_ID])
        response = self.submit()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["pending_files"], 0)
        published = workspace.source.get_case(CASE_ID)
        self.assertEqual(published["judgments"][-1]["overall_score"], 4)
        self.assertEqual(published["judgments"], self.get_case()["judgments"])
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(len(workspace.source.get_case(CASE_ID)["judgments"]), 2)

    def test_creation_and_metadata_routes_are_removed(self):
        workspace = self.app.state.workspace
        baseline = snapshot(workspace.source)
        for method, route in (
            ("POST", "/api/passages"), ("POST", "/api/cases"),
            ("PATCH", f"/api/cases/{CASE_ID}"), ("PUT", f"/api/cases/{CASE_ID}"),
            ("PATCH", f"/api/passages/{PASSAGE_ID}"),
        ):
            with self.subTest(method=method, route=route):
                response = self.client.request(method, route, json={}, headers=self.headers)
                self.assertEqual(response.status_code, 405, response.text)
        self.assertEqual(snapshot(workspace.source), baseline)
        self.assertEqual(self.workspace_status()["pending_files"], 0)

    def test_submit_requires_csrf_and_current_workspace_version(self):
        old = self.workspace_status()["version"]
        self.assertEqual(self.judgment().status_code, 201)
        response = self.client.post("/api/workspace/submit", json={"version": old})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.submit(old).status_code, 409)
        self.assertEqual(len(self.app.state.workspace.source.get_case(CASE_ID)["judgments"]), 1)

    def test_external_source_changes_block_submit_and_keep_drafts(self):
        self.assertEqual(self.judgment().status_code, 201)
        path = self.source_root / f"cases/literary-translation/{CASE_ID}/translation.en.txt"
        path.write_bytes(path.read_bytes() + b"\nExternal edit")
        before = snapshot(self.app.state.workspace.source)
        response = self.submit()
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(snapshot(self.app.state.workspace.source), before)
        self.assertEqual(self.get_case()["judgments"][-1]["overall_score"], 4)
        self.assertGreater(self.workspace_status()["pending_files"], 0)

    def test_restart_discards_unsubmitted_changes(self):
        self.assertEqual(self.judgment().status_code, 201)
        old_root = self.root
        self.app.state.workspace.close()
        self.assertFalse(old_root.exists())
        restarted = create_app(self.source_root)
        try:
            self.assertEqual(restarted.state.workspace.status()["pending_files"], 0)
            self.assertEqual(len(restarted.state.repository.get_case(CASE_ID)["judgments"]), 1)
        finally:
            restarted.state.workspace.close()

    def test_submit_rolls_back_partial_writes_and_can_retry(self):
        second_id = "zh-en-000002"
        target = self.source_root / f"cases/literary-translation/{second_id}"
        shutil.copytree(self.source_root / f"cases/literary-translation/{CASE_ID}", target)
        metadata = json.loads((target / "case.json").read_text(encoding="utf-8"))
        metadata["case_id"] = second_id
        (target / "case.json").write_text(json.dumps(metadata), encoding="utf-8")
        (target / "judgments.jsonl").write_bytes(b"")
        self.app.state.workspace.close()
        self.app = create_app(self.source_root)
        self.addCleanup(self.app.state.workspace.close)
        self.root = self.app.state.repository.root
        self.client.close()
        self.client = TestClient(self.app, base_url=ORIGIN, headers={"Origin": ORIGIN})
        self.addCleanup(self.client.close)
        self.login()
        workspace = self.app.state.workspace
        baseline = snapshot(workspace.source)
        case = self.client.get(f"/api/cases/{second_id}").json()
        response = self.client.post(f"/api/cases/{second_id}/judgments", json={
            "version": case["version"],
            "overall_score": 3, "status": "complete",
        }, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.judgment().status_code, 201)
        atomic = workspace.source.atomic
        calls = 0

        def fail_second(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("Simulated publication failure")
            return atomic(*args)

        with patch.object(workspace.source, "atomic", side_effect=fail_second):
            self.assertEqual(self.submit().status_code, 500)
        self.assertEqual(snapshot(workspace.source), baseline)
        self.assertEqual(self.workspace_status()["pending_files"], 2)
        self.assertEqual(self.submit().status_code, 200)

    def test_failed_submission_preserves_drafts(self):
        workspace = self.app.state.workspace
        baseline = snapshot(workspace.source)
        self.assertEqual(self.judgment().status_code, 201)
        with patch.object(workspace.source, "atomic", side_effect=OSError("Cannot publish rating")):
            self.assertEqual(self.submit().status_code, 500)
        self.assertEqual(snapshot(workspace.source), baseline)
        self.assertEqual(self.workspace_status()["pending_files"], 1)

    def test_submit_rejects_all_nonjudgment_edits(self):
        workspace = self.app.state.workspace
        baseline = snapshot(workspace.source)
        for path in (
            self.root / f"cases/literary-translation/{CASE_ID}/translation.en.txt",
            self.root / "fixtures/manuscripts/work-001/passage-001/source.zh.txt",
            self.root / f"rubrics/{RUBRIC}.json",
            self.root / f"cases/literary-translation/{CASE_ID}/case.json",
            self.root / "fixtures/manuscripts/work-001/passage-001/passage.json",
        ):
            with self.subTest(path=path):
                old = path.read_bytes()
                path.write_bytes(old + b" ")
                response = self.client.get("/api/workspace")
                self.assertEqual(response.status_code, 422)
                path.write_bytes(old)
                self.assertEqual(snapshot(workspace.source), baseline)

    def test_submit_rejects_rewriting_existing_judgment_history(self):
        path = self.root / f"cases/literary-translation/{CASE_ID}/judgments.jsonl"
        prior = json.loads(path.read_text(encoding="utf-8"))
        prior["overall_score"] = 5
        path.write_text(json.dumps(prior) + "\n", encoding="utf-8")
        self.assertEqual(self.client.get("/api/workspace").status_code, 422)
        self.assertIsNone(self.app.state.workspace.source.get_case(CASE_ID)["judgments"][0]["overall_score"])

    def test_repository_write_boundary_rejects_metadata(self):
        repository = self.app.state.repository
        for path, area in (
            (self.root / f"cases/literary-translation/{CASE_ID}/case.json", repository.cases),
            (self.root / "fixtures/manuscripts/work-001/passage-001/source.zh.txt", repository.passages),
        ):
            before = path.read_bytes()
            with self.assertRaises(DataError):
                repository.atomic(path, b"modified", area)
            self.assertEqual(path.read_bytes(), before)

    def test_https_cookie_is_secure(self):
        app = create_app(self.root, "https://reviews.example.test")
        with TestClient(app, base_url="https://reviews.example.test", headers={"Origin": "https://reviews.example.test"}) as client:
            response = client.post("/auth/login", json={"key": app.state.access_key, "rater_id": "test-reviewer"})
            self.assertIn("Secure", response.headers["set-cookie"])
        with self.assertRaises(ValueError):
            create_app(self.root, "http://reviews.example.test")

    def test_bad_host_origin_and_csrf_are_rejected(self):
        self.assertEqual(self.client.get("/api/cases", headers={"Host": "attacker.test"}).status_code, 403)
        self.assertEqual(self.client.get("/api/cases", headers={"Origin": "https://attacker.test"}).status_code, 403)
        self.assertEqual(self.client.post(f"/api/cases/{CASE_ID}/judgments", json={}).status_code, 403)
        self.assertEqual(self.client.post(f"/api/cases/{CASE_ID}/judgments", json={}, headers={"X-CSRF-Token": "wrong"}).status_code, 403)
        with TestClient(self.app, base_url=ORIGIN) as client:
            self.assertEqual(client.post("/auth/login", json={"key": self.app.state.access_key, "rater_id": "test-reviewer"}).status_code, 403)

    def test_oversized_and_non_json_requests_are_rejected(self):
        response = self.client.post("/api/passages", content=b"x" * (MAX_BODY + 1), headers={**self.headers, "Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)
        response = self.client.post("/api/passages", content=b"text", headers=self.headers)
        self.assertEqual(response.status_code, 415)

    def test_chunked_body_limit(self):
        def chunks():
            yield b"x" * (MAX_BODY // 2)
            yield b"x" * MAX_BODY
        response = self.client.post("/api/passages", content=chunks(), headers={**self.headers, "Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)

    def test_login_rate_limit_and_unicode_input(self):
        for _ in range(20):
            self.assertEqual(self.client.post("/auth/login", json={"key": "错误", "rater_id": "test-reviewer"}).status_code, 401)
        self.assertEqual(self.client.post("/auth/login", json={"key": self.app.state.access_key, "rater_id": "test-reviewer"}).status_code, 429)

    def test_no_arbitrary_file_or_execution_endpoints(self):
        for route in ("/docs", "/openapi.json", "/static/app.py", "/api/files", "/api/run", "/.git/config"):
            self.assertEqual(self.client.get(route).status_code, 404, route)
        self.assertEqual(self.client.request("DELETE", f"/api/cases/{CASE_ID}", json={}, headers=self.headers).status_code, 405)

    def test_judgment_edits_preserve_history_and_texts(self):
        before = self.get_case()
        response = self.judgment(supersedes_judgment_id=before["judgments"][0]["judgment_id"])
        self.assertEqual(response.status_code, 201, response.text)
        first = response.json()
        first_id = first["judgments"][-1]["judgment_id"]
        self.assertEqual(first["judgments"][0], before["judgments"][0])
        response = self.judgment(overall_score=3, supersedes_judgment_id=first_id)
        self.assertEqual(response.status_code, 201, response.text)
        final = response.json()
        self.assertEqual([j["overall_score"] for j in final["judgments"]], [None, 4, 3])
        self.assertEqual(final["judgments"][-1]["supersedes_judgment_id"], first_id)
        self.assertEqual(final["source"], before["source"])
        self.assertEqual(final["translation"], before["translation"])
        self.assertEqual(self.judgment(supersedes_judgment_id=first_id).status_code, 409)
        self.assertEqual(final["judgments"][-1]["source_revision"], 1)

    def test_invalid_scores_and_completed_judgments_do_not_write(self):
        before = self.get_case()["version"]
        for score in (0, 6, 2.5, True, "4"):
            with self.subTest(score=score):
                self.assertEqual(self.judgment(overall_score=score).status_code, 422)
        for change in ({"rater_id": None}, {"overall_score": None}, {"rubric_version": "unknown"}):
            self.assertEqual(self.judgment(**change).status_code, 422)
        self.assertEqual(self.get_case()["version"], before)

    def test_pending_judgment_can_have_unset_scores(self):
        response = self.judgment(status="pending", overall_score=None, dimension_scores={})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertIsNone(response.json()["judgments"][-1]["overall_score"])

    def test_stale_versions_and_external_text_edits_conflict(self):
        initial = self.get_case()
        self.assertEqual(self.judgment().status_code, 201)
        self.assertEqual(self.judgment(version=initial["version"]).status_code, 409)
        latest = self.get_case()
        path = self.root / f"cases/literary-translation/{CASE_ID}/translation.en.txt"
        path.write_text(path.read_text(encoding="utf-8") + "\nExternal edit", encoding="utf-8")
        self.assertEqual(self.judgment(version=latest["version"]).status_code, 409)

    def test_scores_and_comments_cannot_alter_case_metadata(self):
        before = self.get_case()
        for extra in (
            {"brief": "Replace instructions"}, {"usage_rights": "permitted"},
            {"translation_origin": "New origin"}, {"case_revision": 999},
            {"source_revision": 999}, {"rubric_version": RUBRIC},
        ):
            with self.subTest(extra=extra):
                self.assertEqual(self.judgment(**extra).status_code, 422)
        self.assertEqual(self.judgment(rationale="My subjective reading of this passage.").status_code, 201)
        self.assertEqual(self.submit().status_code, 200)
        after = self.app.state.workspace.source.get_case(CASE_ID)
        self.assertEqual(before["metadata"], after["metadata"])
        self.assertEqual(before["source"], after["source"])
        self.assertEqual(before["translation"], after["translation"])
        self.assertEqual(after["judgments"][-1]["rubric_version"], RUBRIC)

    def test_completion_requires_unambiguous_maintainer_configured_rubric(self):
        path = self.root / f"rubrics/{RUBRIC}.json"
        rubric = json.loads(path.read_text(encoding="utf-8"))
        rubric["rubric_id"] = "alternative-rubric-v1"
        (self.root / "rubrics/alternative.json").write_text(json.dumps(rubric), encoding="utf-8")
        self.assertIsNone(self.get_case()["rubric"])
        self.assertEqual(self.judgment().status_code, 422)
        metadata_path = self.root / f"cases/literary-translation/{CASE_ID}/case.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["rubric_id"] = RUBRIC
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        self.assertEqual(self.get_case()["rubric"]["rubric_id"], RUBRIC)
        self.assertEqual(self.judgment().status_code, 201)

    def test_version_describes_the_data_returned_during_external_edit(self):
        repository = self.app.state.repository
        read = repository.read
        metadata_path = self.root / f"cases/literary-translation/{CASE_ID}/case.json"
        changed = False

        def edit_after_read(path, area):
            nonlocal changed
            content = read(path, area)
            if path == metadata_path and not changed:
                changed = True
                newer = json.loads(content)
                newer["provenance"]["translation_origin"] = "External edit during read"
                metadata_path.write_text(json.dumps(newer), encoding="utf-8")
            return content

        with patch.object(repository, "read", side_effect=edit_after_read):
            old_response = self.get_case()
        self.assertNotEqual(old_response["version"], self.get_case()["version"])
        self.assertEqual(self.judgment(version=old_response["version"]).status_code, 409)

    def test_rated_brief_cannot_be_overwritten(self):
        self.assertEqual(self.judgment().status_code, 201)
        case = self.get_case()
        response = self.client.patch(f"/api/cases/{CASE_ID}", json={
            "version": case["version"], "brief": "Change the voice", "translation_origin": "user-provided",
            "usage_rights": "pending", "status": "placeholder",
        }, headers=self.headers)
        self.assertEqual(response.status_code, 405)

    def corrupt_reference(self, field, value):
        path = self.root / f"cases/literary-translation/{CASE_ID}/case.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        metadata[field] = value
        path.write_text(json.dumps(metadata), encoding="utf-8")

    def test_stored_traversal_and_absolute_references_are_rejected(self):
        for field, value in (
            ("source_metadata_file", "../../../../README.md"),
            ("source_metadata_file", "/etc/passwd"),
            ("source_metadata_file", "C:/Users/secret.txt"),
            ("source_metadata_file", "../../../server/app.py"),
            ("translation_file", "../../../rubrics/literary-translation-quality-v1.json"),
        ):
            with self.subTest(field=field, value=value):
                self.corrupt_reference(field, value)
                response = self.client.get(f"/api/cases/{CASE_ID}")
                self.assertEqual(response.status_code, 422, response.text)
                self.assertNotIn(str(self.root), response.text)
                sample_copy_path = EVALS / f"cases/literary-translation/{CASE_ID}/case.json"
                shutil.copyfile(sample_copy_path, self.root / f"cases/literary-translation/{CASE_ID}/case.json")

    def test_ids_and_unknown_fields_cannot_choose_write_paths(self):
        self.assertEqual(self.judgment(source_file="../../secret").status_code, 422)
        self.assertEqual(self.judgment(supersedes_judgment_id="../server").status_code, 422)
        self.assertEqual(self.client.get("/api/cases", params={"skill": "../server"}).status_code, 404)

    def test_hard_link_is_rejected_without_reading_target(self):
        original = self.root / f"cases/literary-translation/{CASE_ID}/translation.en.txt"
        outside = self.source_root.parent / "private.txt"
        outside.write_text("PRIVATE_SENTINEL", encoding="utf-8")
        original.unlink()
        os.link(outside, original)
        response = self.client.get(f"/api/cases/{CASE_ID}")
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("PRIVATE_SENTINEL", response.text)

    def test_symlink_or_junction_is_rejected(self):
        outside = self.source_root.parent / "private"
        outside.mkdir()
        target = self.root / "fixtures/manuscripts/linked"
        try:
            target.symlink_to(outside, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                self.skipTest("Symlinks unavailable")
            import subprocess
            response = subprocess.run(["cmd", "/c", "mklink", "/J", str(target), str(outside)], capture_output=True)
            if response.returncode:
                self.skipTest("Links and junctions unavailable")
        try:
            response = self.client.get("/api/passages")
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            if target.is_symlink():
                target.unlink()
            else:
                target.rmdir()

    def test_reparse_detection_without_privileges(self):
        info = SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
        with patch.object(Path, "lstat", return_value=info):
            with patch("evals.server.repository.stat.FILE_ATTRIBUTE_REPARSE_POINT", 0x400, create=True):
                with self.assertRaises(DataError):
                    plain_path(self.root)

    def test_atomic_failure_preserves_original_judgments(self):
        before = self.get_case()
        with patch("evals.server.repository.os.replace", side_effect=OSError("private path must not leak")):
            response = self.judgment()
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private path", response.text)
        self.assertEqual(self.get_case()["version"], before["version"])
        self.assertEqual(list((self.root / f"cases/literary-translation/{CASE_ID}").glob(".write-*")), [])

    def test_skill_registry_and_unsupported_editor(self):
        skills = self.client.get("/api/skills").json()
        self.assertEqual(len(skills), 5)
        self.assertEqual([s["id"] for s in skills if s["supported"]], ["literary-translation"])
        self.assertEqual(self.client.get("/api/cases?skill=literary-editing").json(), [])
        self.assertEqual(self.client.post("/api/cases", json={"skill": "literary-editing"}, headers=self.headers).status_code, 405)


@unittest.skipUnless(os.environ.get("EVAL_BROWSER_TEST") == "1", "Set EVAL_BROWSER_TEST=1 after installing Playwright and Chromium.")
class BrowserTests(unittest.TestCase):
    def test_browser_conflict_offers_contextual_reload_without_losing_edits(self):
        import uvicorn
        from playwright.sync_api import expect, sync_playwright

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "evals"
            sample_copy(root)
            app = create_app(root, "http://127.0.0.1:18765", reviewer_label="one-judge")
            server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18765, log_level="error", access_log=False))
            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()
            try:
                for _ in range(100):
                    if server.started:
                        break
                    time.sleep(.05)
                self.assertTrue(server.started)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch()
                    try:
                        first_context, second_context = browser.new_context(), browser.new_context()
                        first, second = first_context.new_page(), second_context.new_page()
                        for page in (first, second):
                            page.goto("http://127.0.0.1:18765")
                            expect(page.locator("#reviewer-entry")).to_be_hidden()
                            page.get_by_label("Startup access key").fill(app.state.access_key)
                            page.get_by_role("button", name="Open workspace").click()
                            page.locator(f'[data-case-id="{CASE_ID}"]').click()
                            expect(page.locator("#session-reviewer")).to_have_text("Signed in as one-judge")
                            expect(page.locator("#reload-case")).to_have_count(0)
                            expect(page.get_by_role("button", name="Load latest review")).to_be_hidden()
                        first.get_by_label("Overall quality").select_option("4")
                        first.get_by_role("button", name="Mark complete").click()
                        expect(first.locator("#notice")).to_contain_text("You have completed all cases")
                        expect(first.locator("#case-detail")).to_be_hidden()
                        second.get_by_label("Overall quality").select_option("2")
                        second.get_by_label("Comments", exact=True).fill("Unsaved browser-local comment.")
                        second.get_by_role("button", name="Mark complete").click()
                        expect(second.get_by_role("button", name="Load latest review")).to_be_visible()
                        expect(second.get_by_label("Overall quality")).to_have_value("2")
                        expect(second.get_by_label("Comments", exact=True)).to_have_value("Unsaved browser-local comment.")
                        self.assertEqual(app.state.repository.get_case(CASE_ID)["judgments"][-1]["overall_score"], 4)
                        second.once("dialog", lambda dialog: dialog.dismiss())
                        second.get_by_role("button", name="Load latest review").click()
                        expect(second.get_by_label("Overall quality")).to_have_value("2")
                        second.once("dialog", lambda dialog: dialog.accept())
                        second.get_by_role("button", name="Load latest review").click()
                        expect(second.get_by_label("Overall quality")).to_have_value("4")
                        expect(second.get_by_label("Comments", exact=True)).to_have_value("")
                        expect(second.get_by_role("button", name="Load latest review")).to_be_hidden()
                        second.get_by_role("button", name="Mark complete").click()
                        expect(second.locator("#notice")).to_contain_text("You have completed all cases")
                        expect(second.locator("#case-detail")).to_be_hidden()
                        expect(second.locator("#case-empty")).to_be_visible()
                        self.assertEqual(len(app.state.repository.get_case(CASE_ID)["judgments"]), 2)
                        first.get_by_role("button", name="Sign out").click()
                        expect(first.locator("#login-panel")).to_be_visible()
                        expect(first.locator("#reviewer-entry")).to_be_hidden()
                        second.reload()
                        expect(second.locator("#session-reviewer")).to_have_text("Signed in as one-judge")
                        self.assertEqual(len(app.state.workspace.source.get_case(CASE_ID)["judgments"]), 1)
                    finally:
                        browser.close()
            finally:
                server.should_exit = True
                thread.join(timeout=10)

    def test_complete_advances_skips_finished_and_wraps_to_unfinished_cases(self):
        import uvicorn
        from playwright.sync_api import expect, sync_playwright

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "evals"
            sample_copy(root)
            source = root / f"cases/literary-translation/{CASE_ID}"
            for number in range(2, 7):
                case_id = f"zh-en-{number:06d}"
                destination = source.parent / case_id
                shutil.copytree(source, destination)
                metadata = json.loads((destination / "case.json").read_text(encoding="utf-8"))
                metadata["case_id"] = case_id
                if number == 5:
                    metadata["revision"] = 2
                (destination / "case.json").write_text(json.dumps(metadata), encoding="utf-8")
                completed = {
                    "judgment_id": f"completed-{number}", "case_id": case_id,
                    "case_revision": 1, "passage_id": PASSAGE_ID, "source_revision": 1,
                    "rubric_version": "retired-rubric-v0" if number == 6 else RUBRIC,
                    "rater_id": "other-judge" if number == 4 else "navigation-judge",
                    "status": "complete", "overall_score": 4,
                    "dimension_scores": {}, "rationale": None, "issues": [],
                }
                judgments = [completed]
                if number == 2:
                    judgments.append({
                        **completed, "judgment_id": "unfinished-2", "status": "pending",
                        "overall_score": 3, "supersedes_judgment_id": "completed-2",
                    })
                (destination / "judgments.jsonl").write_text(
                    "".join(json.dumps(j) + "\n" for j in judgments), encoding="utf-8"
                )
            app = create_app(root, "http://127.0.0.1:18765", reviewer_label="navigation-judge")
            originals = snapshot(app.state.workspace.source)
            server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18765, log_level="error", access_log=False))
            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()
            try:
                for _ in range(100):
                    if server.started:
                        break
                    time.sleep(.05)
                self.assertTrue(server.started)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch()
                    try:
                        page = browser.new_page()
                        page.goto("http://127.0.0.1:18765")
                        expect(page.locator("#reviewer-entry")).to_be_hidden()
                        page.get_by_label("Startup access key").fill(app.state.access_key)
                        page.get_by_role("button", name="Open workspace").click()
                        for number, status in (
                            (1, "Not reviewed"), (2, "Draft"), (3, "Completed"),
                            (4, "Not reviewed"), (5, "Not reviewed"), (6, "Not reviewed"),
                        ):
                            expect(page.locator(f'[data-case-id="zh-en-{number:06d}"]')).to_contain_text(status)
                        expect(page.locator("#case-list")).not_to_contain_text("Dataset")
                        page.locator(f'[data-case-id="{CASE_ID}"]').click()
                        page.get_by_role("button", name="Save draft", exact=True).click()
                        expect(page.locator(f'[data-case-id="{CASE_ID}"]')).to_contain_text("Draft")
                        expect(page.locator("#case-subtitle")).to_contain_text("Draft")
                        page.locator('[data-case-id="zh-en-000002"]').click()
                        expect(page.get_by_label("Overall quality")).to_have_value("3")
                        page.get_by_role("button", name="Save draft", exact=True).click()
                        expect(page.locator("#notice")).to_contain_text("Assessment saved")
                        expect(page.locator("#case-title")).to_have_text("zh-en-000002")
                        expect(page.locator("#case-detail")).to_be_visible()
                        page.get_by_role("button", name="Mark complete", exact=True).click()
                        for next_id in ("zh-en-000004", "zh-en-000005", "zh-en-000006", CASE_ID):
                            expect(page.locator("#case-title")).to_have_text(next_id)
                            expect(page.locator("#case-detail")).to_be_visible()
                            expect(page.get_by_label("Overall quality")).to_have_value("")
                            page.get_by_label("Overall quality").select_option("4")
                            page.get_by_role("button", name="Mark complete", exact=True).click()
                        expect(page.locator("#notice")).to_contain_text("You have completed all cases for Literary translation")
                        expect(page.locator("#notice")).to_contain_text("Submit changes")
                        expect(page.locator("#case-detail")).to_be_hidden()
                        expect(page.locator("#case-empty")).to_be_visible()
                        expect(page.locator("#case-empty")).to_contain_text("You have completed all cases")
                        expect(page.locator("#case-list button.selected")).to_have_count(0)
                        for number in range(1, 7):
                            expect(page.locator(f'[data-case-id="zh-en-{number:06d}"]')).to_contain_text("Completed")
                        self.assertEqual(snapshot(app.state.workspace.source), originals)
                        self.assertEqual(app.state.workspace.status()["pending_files"], 5)
                    finally:
                        browser.close()
            finally:
                server.should_exit = True
                thread.join(timeout=10)

    def test_judge_only_review_and_submission_in_browser(self):
        self.exercise_review()

    def test_startup_reviewer_label_in_browser(self):
        self.exercise_review(reviewer_label="configured-judge")

    def test_existing_review_loads_without_placeholder_choices(self):
        self.exercise_review(initial_review="own")

    def test_other_reviewers_stay_in_history_without_prefilling_your_review(self):
        self.exercise_review(initial_review="other")

    def exercise_review(self, reviewer_label=None, initial_review=None):
        import uvicorn
        from playwright.sync_api import expect, sync_playwright

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "evals"
            sample_copy(root)
            expected_reviewer = reviewer_label or "browser-test"
            if initial_review:
                path = root / f"cases/literary-translation/{CASE_ID}/judgments.jsonl"
                pending = json.loads(path.read_text(encoding="utf-8"))
                existing = {
                    **pending, "judgment_id": "existing-review",
                    "supersedes_judgment_id": pending["judgment_id"],
                    "status": "complete", "overall_score": 4,
                    "dimension_scores": {"fidelity": 3, "english_naturalness": 4, "literary_voice": 4},
                    "rater_id": expected_reviewer if initial_review == "own" else "other-reviewer",
                    "rubric_version": RUBRIC,
                }
                path.write_text(json.dumps(pending) + "\n" + json.dumps(existing) + "\n", encoding="utf-8")
            app = create_app(root, "http://127.0.0.1:18765", reviewer_label=reviewer_label)
            originals = snapshot(app.state.workspace.source)
            server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18765, log_level="error", access_log=False))
            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()
            try:
                for _ in range(100):
                    if server.started:
                        break
                    time.sleep(.05)
                self.assertTrue(server.started)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch()
                    try:
                        page = browser.new_page(viewport={"width": 1440, "height": 1100})
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.goto("http://127.0.0.1:18765")
                        page.get_by_label("Startup access key").fill(app.state.access_key)
                        if reviewer_label:
                            expect(page.locator("#reviewer-entry")).to_be_hidden()
                            expect(page.locator("#fixed-reviewer-note")).to_be_visible()
                        else:
                            page.get_by_label("Reviewer label", exact=True).fill(expected_reviewer)
                        page.get_by_role("button", name="Open workspace").click()
                        expect(page.locator("#session-reviewer")).to_have_text(f"Signed in as {expected_reviewer}")
                        expected_status = "Completed" if initial_review == "own" else "Not reviewed"
                        expect(page.locator(f'[data-case-id="{CASE_ID}"]')).to_contain_text(expected_status)
                        page.locator(f'[data-case-id="{CASE_ID}"]').click()
                        page.locator("#translation-text").wait_for()
                        self.assertIn("Braving the bitter cold", page.locator("#translation-text").inner_text())
                        self.assertIn("我冒了严寒", page.locator("#source-text").inner_text())
                        expect(page.get_by_role("heading", name="Your review", exact=True)).to_be_visible()
                        expect(page.locator("#case-subtitle")).to_contain_text(expected_status)
                        expect(page.locator("#case-subtitle")).not_to_contain_text("dataset status")
                        expect(page.locator("#case-provenance")).to_contain_text("Case status: placeholder")
                        expect(page.locator("#assessment-select")).to_have_count(0)
                        self.assertEqual(page.locator('[name="overall_score"]').input_value(), "4" if initial_review == "own" else "")
                        if initial_review == "other":
                            expect(page.locator("#review-history")).to_be_visible()
                        else:
                            expect(page.locator("#review-history")).to_be_hidden()
                        expect(page.locator("#review-history[open]")).to_have_count(0)
                        expect(page.locator("#review-history-list")).not_to_contain_text("Unassigned")
                        expect(page.locator("#new-case, #new-passage, #case-create-form, #metadata-form, #passage-form, #rubric-select, #reload-case")).to_have_count(0)
                        expect(page.locator("#assigned-rubric")).to_contain_text("v1")
                        if os.environ.get("EVAL_SCREENSHOT"):
                            page.screenshot(path=os.environ["EVAL_SCREENSHOT"], full_page=True)
                        expect(page.locator('#judgment-form [name="rater_id"]')).to_have_count(0)
                        expect(page.locator("#assessment-reviewer")).to_have_text(expected_reviewer)
                        page.get_by_label("Overall quality").select_option("4")
                        comments = 'Browser test on disposable data. <img src=x onerror="alert(1)">'
                        page.get_by_label("Comments", exact=True).fill(comments)
                        page.get_by_role("button", name="Add issue", exact=True).click()
                        page.get_by_label("Explanation", exact=True).fill("The image loses some of its restraint.")
                        page.get_by_role("button", name="Mark complete").click()
                        expect(page.locator("#notice")).to_contain_text("You have completed all cases for Literary translation")
                        expect(page.locator("#case-detail")).to_be_hidden()
                        expect(page.locator("#case-empty")).to_contain_text("You have completed all cases")
                        expect(page.locator(f'[data-case-id="{CASE_ID}"]')).to_contain_text("Completed")
                        page.reload()
                        page.locator(f'[data-case-id="{CASE_ID}"]').click()
                        expect(page.locator('[name="overall_score"]')).to_have_value("4")
                        expect(page.locator("#session-reviewer")).to_have_text(f"Signed in as {expected_reviewer}")
                        expect(page.get_by_label("Comments", exact=True)).to_have_value(comments)
                        expect(page.locator("#judgment-form img")).to_have_count(0)
                        page.get_by_label("Overall quality").select_option("3")
                        page.get_by_role("button", name="Mark complete").click()
                        expect(page.locator("#case-detail")).to_be_hidden()
                        page.locator(f'[data-case-id="{CASE_ID}"]').click()
                        expect(page.locator("#case-detail")).to_be_visible()
                        expect(page.locator("#review-history-list > details")).to_have_count(2 if initial_review else 1)
                        expect(page.locator("#review-history[open]")).to_have_count(0)
                        page.locator("#review-history-summary").click()
                        page.locator("#review-history-list > details > summary").first.click()
                        expect(page.locator("#review-history-list")).to_contain_text("overall 4")
                        expect(page.locator("#review-history input, #review-history textarea, #review-history select, #review-history button, #review-history img")).to_have_count(0)
                        expect(page.locator('[name="overall_score"]')).to_have_value("3")
                        page.get_by_role("button", name="Original passages", exact=True).click()
                        page.locator("#passage-list button").first.click()
                        expect(page.locator("#passage-text")).to_contain_text("我冒了严寒")
                        expect(page.locator("#passages-view input, #passages-view textarea")).to_have_count(0)
                        self.assertEqual(errors, [])
                        data = app.state.repository.get_case(CASE_ID)
                        self.assertEqual([j["overall_score"] for j in data["judgments"]], [None] + ([4] if initial_review else []) + [4, 3])
                        expected_raters = [None] + ([existing["rater_id"]] if initial_review else []) + [expected_reviewer, expected_reviewer]
                        self.assertEqual([j["rater_id"] for j in data["judgments"]], expected_raters)
                        self.assertEqual(len(app.state.workspace.source.get_case(CASE_ID)["judgments"]), 2 if initial_review else 1)
                        self.assertEqual(len(app.state.workspace.source.list_passages()), 1)
                        page.get_by_role("button", name="Submit changes", exact=True).click()
                        page.get_by_role("button", name="Submit to source", exact=True).click()
                        expect(page.locator("#workspace-state")).to_have_text("No pending changes.")
                        self.assertEqual(len(app.state.workspace.source.get_case(CASE_ID)["judgments"]), 4 if initial_review else 3)
                        self.assertEqual(len(app.state.workspace.source.list_passages()), 1)
                        submitted = snapshot(app.state.workspace.source)
                        self.assertEqual(
                            {name for name in submitted if submitted[name] != originals.get(name)},
                            {f"cases/literary-translation/{CASE_ID}/judgments.jsonl"},
                        )
                        page.get_by_role("button", name="Cases", exact=True).click()
                        page.locator(f'[data-case-id="{CASE_ID}"]').click()
                        page.get_by_role("button", name="Save draft", exact=True).click()
                        expect(page.locator(f'[data-case-id="{CASE_ID}"]')).to_contain_text("Draft")
                        expect(page.locator("#case-subtitle")).to_contain_text("Draft")
                        self.assertEqual(app.state.workspace.source.get_case(CASE_ID)["judgments"][-1]["status"], "complete")
                        page.get_by_role("button", name="Sign out", exact=True).click()
                        page.locator("#login-panel").wait_for()
                    finally:
                        browser.close()
            finally:
                server.should_exit = True
                thread.join(timeout=10)


if __name__ == "__main__":
    unittest.main()
