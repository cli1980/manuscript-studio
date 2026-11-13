"""Protocol-neutral JSONL subprocess transport; construction has no process side effects."""

from __future__ import annotations

import json
import os
import queue
import signal
import subprocess
import threading
import time


class StdioTransport:
    def __init__(self, command, *, cwd, timeout, name, env=None):
        self.command, self.cwd, self.env = list(command), cwd, env
        self.timeout, self.name = timeout, name
        self.process = None
        self.readers = []
        self.messages = queue.Queue()

    def __enter__(self):
        self.deadline = time.monotonic() + self.timeout
        self.process = subprocess.Popen(
            self.command, cwd=self.cwd, env=self.env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
            bufsize=1, start_new_session=os.name != "nt",
        )
        self.readers = [threading.Thread(target=self._read_stdout, daemon=True),
                        threading.Thread(target=self._drain_stderr, daemon=True)]
        try:
            for reader in self.readers:
                reader.start()
        except BaseException:
            self.close()
            raise
        return self

    def _read_stdout(self):
        try:
            for line in self.process.stdout:
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError()
                    self.messages.put(value)
                except ValueError:
                    self.messages.put(RuntimeError(f"{self.name} emitted malformed JSONL."))
        except (OSError, ValueError):
            pass
        finally:
            self.messages.put(RuntimeError(
                f"{self.name} closed its protocol output before completing the operation."))

    def _drain_stderr(self):
        # Provider diagnostics may contain credentials or manuscript text.
        try:
            for _ in self.process.stderr:
                pass
        except (OSError, ValueError):
            pass

    def send(self, value):
        try:
            self.process.stdin.write(json.dumps(value, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
        except (OSError, ValueError):
            raise RuntimeError(f"{self.name} closed its protocol input.") from None

    def receive(self):
        remaining = self.deadline - time.monotonic()
        try:
            if remaining <= 0:
                raise queue.Empty()
            value = self.messages.get(timeout=remaining)
        except queue.Empty:
            raise TimeoutError(f"{self.name} turn exceeded the configured execution timeout.") from None
        if isinstance(value, Exception):
            raise value
        return value

    def close(self):
        process = self.process
        if process is None:
            return
        try:
            if os.name == "nt":
                if process.poll() is None:
                    try:
                        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                    except (OSError, subprocess.TimeoutExpired):
                        process.kill()
            else:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            for reader in self.readers:
                if reader.ident is not None:
                    reader.join(timeout=2)
        finally:
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
            self.process = None

    def __exit__(self, *_):
        self.close()
