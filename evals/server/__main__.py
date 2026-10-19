import argparse
from pathlib import Path

import uvicorn
from pydantic import TypeAdapter

from .app import create_app
from .models import ReviewerLabel


def main(argv=None):
    parser = argparse.ArgumentParser(description="Manage evaluation ground truth with a temporary shared access key.")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1")
    parser.add_argument("--origin", help="Exact browser origin; network-facing origins require HTTPS.")
    parser.add_argument("--reviewer-label", help="Fix the reviewer label for every session; sign-in then needs only the access key.")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535.")
    origin = args.origin or f"http://127.0.0.1:{args.port}"
    if args.reviewer_label is not None:
        try:
            args.reviewer_label = TypeAdapter(ReviewerLabel).validate_python(args.reviewer_label)
        except ValueError:
            parser.error("Reviewer label must contain 1–500 characters after trimming whitespace.")
    app = create_app(args.data_dir, origin, reviewer_label=args.reviewer_label)
    print(f"Evaluation workspace: {origin}", flush=True)
    print(f"Access key (valid until restart): {app.state.access_key}", flush=True)
    if args.reviewer_label is not None:
        print(f"Reviewer label: {args.reviewer_label} (fixed for this server)", flush=True)
    print("Edits stay in a temporary workspace until Submit changes. Restart discards unsubmitted edits.", flush=True)
    uvicorn.run(app, host=args.host, port=args.port, workers=1, proxy_headers=False, server_header=False, access_log=False)


if __name__ == "__main__":
    main()
