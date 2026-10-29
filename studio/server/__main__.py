"""Run the local web application: python -m studio.server --server-root .workflow-runs."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from .app import create_app


def main(argv=None):
    parser = argparse.ArgumentParser(description="Manuscript Studio web application (localhost only).")
    parser.add_argument("--server-root", type=Path, default=Path(".workflow-runs"))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--codex", default="codex", help="Codex executable path (not a shell command).")
    parser.add_argument("--timeout", type=float, default=900, help="Active-turn timeout in seconds.")
    parser.add_argument("--owner", help="Owner recorded on new works and runs (default: OS user name).")
    parser.add_argument("--allow-origin", action="append", default=[], metavar="http://127.0.0.1:PORT",
                        help="Additional loopback origin allowed to write, e.g. a local preview proxy.")
    args = parser.parse_args(argv)
    app = create_app(args.server_root, port=args.port, codex=args.codex, timeout=args.timeout, owner=args.owner,
                     extra_origins=args.allow_origin)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
