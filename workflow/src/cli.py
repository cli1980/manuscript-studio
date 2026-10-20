"""CLI implementation, exposed through python -m workflow."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .engine import DEFAULT_DEFINITION, Engine
from .runtime import CodexRuntime


def display(engine, state, *, review=False):
    summary = {key: state.get(key) for key in
               ("id", "status", "stage", "chapter_index", "attempts", "error", "export_path")}
    if state.get("gate"):
        summary["gate_id"] = state["gate"]["id"]
        summary["gate_kind"] = state["gate"]["kind"]
    if state.get("acceptance_id"):
        summary["acceptance_id"] = state["acceptance_id"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not review:
        return
    if state.get("gate"):
        gate = state["gate"]
        print("\n" + gate["message"])
        if gate["binding"] and gate["kind"] in ("translation_issue", "chapter_sanity"):
            print("\nSaved English checkpoint:\n" + engine.store.content(gate["binding"]).decode("utf-8"))
        if gate["sheet"]:
            sheet = json.loads(engine.store.content(gate["sheet"]))
            print(f"\nApproval sheet: {sheet['sheet_id']}\nRevision: {sheet['revision']}")
            decisions = {d["id"]: d for d in sheet["decisions"]}
            for item in sheet["items"]:
                print(f"\n{item['id']} [{item['status']}]: {item['summary']}")
                for row in item["details"]:
                    print(f"{row['label']}:\n{row['value']}")
                if item["status"] != "resolved":
                    print("Commands: " + "; ".join(
                        decisions[key]["command"] + (" (note required)" if decisions[key]["requires_note"] else "")
                        for key in item["allowed_decisions"]))
            if all(item["status"] == "resolved" for item in sheet["items"]):
                print("Closure command: " + sheet["submission"]["closure_command"])
            print("\nReply with explicit item lines, bound to the displayed gate ID.")
        elif gate["kind"] == "chapter_sanity":
            print("\nReply 'approve chapter' to approve the empty-diff chapter review, or provide feedback.")
    if state["status"] == "WAITING_FOR_ACCEPTANCE":
        print("\nReview these immutable English outputs against the source before accepting.")
        for artifact in state["outputs"]:
            print(f"\nChapter: {artifact['chapter_id']}\nSHA-256: {artifact['sha256']}")
            source = next(chapter for chapter in state["chapters"] if chapter["chapter_id"] == artifact["chapter_id"])
            print("Original:\n" + engine.store.content(state["prepared"]["files"][source["path"]]).decode("utf-8"))
            if artifact["content_changed_after_sanity_review"]:
                print("Text changed after the approved sanity-review base; inspect the applied changes.")
            print("English:\n" + engine.store.content(artifact).decode("utf-8"))


def parser():
    result = argparse.ArgumentParser(description="Human-supervised literary translation workflow (CLI prototype).")
    sub = result.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="Snapshot one source file and pin the skill bundle.")
    create.add_argument("run_dir", type=Path)
    create.add_argument("--source", type=Path, required=True)
    create.add_argument("--source-language", required=True)
    create.add_argument("--definition", type=Path, default=DEFAULT_DEFINITION)
    create.add_argument("--model")
    for command in ("step", "status", "review", "reply", "accept", "recover", "cancel", "events"):
        child = sub.add_parser(command)
        child.add_argument("run_dir", type=Path)
        if command == "step":
            child.add_argument("--codex", default="codex", help="Codex executable path (not a shell command).")
            child.add_argument("--timeout", type=float, default=900)
        elif command == "reply":
            child.add_argument("--gate", required=True)
            child.add_argument("--response-file", required=True, type=Path)
        elif command == "accept":
            child.add_argument("--acceptance-id", required=True)
        elif command == "recover":
            child.add_argument("--confirm-stopped", action="store_true")
            child.add_argument("--refresh-gate", action="store_true")
        elif command == "events":
            child.add_argument("--after", type=int, default=0)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    engine = None
    try:
        if args.command == "create":
            engine = Engine.create(args.run_dir, args.source, args.source_language,
                                   definition=args.definition, model=args.model)
            display(engine, engine.state())
            return 0
        engine = Engine(args.run_dir)
        if args.command == "step":
            if args.timeout <= 0:
                raise ValueError("Timeout must be positive.")
            if engine.state()["stage"] != "export" and shutil.which(args.codex) is None:
                raise ValueError("Codex executable not found. Install/sign in to Codex or pass --codex PATH.")
            state = engine.advance(CodexRuntime([args.codex, "app-server"], args.timeout))
        elif args.command == "reply":
            state = engine.reply(args.gate, args.response_file.read_text(encoding="utf-8"))
        elif args.command == "accept":
            state = engine.accept(args.acceptance_id)
        elif args.command == "recover":
            state = engine.recover(confirm_stopped=args.confirm_stopped, refresh_gate=args.refresh_gate)
        elif args.command == "cancel":
            state = engine.cancel()
        elif args.command == "events":
            for event in engine.store.events(args.after):
                print(json.dumps(event, ensure_ascii=False))
            return 0
        else:
            state = engine.state()
        display(engine, state, review=args.command == "review")
        return 0
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(f"workflow: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("workflow: interrupted; the run remains paused with its recorded state.", file=sys.stderr)
        return 130
    finally:
        if engine:
            engine.close()


if __name__ == "__main__":
    raise SystemExit(main())
