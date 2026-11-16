"""Thin CLI client of the workflow service, exposed through python -m workflow."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .execution import ExecutionProfile
from .runtime import CodexRuntime
from .service import WorkflowService


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def display(engine, state, *, review=False):
    emit(engine.summary(state))
    if engine.retired:
        print("\nThis workflow was removed. Its history and artifacts are read-only; "
              "start a supported workflow to continue.")
        return
    if not review:
        return
    if state.get("gate"):
        gate = state["gate"]
        print("\n" + gate["message"])
        if gate["binding"] and gate["kind"] in ("translation_issue", "chapter_sanity"):
            print("\nSaved English checkpoint:\n" + engine.store.content(gate["binding"]).decode("utf-8"))
        for document in gate.get("documents") or []:
            print(f"\n{document['path']}:\n" + engine.store.content(document).decode("utf-8"))
        if gate.get("documents"):
            print("\nReply '" + "' or '".join(engine.gate_commands(state, gate)) + "' to approve, or provide feedback.")
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
        elif gate.get("options"):
            for option in gate["options"]:
                print(f"- {option['title']}: reply exactly '{option['command']}'"
                      + (f"\n  {option['description']}" if option.get("description") else ""))
        elif gate["kind"] == "metadata_review":
            print("\nEdit: python -m workflow metadata RUN --gate GATE-ID --field /PATH --value-file VALUE.json"
                  "\nEach edit presents a new gate ID. Confirm with a reply containing exactly 'confirm metadata'.")
        elif gate["kind"] == "docx_generation_review":
            print("\n" + state["gate"]["message"])
            print("Authorize the displayed exact plan with: python -m workflow authorize-docx RUN "
                  "--gate GATE-ID --plan-sha256 " + state["production"]["plan_sha256"])
    if state["status"] == "WAITING_FOR_ACCEPTANCE":
        print("\nReview these immutable outputs against the source before accepting.")
        for artifact in state["outputs"]:
            print(f"\nChapter: {artifact['chapter_id']}\nSHA-256: {artifact['sha256']}")
            source = next(chapter for chapter in state["chapters"] if chapter["chapter_id"] == artifact["chapter_id"])
            print("Original:\n" + engine.store.content(state["prepared"]["files"][source["path"]]).decode("utf-8"))
            if artifact.get("content_changed_after_sanity_review"):
                print("Text changed after the approved sanity-review base; inspect the applied changes.")
            print("Accepted candidate:\n" + engine.store.content(artifact).decode("utf-8"))
        print("\nIMPORTANT: " + engine.acceptance_details(state)["notice"])
        print("Accept with: python -m workflow accept RUN --acceptance-id ACCEPTANCE-ID --confirm-final")
    if engine.finalized(state):
        print(f"\nFINAL: this run is finalized; its {state['workflow']} version on work {state['work_id']} can never "
              "change. A new run on the work publishes the next version.")


def show(service, run_id, *, review=False):
    with service.open_run(run_id) as engine:
        display(engine, engine.state(), review=review)


def agent_models(values):
    result = {}
    for value in values or []:
        name, separator, model = value.partition("=")
        if not separator or not name or not model:
            raise ValueError("Use --agent-model AGENT=MODEL.")
        result[name] = model
    return result


def parser():
    result = argparse.ArgumentParser(description="Human-supervised manuscript workflows (CLI client of the service).")
    result.add_argument("--server-root", type=Path, default=Path(".workflow-runs"),
                        help="Server root holding the run/work index, work libraries, and runs.")
    result.add_argument("--owner", help="Owner recorded on new works and runs (default: OS user name).")
    result.add_argument("--execution-profile", type=Path, help="Startup execution profile JSON.")
    result.add_argument("--user-execution-profile", type=Path,
                        help="User JSON overlay for endpoints, models, and default model; requires --execution-profile.")
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("templates", help="List registered workflow templates.")
    sub.add_parser("models", help="Show the startup profile's configured model choices.")
    sub.add_parser("reindex", help="Rebuild the index from work libraries and per-run state.")
    works = sub.add_parser("works", help="Inspect works and their libraries.")
    work_sub = works.add_subparsers(dest="works_command", required=True)
    work_sub.add_parser("list")
    for name in ("show", "verify", "publications"):
        work_sub.add_parser(name).add_argument("work")
    work_metadata = work_sub.add_parser("metadata", help="Show the work's shared metadata or its history.")
    work_metadata.add_argument("work")
    work_metadata.add_argument("--history", action="store_true")
    work_metadata.add_argument("--version", type=int)
    work_edit = work_sub.add_parser("edit-metadata", help="Edit shared metadata while no run is unfinished.")
    work_edit.add_argument("work")
    work_edit.add_argument("--field", required=True)
    work_edit.add_argument("--value-file", required=True, type=Path)
    work_edit.add_argument("--reason", default="Explicit metadata edit.")
    create = sub.add_parser("create", help="Create a run: --source makes a new work; --work uses an existing work.")
    create.add_argument("--template", required=True)
    origin = create.add_mutually_exclusive_group(required=True)
    origin.add_argument("--source", type=Path, help="Upload a manuscript; always creates a new work.")
    origin.add_argument("--work", help="Start this workflow on an existing work.")
    create.add_argument("--manuscript-language", help="Optional language hint; preparation detects it when omitted.")
    create.add_argument("--model", help="Configured model key with --execution-profile; otherwise a runtime model ID.")
    create.add_argument("--agent-model", action="append", metavar="AGENT=MODEL", help="Model for one agent.")
    create.add_argument("--passage-size", type=int, metavar="N",
                        help="Maximum passage size for this run (characters for CJK text, else words); "
                             "default from the template.")
    runs = sub.add_parser("runs", help="List runs.")
    runs.add_argument("--work")
    metadata = sub.add_parser("metadata", help="Edit one shared metadata field of a run.")
    metadata.add_argument("run")
    metadata.add_argument("--gate", help="The metadata review gate ID, when the run waits at that gate.")
    metadata.add_argument("--field", required=True, help="Metadata field path, such as /genres or /edition/label.")
    metadata.add_argument("--value-file", required=True, type=Path, help="UTF-8 JSON value, including null or [].")
    metadata.add_argument("--reason", default="Explicit metadata edit.")
    history = sub.add_parser("metadata-history", help="List a run's metadata versions or show one.")
    history.add_argument("run")
    history.add_argument("--version", type=int)
    for command in ("step", "status", "review", "reply", "accept", "authorize-docx", "retry", "stop", "events",
                    "restart-stage", "restart-chapter", "restart"):
        child = sub.add_parser(command)
        child.add_argument("run")
        if command == "step":
            child.add_argument("--codex", default="codex", help="Codex executable path (not a shell command).")
            child.add_argument("--timeout", type=float, default=900)
        elif command == "reply":
            child.add_argument("--gate", required=True)
            child.add_argument("--response-file", required=True, type=Path)
        elif command == "authorize-docx":
            child.add_argument("--gate", required=True)
            child.add_argument("--plan-sha256", required=True)
        elif command == "accept":
            child.add_argument("--acceptance-id", required=True)
            child.add_argument("--confirm-final", action="store_true",
                               help="Confirm the displayed manuscript-approval or finalization notice.")
        elif command == "retry":
            child.add_argument("--confirm-stopped", action="store_true")
            child.add_argument("--refresh-gate", action="store_true")
        elif command == "events":
            child.add_argument("--after", type=int, default=0)
        elif command.startswith("restart"):
            child.add_argument("--reason", required=True)
            if command == "restart-stage":
                child.add_argument("--stage", required=True)
            elif command == "restart-chapter":
                child.add_argument("--chapter", required=True)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        profile = ExecutionProfile.load(args.execution_profile, args.user_execution_profile)
        with WorkflowService(args.server_root, owner=args.owner, execution_profile=profile) as service:
            return run(service, args)
    except ModuleNotFoundError as exc:
        print(f"workflow: missing dependency ({exc}); install workflow/requirements-docx.txt for native formatting.",
              file=sys.stderr)
        return 1
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(f"workflow: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("workflow: interrupted; the run remains paused with its recorded state.", file=sys.stderr)
        return 130


def run(service, args):
    command = args.command
    if command == "models":
        emit(service.execution_profile.public() if service.execution_profile else
             {"name": "codex-default", "harness": "codex", "models": []})
        return 0
    if command == "templates":
        emit(service.list_templates())
    elif command == "reindex":
        emit(service.reindex())
    elif command == "works":
        sub = args.works_command
        if sub == "list":
            emit(service.list_works())
        elif sub == "show":
            emit(service.get_work(args.work))
        elif sub == "verify":
            emit(service.verify_work(args.work))
        elif sub == "publications":
            emit(service.work_publications(args.work))
        elif sub == "metadata":
            emit(service.work_metadata_version(args.work, args.version) if args.version is not None else
                 service.work_metadata_history(args.work) if args.history else service.get_work_metadata(args.work))
        else:
            value = json.loads(args.value_file.read_text(encoding="utf-8-sig"))
            emit(service.edit_work_metadata(args.work, args.field, value, args.reason))
    elif command == "create":
        run_id = service.create_run(args.template, upload=args.source, work_id=args.work,
                                    manuscript_language=args.manuscript_language, model=args.model,
                                    agent_models=agent_models(args.agent_model),
                                    settings={"passage_size": args.passage_size} if args.passage_size else None)
        show(service, run_id)
        profile_option = f' --execution-profile "{args.execution_profile}"' if args.execution_profile else ""
        if args.user_execution_profile:
            profile_option += f' --user-execution-profile "{args.user_execution_profile}"'
        print(f'\nNext: python -m workflow --server-root "{service.root}"{profile_option} step {run_id}')
    elif command == "runs":
        emit(service.list_runs(work_id=args.work))
    elif command == "events":
        for event in service.events(args.run, args.after):
            print(json.dumps(event, ensure_ascii=False))
    elif command == "metadata-history":
        emit(service.metadata_version(args.run, args.version) if args.version is not None else
             service.metadata_history(args.run))
    elif command == "status":
        emit(service.get_run(args.run))
    elif command == "review":
        show(service, args.run, review=True)
    else:
        review = False
        if command == "step":
            if args.timeout <= 0:
                raise ValueError("Timeout must be positive.")
            profile = service.execution_profile
            if profile and (args.codex != "codex" or args.timeout != 900):
                raise ValueError("With --execution-profile, configure command and timeout in that profile.")
            with service.open_run(args.run) as engine:
                kind = engine._stage_or_empty(engine.state()).get("kind")
            if not profile and kind == "agent" and shutil.which(args.codex) is None:
                raise ValueError("Codex executable not found. Install/sign in to Codex or pass --codex PATH.")
            runtime = None
            if kind == "agent":
                runtime = profile.runtime() if profile else CodexRuntime([args.codex, "app-server"], args.timeout)
            service.step(args.run, runtime)
        elif command == "metadata":
            value = json.loads(args.value_file.read_text(encoding="utf-8-sig"))
            service.edit_metadata(args.run, args.field, value, args.reason, gate_id=args.gate)
            review = True
        elif command == "reply":
            service.reply(args.run, args.gate, args.response_file.read_text(encoding="utf-8"))
        elif command == "authorize-docx":
            service.authorize_docx(args.run, args.gate, args.plan_sha256)
        elif command == "accept":
            service.accept(args.run, args.acceptance_id, confirm_final=args.confirm_final)
        elif command == "retry":
            service.retry(args.run, confirm_stopped=args.confirm_stopped, refresh_gate=args.refresh_gate)
        elif command == "stop":
            service.stop(args.run)
        elif command == "restart-stage":
            service.restart_stage(args.run, args.stage, reason=args.reason)
        elif command == "restart-chapter":
            service.restart_chapter(args.run, args.chapter, reason=args.reason)
        elif command == "restart":
            new_id = service.restart_workflow(args.run, reason=args.reason)
            print(f"Run {args.run} stopped; restarted as {new_id}.")
            args.run = new_id
        show(service, args.run, review=review)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
