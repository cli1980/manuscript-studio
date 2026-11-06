"""Case-driven studio tests: each case.json lists API steps and expectations, using shared repository fixtures.

Steps run against the FastAPI app through its HTTP interface, exactly as the browser does. Values saved by
one step (`save_as`) are referenced later as "$name" or "$name.field". Fixture paths are relative to the
repository's shared `fixtures/` folder.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "fixtures"
CASES = Path(__file__).resolve().parent / "cases"
ORIGIN = "http://127.0.0.1:8765"
REFERENCE = re.compile(r"\$[A-Za-z_]\w*(?:\.[\w-]+)*")


class CaseFailure(AssertionError):
    pass


def load_cases():
    cases = []
    for path in sorted(CASES.glob("*/case.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        if case.get("schema_version") != 1 or case.get("case_id") != path.parent.name or not case.get("steps"):
            raise ValueError(f"Invalid studio case: {path}")
        cases.append(case)
    return cases


def fixture(relative):
    path = (FIXTURES / relative).resolve()
    if not path.is_relative_to(FIXTURES) or not path.is_file():
        raise ValueError(f"Missing shared fixture: {relative}")
    return path


class CaseRunner:
    def __init__(self, client, case, *, origin=ORIGIN, page=None):
        self.client, self.case, self.saved, self.origin, self.page = client, case, {}, origin, page

    def lookup(self, reference):
        name, _, field = reference.partition(".")
        result = self.saved[name]
        for key in filter(None, field.split(".")):
            result = result[int(key)] if isinstance(result, list) else result[key]
        return result

    def resolve(self, value):
        if isinstance(value, str) and REFERENCE.fullmatch(value):
            return self.lookup(value[1:])  # A whole-string reference keeps its type.
        if isinstance(value, str) and "$" in value:
            return REFERENCE.sub(lambda match: str(self.lookup(match.group(0)[1:])), value)
        if isinstance(value, dict):
            return {key: self.resolve(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        return value

    def request(self, method, path, payload=None):
        path = self.resolve(path)
        if method == "GET":
            response = self.client.get(path)
        else:
            response = self.client.post(path, json=self.resolve(payload or {}), headers={"Origin": self.origin})
        try:
            body = response.json()
        except ValueError:
            body = response.text
        return response.status_code, body

    def run(self):
        for number, step in enumerate(self.case["steps"], 1):
            label = f"{self.case['case_id']} step {number} ({step['action']})"
            try:
                body = getattr(self, "step_" + step["action"])(step)
            except CaseFailure as exc:
                raise CaseFailure(f"{label}: {exc}") from None
            if step.get("save_as"):
                self.saved[step["save_as"]] = body
            for check in step.get("expect", []):
                self.check(label, body, check)

    # ----- actions ------------------------------------------------------------------------

    def step_upload_work(self, step):
        """Works-page intake: upload a shared fixture as a new work."""
        source = fixture(step["fixture"])
        name = step.get("name", source.name)
        status, body = self.request("POST", "/api/works", {
            "upload": {"name": name, "data": base64.b64encode(source.read_bytes()).decode()},
            "manuscript_language": step["manuscript_language"]})
        self.expect_status(status, step.get("status", 200), body)
        if status == 200:
            data = source.read_bytes()
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = None  # Binary fixtures such as DOCX.
            body["_fixture"] = {"path": step["fixture"], "sha256": hashlib.sha256(data).hexdigest(), "text": text}
        return body

    def step_get(self, step):
        status, body = self.request("GET", step["path"])
        self.expect_status(status, step.get("status", 200), body)
        return body

    def step_post(self, step):
        status, body = self.request("POST", step["path"], step.get("payload"))
        self.expect_status(status, step.get("status", 200), body)
        return body

    def step_page(self, step):
        """The browser entry point serves the built frontend (or explains that it is not built)."""
        response = self.client.get(step.get("path", "/"))
        if response.status_code not in (200, 503):
            raise CaseFailure(f"page returned {response.status_code}")
        return {"status": response.status_code, "html": response.text}

    def step_start_run(self, step):
        """The work page's Start button: create a run on an existing work."""
        status, body = self.request("POST", "/api/runs", {"template_id": step["template_id"], "work_id": step["work_id"]})
        self.expect_status(status, step.get("status", 200), body)
        return body

    def step_drive_run(self, step):
        """Answer gates as a reviewer would in the GUI until the run reaches `until` (a status or stage).

        Metadata is confirmed at the presented revision; every open sheet item gets the first allowed decision
        that resolves without a note (for translation advice, "keep current translation"), followed by the
        separate closure; free questions get their offered command or "continue". Final acceptance is given
        only when the step sets "accept": true.
        """
        run_id = self.resolve(step["run_id"])
        until, deadline = step.get("until", "COMPLETED"), time.monotonic() + float(step.get("timeout", 4 * 3600))
        answered = 0
        while True:
            if time.monotonic() > deadline:
                raise CaseFailure(f"run did not reach {until} in time")
            _, run = self.request("GET", f"/api/runs/{run_id}")
            if run["status"] == until or (run["stage"] == until and run["status"] != "RUNNING"):
                run["_answered"] = answered
                return run
            if run["status"] in ("FAILED", "BLOCKED", "CANCELLED") or run["status"] == "COMPLETED":
                raise CaseFailure(f"run stopped at {run['status']} ({run['stage']}): {run.get('error')}")
            if run["status"] == "RUNNING" or run["worker"]["active"] or run["status"] == "READY":
                time.sleep(float(step.get("poll", 10)))
                continue
            if self.page is not None:
                if run["status"] == "WAITING_FOR_ACCEPTANCE" and not step.get("accept"):
                    raise CaseFailure("final acceptance reached but the step does not accept")
                self.answer_in_browser(run_id, run, step)
                answered += 1
                continue
            if run["status"] == "WAITING_FOR_ACCEPTANCE":
                if not step.get("accept"):
                    raise CaseFailure("final acceptance reached but the step does not accept")
                path, payload = f"/api/runs/{run_id}/accept", {"acceptance_id": run["acceptance"]["acceptance_id"],
                                                               "confirm_final": True}
            else:
                gate = run["gate"]
                path = f"/api/runs/{run_id}/reply"
                if gate["kind"] == "metadata_review":
                    path, payload = f"/api/runs/{run_id}/metadata/confirm", {
                        "gate_id": gate["id"], "record_revision": run["metadata"]["record_revision"]}
                elif gate.get("options"):
                    payload = {"gate_id": gate["id"], "text": self.pass_command(run, step)}
                elif gate["sheet"]:
                    payload = {"gate_id": gate["id"], "text": self.sheet_reply(gate["sheet"])}
                else:
                    payload = {"gate_id": gate["id"], "text": (gate["commands"] or ["continue"])[0]}
            status, body = self.request("POST", path, payload)
            self.expect_status(status, 200, body)
            answered += 1

    def choose(self, sheet, item):
        decisions = {d["id"]: d for d in sheet["decisions"]}
        choice = next((decisions[d] for d in item["allowed_decisions"]
                       if decisions[d]["effect"] == "resolve" and not decisions[d]["requires_note"]), None)
        if choice is None:
            raise CaseFailure(f"{item['id']} has no decision that resolves without a note")
        return choice

    @staticmethod
    def pass_command(run, step):
        """Editing passes follow the step's plan ("passes": ["line", ...]); each is accepted, then final acceptance."""
        if run["gate"]["kind"] == "pass_review":
            return run["gate"]["options"][0]["command"]
        plan, done = step.get("passes", []), len(run.get("passes") or [])
        return f"run {plan[done]}" if done < len(plan) else "finish"

    def answer_in_browser(self, run_id, run, step):
        """Make the reviewer's choice by clicking the studio's run page, as a person would."""
        page = self.page
        gate = run.get("gate") or {}
        if run.get("workflow") in ("literary-translation", "literary-editing"):
            # Every decision of these runs is made in the review viewer (see studio/frontend/src/workflows.ts);
            # whole-book and pass decisions show at its top.
            chapter = (f"/{gate['chapter_id']}" if run["status"] == "WAITING_FOR_HUMAN" and gate.get("chapter_id")
                       and gate["chapter_id"] != "_whole" else "")
            page.goto(f"{self.origin}/#/runs/{run_id}/chapters{chapter}")
            page.wait_for_selector(".panel.gate", timeout=60000)
        else:
            page.goto(f"{self.origin}/#/runs/{run_id}")
            page.wait_for_selector(".panel.gate", timeout=60000)
        before = (run["status"], (run.get("gate") or {}).get("id"))
        gate = run.get("gate") or {}
        sheet = gate.get("sheet")
        if run["status"] == "WAITING_FOR_ACCEPTANCE":
            page.get_by_label("I understand that accepting finalizes this run.").check()
            page.get_by_role("button", name="Accept and finalize").click()
        elif gate["kind"] == "chapter_sanity" and not sheet:
            page.get_by_role("button", name="Approve chapter").click()
        elif gate["kind"] == "metadata_review":
            page.get_by_role("button", name=re.compile(r"^Confirm metadata")).click()
        elif gate.get("options"):
            command = self.pass_command(run, step)
            option = next(o for o in gate["options"] if o["command"] == command)
            if option.get("stage"):
                page.get_by_label("Next pass").select_option(label=option["title"])
                page.get_by_role("button", name="Start pass").click()
            else:
                page.get_by_role("button", name=option["title"], exact=True).click()
        elif sheet and page.locator(".sample-poll").count():
            # The sample poll: pick the first variant of every open sample, then submit.
            for index, item in enumerate(sheet["items"]):
                if item["status"] != "resolved":
                    page.locator(".sample-poll .sample").nth(index).locator(".variant input").first.check()
            page.get_by_role("button", name=re.compile(r"^Submit choices")).click()
        elif sheet and page.locator(".review").count():
            open_items = [item for item in sheet["items"] if item["status"] != "resolved"]
            if not open_items:
                page.locator(".review button.primary").click()
            else:
                for item in open_items:
                    page.locator(".chips").get_by_role("button", name=item["id"], exact=True).click()
                    label = self.choose(sheet, item)["label"]
                    page.locator(".review-card button.decision").filter(has_text=label).first.click()
                page.get_by_role("button", name=re.compile(r"^Submit all")).click()
        elif gate.get("commands"):
            # The shared agent feedback widget shows each command as a button, capitalized.
            page.get_by_role("button", name=re.compile(f"^{re.escape(gate['commands'][0])}$", re.I)).click()
        else:
            page.locator(".panel.gate textarea").fill("continue")
            page.get_by_role("button", name="Send answer").click()
        for _ in range(120):  # Wait until the server records the choice.
            code, now = self.request("GET", f"/api/runs/{run_id}")
            if not isinstance(now, dict):
                raise CaseFailure(f"run status request failed with HTTP {code}: {str(now)[:300]}")
            if (now["status"], (now.get("gate") or {}).get("id")) != before:
                return
            error = page.locator(".error").first
            if error.count() and error.is_visible():
                raise CaseFailure(f"the page reported: {error.inner_text()}")
            time.sleep(1)
        raise CaseFailure("the page did not record the reviewer's choice")

    @staticmethod
    def sheet_reply(sheet):
        open_items = [item for item in sheet["items"] if item["status"] != "resolved"]
        if not open_items:
            return sheet["submission"]["closure_command"]
        decisions = {d["id"]: d for d in sheet["decisions"]}
        lines = []
        for item in open_items:
            choice = next((decisions[d] for d in item["allowed_decisions"]
                           if decisions[d]["effect"] == "resolve" and not decisions[d]["requires_note"]), None)
            if choice is None:
                raise CaseFailure(f"{item['id']} has no decision that resolves without a note")
            lines.append(f"{item['id']} {choice['command']}")
        return "\n".join(lines)

    @staticmethod
    def expect_status(status, expected, body):
        if status != expected:
            raise CaseFailure(f"expected HTTP {expected}, got {status}: {body}")

    # ----- expectations -------------------------------------------------------------------

    def value(self, body, path):
        result = body
        for key in filter(None, self.resolve(path).split(".")) if path else []:
            if key == "*keys":
                result = sorted(result)
            elif key == "*len":
                result = len(result)
            elif isinstance(result, list):
                result = result[int(key)] if re.fullmatch(r"-?\d+", key) else [item[key] for item in result]
            else:
                if key not in result:
                    raise CaseFailure(f"missing field {key!r} in {path}")
                result = result[key]
        return result

    def check(self, label, body, check):
        actual = self.value(body, check.get("path", ""))
        expected = self.resolve(check.get("value"))
        kind = check.get("op", "equals")
        passed = {
            "equals": lambda: actual == expected,
            "not_equals": lambda: actual != expected,
            "contains": lambda: expected in actual,
            "length": lambda: len(actual) == expected,
            "unique": lambda: len(actual) == len(set(actual)),
            "matches": lambda: re.fullmatch(expected, str(actual)) is not None,
            "every_startswith": lambda: all(str(item).startswith(expected) for item in actual),
            "empty": lambda: not actual,
        }[kind]()
        if not passed:
            raise CaseFailure(f"{label}: {check.get('path', '<body>')} {kind} {expected!r} failed; actual {actual!r}")
