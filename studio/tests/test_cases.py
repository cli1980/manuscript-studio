"""Run every case under studio/tests/cases: python -m unittest studio.tests.test_cases -v."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

from .runner import FIXTURES, CaseRunner, load_cases

HAS_WEB = importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx")


@unittest.skipUnless(HAS_WEB, "Install studio/requirements.txt for studio case tests.")
class StudioCaseTests(unittest.TestCase):
    """Each case gets a fresh server root and app; no model runtime is started unless a case asks for one."""

    def run_case(self, case):
        from fastapi.testclient import TestClient
        from studio.server.app import create_app

        def no_runtime():
            raise AssertionError("This case must not start an agent turn.")

        runtime = no_runtime
        live = case.get("runtime")
        if live:
            # Live cases run real agent turns; opt in with STUDIO_LIVE=1 (and CODEX=path if not on PATH).
            if os.environ.get("STUDIO_LIVE") != "1":
                self.skipTest("Live case: set STUDIO_LIVE=1 to run it with Codex.")
            for name in live.get("fixtures", []):
                if not (FIXTURES / name).is_file():
                    self.skipTest(f"Local-only fixture missing: fixtures/{name}")
            from workflow.src.runtime import CodexRuntime
            codex, timeout = os.environ.get("CODEX", "codex"), float(live.get("turn_timeout", 900))
            runtime = lambda: CodexRuntime([codex, "app-server"], timeout)  # noqa: E731
        root = os.environ.get("STUDIO_CASE_ROOT")  # Keep a live case's server root for inspection.
        with tempfile.TemporaryDirectory() as temporary:
            server = Path(root) / case["case_id"] if root else Path(temporary) / "server"
            if live and live.get("client") == "browser":
                self.run_in_browser(case, server, runtime)
                return
            app = create_app(server, runtime_factory=runtime, owner="case-runner")
            with TestClient(app, base_url="http://127.0.0.1:8765") as client:
                CaseRunner(client, case).run()

    def run_in_browser(self, case, server, runtime):
        """Serve the studio on its own port and make every reviewer choice by clicking its pages.

        Watch it at http://127.0.0.1:<STUDIO_CASE_PORT> (default 8766), or show the automated browser with
        STUDIO_HEADED=1 (STUDIO_SLOW_MO=ms slows its clicks). STUDIO_ALLOW_ORIGIN adds a loopback preview origin.
        """
        import threading
        import time

        import httpx
        import uvicorn
        from playwright.sync_api import sync_playwright
        from studio.server.app import create_app

        port = int(os.environ.get("STUDIO_CASE_PORT", "8766"))
        extra = [o for o in os.environ.get("STUDIO_ALLOW_ORIGIN", "").split(",") if o]
        app = create_app(server, port=port, runtime_factory=runtime, owner="case-runner", extra_origins=extra)
        web = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        thread = threading.Thread(target=web.run, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if web.started:
                    break
                time.sleep(0.1)
            origin = f"http://127.0.0.1:{port}"
            with httpx.Client(base_url=origin, timeout=120) as client, sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=os.environ.get("STUDIO_HEADED") != "1",
                                                     slow_mo=int(os.environ.get("STUDIO_SLOW_MO", "0")))
                try:
                    CaseRunner(client, case, origin=origin, page=browser.new_page()).run()
                finally:
                    browser.close()
        finally:
            web.should_exit = True
            thread.join(10)


def _make(case):
    def test(self):
        self.run_case(case)
    test.__doc__ = case.get("title")
    return test


for _case in load_cases():
    setattr(StudioCaseTests, "test_" + _case["case_id"].replace("-", "_"), _make(_case))


if __name__ == "__main__":
    unittest.main()
