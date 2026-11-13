"""Run the local web application: python -m studio.server --server-root .workflow-runs."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from workflow.src.execution import ExecutionProfile

from .app import create_app


def main(argv=None):
    parser = argparse.ArgumentParser(description="Manuscript Studio web application (localhost only).")
    parser.add_argument("--server-root", type=Path, default=Path(".workflow-runs"))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--codex", default="codex", help="Codex executable path (not a shell command).")
    parser.add_argument("--timeout", type=float, default=900, help="Active-turn timeout in seconds.")
    parser.add_argument("--owner", help="Owner recorded on new works and runs (default: OS user name).")
    parser.add_argument("--execution-profile", type=Path, help="Execution profile JSON, loaded once at startup.")
    parser.add_argument("--user-execution-profile", type=Path,
                        help="User JSON overlay for endpoints, models, and default model; requires --execution-profile.")
    parser.add_argument("--allow-origin", action="append", default=[], metavar="http://127.0.0.1:PORT",
                        help="Additional loopback origin allowed to write, e.g. a local preview proxy.")
    args = parser.parse_args(argv)
    try:
        profile = ExecutionProfile.load(args.execution_profile, args.user_execution_profile)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if profile and (args.codex != "codex" or args.timeout != 900):
        parser.error("With --execution-profile, configure command and timeout in that profile.")
    app = create_app(args.server_root, port=args.port, codex=args.codex, timeout=args.timeout, owner=args.owner,
                     extra_origins=args.allow_origin, execution_profile=profile)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
