"""Background execution: run agent turns automatically until a run needs a human."""

from __future__ import annotations

import threading
import traceback

from workflow.src.service import WorkflowService
from workflow.src.storage import now


class Workers:
    """One thread per active run. Human waits, blockers, failures, and completion stop a worker."""

    def __init__(self, server_root, runtime_factory, *, owner=None, execution_profile=None):
        self.server_root = server_root
        self.runtime_factory = runtime_factory
        self.owner = owner
        self.execution_profile = execution_profile
        self.lock = threading.Lock()
        self.threads = {}
        self.paused = set()
        self.last = {}

    def status(self, run_id):
        with self.lock:
            thread = self.threads.get(run_id)
            return {"active": bool(thread and thread.is_alive()), "paused": run_id in self.paused,
                    **self.last.get(run_id, {})}

    def start(self, run_id):
        """Start (or keep) automatic execution unless the user paused it."""
        with self.lock:
            if run_id in self.paused:
                return False
            thread = self.threads.get(run_id)
            if thread and thread.is_alive():
                return True
            thread = threading.Thread(target=self._loop, args=(run_id,), name=f"run-{run_id}", daemon=True)
            self.threads[run_id] = thread
            thread.start()
            return True

    def pause(self, run_id):
        """Stop after the current agent turn; saved state is preserved."""
        with self.lock:
            self.paused.add(run_id)

    def resume(self, run_id):
        with self.lock:
            self.paused.discard(run_id)
        return self.start(run_id)

    def wait(self, run_id, timeout=None):
        thread = self.threads.get(run_id)
        if thread:
            thread.join(timeout)

    def _loop(self, run_id):
        service = WorkflowService(self.server_root, owner=self.owner, execution_profile=self.execution_profile)
        try:
            while True:
                with self.lock:
                    if run_id in self.paused:
                        self.last[run_id] = {"stopped": "paused", "at": now()}
                        return
                state = service.get_run(run_id)
                if state["status"] != "READY":
                    self.last[run_id] = {"stopped": state["status"], "at": now()}
                    return
                self.last[run_id] = {"stopped": None, "turn_started": now()}
                try:
                    service.step(run_id, self.runtime_factory())
                except Exception as exc:  # The run records FAILED/PAUSED itself; stop and surface it.
                    self.last[run_id] = {"stopped": "error", "error": str(exc), "at": now()}
                    return
        except Exception as exc:
            self.last[run_id] = {"stopped": "error", "error": str(exc), "trace": traceback.format_exc(limit=3),
                                 "at": now()}
        finally:
            service.close()
