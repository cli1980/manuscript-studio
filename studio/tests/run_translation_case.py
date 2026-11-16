"""Run the existing translation browser case against a live, explicitly selected server.

Automated decisions go through the shared local engine for delegated attribution,
then the real server resumes execution. This is not full decision-API transport coverage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from playwright.sync_api import sync_playwright

from studio.tests.runner import CASES, CaseRunner
from workflow.src import registry
from workflow.src.service import WorkflowService


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--server-root", required=True, type=Path)
    parser.add_argument("--harness", required=True)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args(argv)
    origin, root = args.origin.rstrip("/"), args.server_root.resolve()
    url = urlsplit(origin)
    if url.scheme != "http" or url.hostname not in ("127.0.0.1", "localhost") or url.path:
        parser.error("Use an explicit loopback HTTP origin.")
    if args.report.exists():
        parser.error("Choose a new report path; previous evaluation evidence is never overwritten.")
    raw = (CASES / "beijing-night-translation-gui-001/case.json").read_bytes()
    case = json.loads(raw)
    report = {
        "case_id": case["case_id"], "case_sha256": hashlib.sha256(raw).hexdigest(),
        "started_at": datetime.now(timezone.utc).isoformat(), "status": "running",
        "origin": origin, "server_root": str(root), "steps": [],
        "decision_source": "delegated-automation", "human_quality_review": "not performed",
        "decision_transport": "browser interception into shared local engine; real server resumes",
        "engine": registry.engine_identity("literary-translation-v1"),
    }

    def save():
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                               encoding="utf-8", newline="\n")

    class Runner(CaseRunner):
        last = None

        def request(self, method, path, payload=None):
            status, body = super().request(method, path, payload)
            if isinstance(body, dict) and "stage" in body and "status" in body:
                key = (body["status"], body["stage"], (body.get("gate") or {}).get("id"))
                if key != self.last:
                    print("RUN", body.get("id"), *key[:2], body.get("error") or "", flush=True)
                    self.last = key
                    report["last_run"] = body
                    save()
            return status, body

        def step_start_run(self, step):
            status, body = self.request("POST", "/api/runs", {
                "template_id": step["template_id"], "work_id": step["work_id"], "start": False})
            self.expect_status(status, 200, body)
            report["run_id"] = body["id"]
            with WorkflowService(root) as service, service.open_run(body["id"]) as engine:
                if engine.state()["engine"] != report["engine"]:
                    raise RuntimeError("Server loaded different engine code; restart it before evaluating.")
                engine.store.event("test.case_bound", {
                    "case_id": report["case_id"], "case_sha256": report["case_sha256"],
                    "decision_source": "delegated-automation"})
            status, _ = self.request("POST", f"/api/runs/{body['id']}/resume", {})
            self.expect_status(status, 200, {})
            return body

    with httpx.Client(base_url=origin, timeout=120) as client:
        catalog = client.get("/api/execution").raise_for_status().json()
        if catalog["harness"] != args.harness or not catalog["models"]:
            raise RuntimeError("The live server must use the explicitly selected harness profile.")
        report["execution_catalog"] = catalog
        save()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()

            def decide(route):
                path = urlsplit(route.request.url).path
                parts, suffix = path.strip("/").split("/"), path.rsplit("/", 1)[-1]
                if (route.request.method != "POST" or suffix not in ("reply", "confirm", "accept")
                        or len(parts) < 4 or parts[:2] != ["api", "runs"]):
                    route.continue_()
                    return
                payload, run_id = route.request.post_data_json, parts[2]
                try:
                    with WorkflowService(root) as service, service.open_run(run_id) as engine:
                        if suffix == "accept":
                            engine.accept(payload["acceptance_id"],
                                          confirm_final=payload.get("confirm_final") is True,
                                          decision_source="delegated-automation")
                        else:
                            if suffix == "confirm":
                                if engine.state()["gate"]["record_revision"] != payload["record_revision"]:
                                    raise ValueError("Stale metadata revision.")
                            engine.reply(payload["gate_id"],
                                         "confirm metadata" if suffix == "confirm" else payload["text"],
                                         decision_source="delegated-automation")
                    response = client.post(f"/api/runs/{run_id}/resume", json={}, headers={"Origin": origin})
                    route.fulfill(status=response.status_code, content_type="application/json", body=response.text)
                except Exception as error:
                    route.fulfill(status=409, json={"detail": f"Evaluation decision failed: {error}"})

            page.route("**/api/runs/**", decide)
            runner = Runner(client, case, origin=origin, page=page)
            try:
                for number, step in enumerate(case["steps"], 1):
                    print("STEP", number, step["action"], flush=True)
                    if step["action"] == "drive_run":
                        step = {**step, "poll": 3}
                    body = getattr(runner, "step_" + step["action"])(step)
                    if step.get("save_as"):
                        runner.saved[step["save_as"]] = body
                    for check in step.get("expect", []):
                        runner.check(f"{case['case_id']} step {number}", body, check)
                    report["steps"].append({"number": number, "action": step["action"], "status": "passed"})
                    save()
                with WorkflowService(root) as service, service.open_run(report["run_id"]) as engine:
                    state = engine.state()
                    export = Path(state["export_path"])
                    manifest = json.loads((export / "manifest.json").read_text(encoding="utf-8"))
                    for index, artifact in enumerate(manifest["chapters"], 1):
                        if hashlib.sha256((export / f"{index:04d}.md").read_bytes()).hexdigest() != artifact["sha256"]:
                            raise ValueError("Exported chapter does not match its accepted artifact.")
                    for name, artifact in manifest["continuity"].items():
                        if hashlib.sha256((export / f"{name}.md").read_bytes()).hexdigest() != artifact["sha256"]:
                            raise ValueError("Exported continuity does not match its accepted artifact.")
                    if any(r["decision_source"] != "delegated-automation" for r in state["receipts"]):
                        raise ValueError("Automated gate decision was incorrectly attributed.")
                    if state["acceptance"]["decision_source"] != "delegated-automation":
                        raise ValueError("Automated acceptance was incorrectly attributed.")
                    attempts = [e["payload"]["execution"] for e in engine.store.events()
                                if e["kind"] == "execution.started"]
                    if not attempts or any(a["harness"] != args.harness for a in attempts):
                        raise ValueError("Execution attempts do not match the selected harness.")
                    report.update(work_id=state["work_id"], export_path=str(export), attempts=attempts,
                                  receipt_count=len(state["receipts"]), artifact_hashes_verified=True)
                report["status"] = "passed"
            except Exception as error:
                report.update(status="failed", error=str(error))
                print("CASE FAILED:", error, flush=True)
            finally:
                report["finished_at"] = datetime.now(timezone.utc).isoformat()
                save()
                browser.close()
    print("REPORT", args.report, flush=True)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
