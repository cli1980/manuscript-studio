"""Read-only timing/token analysis of an existing workflow run; no model calls."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time

KINDS = (
    "execution.started", "execution.thread", "execution.result", "execution.failed",
    "thread/started", "turn/started", "turn/completed", "thread/tokenUsage/updated",
    "item/started", "item/completed", "review.received", "e2e.delegated_approval", "artifacts.accepted",
)
TOOL_TYPES = {"commandExecution", "fileChange", "mcpToolCall", "dynamicToolCall", "webSearch"}
TOKEN_FIELDS = ("inputTokens", "cachedInputTokens", "outputTokens", "reasoningOutputTokens")


def union_seconds(spans):
    total, end = 0.0, float("-inf")
    for lo, hi in sorted(spans):
        total += max(0.0, hi - max(lo, end))
        end = max(end, hi)
    return total


def work_category(stage, input_gate, receipt_type, output_gate):
    """Classify the work following a receipt, not just the gate it produces."""
    if stage == "prepare":
        return "preparation"
    if input_gate == "passage_map":
        return ("drafting_and_source_review" if receipt_type == "final-closure"
                else "map_decision_recording")
    if input_gate == "translation_issue":
        return "issue_application_and_finalization_mixed"
    if input_gate == "continuation":
        return "chapter_sanity_review" if output_gate == "chapter_sanity" else "next_passage_drafting_and_review"
    if input_gate == "chapter_sanity":
        return ("approved_chapter_delivery" if receipt_type == "final-closure"
                else "sanity_decision_application_mixed")
    return "chapter_context_and_passage_map" if input_gate is None else "other_followup"


def analyze(events, state, captured_at):
    attempts, current, prior_usage, models = [], None, {}, {}
    receipts = {r["id"]: r for r in state.get("receipts", [])}
    pending_receipt, last_result = None, None
    submission_starts, approval_timings = {}, []
    for event in events:
        timestamp = datetime.fromisoformat(event["created_at"]).timestamp()
        kind, payload = event["kind"], event["payload"]
        if kind == "e2e.delegated_approval":
            submission_starts[payload.get("gate_id", payload.get("acceptance_id"))] = timestamp
        elif kind == "review.received":
            pending_receipt = receipts.get(payload["receipt_id"])
            if pending_receipt and pending_receipt.get("decision_source") == "delegated-automation":
                started = submission_starts.get(payload["gate_id"])
                approval_timings.append({
                    "gate": pending_receipt["gate"]["kind"],
                    "item_count": len(pending_receipt["parsed"].get("dispositions", [])),
                    "result_to_receipt_seconds": timestamp - last_result if last_result is not None else None,
                    "submission_seconds": timestamp - started if started is not None else None,
                })
        elif kind == "artifacts.accepted" and payload.get("decision_source") == "delegated-automation":
            started = submission_starts.get(payload["id"])
            approval_timings.append({
                "gate": "artifact_acceptance", "item_count": 0, "result_to_receipt_seconds": None,
                "submission_seconds": timestamp - started if started is not None else None,
            })
        if kind == "thread/started":
            thread = payload["thread"]
            models[thread["id"]] = thread.get("model")
        if kind == "execution.started":
            current = {
                "attempt": len(attempts) + 1, "stage": payload["stage"], "start": timestamp,
                "end": None, "turn_start": None, "turn_end": None, "thread_id": None,
                "turn_id": None, "outcome": "in_progress", "gate": None, "tools": {},
                "spans": [], "tool_count": 0, "failed_commands": 0,
                "tokens": dict.fromkeys(TOKEN_FIELDS, 0), "usage_updates": 0,
                "context_samples": [], "agent_message_chars": 0,
                "command_chars": 0, "command_output_chars": 0, "file_diff_chars": 0,
                "input_gate": pending_receipt["gate"]["kind"] if pending_receipt else None,
                "input_receipt_type": pending_receipt["parsed"]["type"] if pending_receipt else None,
            }
            attempts.append(current)
            pending_receipt = None
        if current is None:
            continue
        if kind == "execution.thread":
            current["thread_id"] = payload["thread_id"]
        elif kind == "turn/started":
            current["turn_start"] = timestamp
            current["turn_id"] = payload["turn"]["id"]
        elif kind == "turn/completed" and payload["turn"]["id"] == current["turn_id"]:
            current["turn_end"] = timestamp
        elif kind in ("execution.result", "execution.failed"):
            current["end"] = timestamp
            current["outcome"] = payload.get("outcome", "failed")
            current["gate"] = payload.get("gate")
            if kind == "execution.result":
                last_result = timestamp
        elif kind == "thread/tokenUsage/updated":
            thread = payload["threadId"]
            total = payload["tokenUsage"]["total"]
            previous = prior_usage.get(thread, {})
            delta = {key: max(0, total.get(key, 0) - previous.get(key, 0)) for key in TOKEN_FIELDS}
            prior_usage[thread] = total
            if payload.get("turnId") == current["turn_id"] and any(delta.values()):
                current["usage_updates"] += 1
                for key, value in delta.items():
                    current["tokens"][key] += value
                sample = payload["tokenUsage"].get("last", {}).get("inputTokens")
                if sample is not None:
                    current["context_samples"].append(sample)
        elif kind.startswith("item/") and payload.get("turnId") == current["turn_id"]:
            item = payload["item"]
            if kind == "item/started" and item.get("type") in TOOL_TYPES:
                current["tools"].setdefault(item["id"], timestamp)
            elif kind == "item/completed":
                started = current["tools"].pop(item.get("id"), None)
                if started is not None:
                    current["spans"].append((started, timestamp))
                    current["tool_count"] += 1
                if item.get("type") == "agentMessage":
                    current["agent_message_chars"] += len(item.get("text") or "")
                elif item.get("type") == "commandExecution":
                    current["command_chars"] += len(item.get("command") or "")
                    current["command_output_chars"] += len(item.get("aggregatedOutput") or "")
                    current["failed_commands"] += item.get("exitCode") not in (None, 0)
                elif item.get("type") == "fileChange":
                    current["file_diff_chars"] += sum(len(change.get("diff") or "")
                                                     for change in item.get("changes", []))

    now = captured_at.timestamp()
    turns = []
    for attempt in attempts:
        end = attempt["end"] if attempt["end"] is not None else now
        start = attempt["turn_start"]
        turn_end = attempt["turn_end"] if attempt["turn_end"] is not None else end
        spans = attempt["spans"] + [(t, turn_end) for t in attempt["tools"].values()]
        tools = union_seconds([(max(start, lo), min(turn_end, hi)) for lo, hi in spans
                               if start is not None and hi >= start and lo <= turn_end])
        runtime = max(0, turn_end - start) if start is not None else None
        measured = {
            "wall_seconds": max(0, end - attempt["start"]),
            "startup_seconds": start - attempt["start"] if start is not None else None,
            "runtime_seconds": runtime,
            "tool_seconds": tools if runtime is not None else None,
            "runtime_non_tool_seconds": max(0, runtime - tools) if runtime is not None else None,
            "post_turn_seconds": end - attempt["turn_end"] if attempt["end"] is not None and attempt["turn_end"] is not None else None,
        }
        entry = {key: value for key, value in attempt.items()
                 if key not in ("start", "end", "turn_start", "turn_end", "tools", "spans", "context_samples")}
        entry.update({key: round(value, 3) if value is not None else None for key, value in measured.items()})
        entry["model"] = models.get(attempt["thread_id"])
        entry["finished"] = attempt["end"] is not None
        entry["context_first_input_tokens"] = next(iter(attempt["context_samples"]), None)
        entry["context_last_input_tokens"] = attempt["context_samples"][-1] if attempt["context_samples"] else None
        entry["context_max_input_tokens"] = max(attempt["context_samples"], default=None)
        entry["cached_input_percent"] = round(
            100 * attempt["tokens"]["cachedInputTokens"] / max(1, attempt["tokens"]["inputTokens"]), 2)
        entry["work_category"] = (work_category(entry["stage"], entry["input_gate"],
                                               entry["input_receipt_type"], entry["gate"])
                                  if entry["finished"] else "in_progress")
        turns.append(entry)
    finished = [turn for turn in turns if turn["finished"]]
    totals = {key: round(sum(turn[key] or 0 for turn in finished), 3) for key in
              ("wall_seconds", "startup_seconds", "runtime_seconds", "tool_seconds",
               "runtime_non_tool_seconds", "post_turn_seconds")}
    totals["tokens"] = {key: sum(turn["tokens"][key] for turn in finished) for key in TOKEN_FIELDS}
    totals["cached_input_percent"] = round(
        100 * totals["tokens"]["cachedInputTokens"] / max(1, totals["tokens"]["inputTokens"]), 2)
    totals["uncached_input_tokens"] = totals["tokens"]["inputTokens"] - totals["tokens"]["cachedInputTokens"]
    totals["context_max_input_tokens"] = max((t["context_max_input_tokens"] or 0 for t in finished), default=0)
    totals["usage_updates"] = sum(t["usage_updates"] for t in finished)
    if finished:
        span = max(a["end"] for a in attempts if a["end"] is not None) - attempts[0]["start"]
        totals["between_attempts_seconds"] = round(max(0, span - totals["wall_seconds"]), 3)
    else:
        totals["between_attempts_seconds"] = 0
    groups = {}
    for turn in finished:
        name = turn["stage"] + "/" + (turn["gate"] or turn["outcome"])
        group = groups.setdefault(name, {"turns": 0, "wall_seconds": 0, "output_tokens": 0})
        group["turns"] += 1
        group["wall_seconds"] += turn["wall_seconds"]
        group["output_tokens"] += turn["tokens"]["outputTokens"]
    for group in groups.values():
        group["wall_seconds"] = round(group["wall_seconds"], 3)
        group["mean_seconds"] = round(group["wall_seconds"] / group["turns"], 3)
    work_groups = {}
    for turn in finished:
        group = work_groups.setdefault(turn["work_category"], {"turns": 0, "wall_seconds": 0, "output_tokens": 0})
        group["turns"] += 1
        group["wall_seconds"] += turn["wall_seconds"]
        group["output_tokens"] += turn["tokens"]["outputTokens"]
    for group in work_groups.values():
        group["wall_seconds"] = round(group["wall_seconds"], 3)
        group["mean_seconds"] = round(group["wall_seconds"] / group["turns"], 3)
    return {
        "captured_at": captured_at.isoformat(), "run_id": state["id"],
        "status": state["status"], "stage": state["stage"],
        "completed_units": len(state["outputs"]), "total_units": len(state["chapters"]),
        "finished_attempts": len(finished), "completed_attempt_totals": totals,
        "phase_groups": groups, "work_groups": work_groups, "attempts": turns,
        "delegated_approval_timing": {
            "count": len(approval_timings),
            "submission_seconds": round(sum(a["submission_seconds"] or 0 for a in approval_timings), 3),
            "result_to_receipt_seconds": round(sum(a["result_to_receipt_seconds"] or 0 for a in approval_timings), 3),
            "batches": approval_timings,
        },
        "measurement_limits": [
            "Runtime non-tool time includes inference, generation, provider/network waits and local event handling; it is not pure model computation.",
            "Item intervals are observer timestamps; overlapping tool intervals are unioned, not added twice.",
            "Token counts are differences of observed cumulative counters per thread, not a sum of cumulative snapshots.",
            "Input tokens include repeated cached context across model requests; they are not unique manuscript tokens.",
            "Reasoning output tokens are a subset of output tokens and are not added to that total.",
            "Timing/token data for active attempts is provisional and excluded from completed-attempt totals.",
            "Provider queue/prefill timings and per-event SQLite write costs were not instrumented in this run.",
            "Work categories are inferred from the incoming receipt and resulting gate. Drafting and source review share a turn; their individual durations are not observable.",
            "Issue application/finalization and sanity-decision application can include substantive review; they are not pure approval overhead.",
            "Delegated submission time is the launcher event-to-receipt interval; result-to-receipt time additionally includes presentation and orchestration.",
        ],
    }


def inspect_run(run):
    run = Path(run).resolve()
    with sqlite3.connect((run / "state.sqlite3").as_uri() + "?mode=ro", uri=True, timeout=5) as connection:
        connection.execute("BEGIN")
        state = json.loads(connection.execute("SELECT state FROM run WHERE id=1").fetchone()[0])
        rows = connection.execute(
            "SELECT created_at,kind,payload FROM events WHERE kind IN (" + ",".join("?" for _ in KINDS) + ") ORDER BY id",
            KINDS,
        ).fetchall()
        latest = connection.execute("SELECT created_at,kind FROM events ORDER BY id DESC LIMIT 1").fetchone()
        counts = dict(connection.execute("SELECT kind,count(*) FROM events GROUP BY kind").fetchall())
    events = [{"created_at": at, "kind": kind, "payload": json.loads(payload)} for at, kind, payload in rows]
    report = analyze(events, state, datetime.now(timezone.utc))
    report["event_counts"] = counts
    report["latest_event"] = {"created_at": latest[0], "kind": latest[1]} if latest else None
    report["database_bytes"] = (run / "state.sqlite3").stat().st_size
    return report


def display(report, *, tail=None):
    totals = report["completed_attempt_totals"]
    print(f"\n{report['captured_at']} {report['status']} | "
          f"{report['completed_units']}/{report['total_units']} units | {report['finished_attempts']} finished turns")
    print(f"Finished-turn time: {totals['wall_seconds']/60:.1f} min; "
          f"tools {totals['tool_seconds']:.1f}s; startup {totals['startup_seconds']:.1f}s; "
          f"non-tool runtime {totals['runtime_non_tool_seconds']/60:.1f} min; "
          f"post-turn {totals['post_turn_seconds']:.1f}s.")
    print(f"Tokens: input {totals['tokens']['inputTokens']:,} ({totals['cached_input_percent']}% cached), "
          f"output {totals['tokens']['outputTokens']:,}; largest context {totals['context_max_input_tokens']:,}.")
    approvals = report["delegated_approval_timing"]
    print(f"Delegated approvals: {approvals['count']}; submit/validate {approvals['submission_seconds']:.1f}s; "
          f"result-to-receipt {approvals['result_to_receipt_seconds']:.1f}s.")
    if not tail:
        print("Work following model inputs (finished turns):")
        for name, group in report["work_groups"].items():
            print(f"  {name}: {group['turns']} turns, {group['wall_seconds']/60:.2f} min")
    print("Turn  Phase                         Wall(s) Tool(s) Non-tool(s) Output tokens  Last context")
    for turn in report["attempts"][-tail:] if tail else report["attempts"]:
        phase = turn["stage"] + "/" + (turn["gate"] or turn["outcome"])
        print(f"{turn['attempt']:4}  {phase:29} {turn['wall_seconds']:7.1f} "
              f"{turn['tool_seconds'] or 0:7.1f} {turn['runtime_non_tool_seconds'] or 0:11.1f} "
              f"{turn['tokens']['outputTokens']:13,} {turn['context_last_input_tokens'] or 0:13,}"
              + ("" if turn["finished"] else " (active)"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path, help="Optional performance JSON; database is never changed.")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--duration", type=float, default=0, help="Watch limit in seconds; 0 means until stopped.")
    args = parser.parse_args(argv)
    if not 1 <= args.interval <= 3600 or not 0 <= args.duration < float("inf"):
        parser.error("Interval must be 1–3600 seconds; duration must be nonnegative and finite.")
    deadline = time.monotonic() + args.duration if args.duration else float("inf")
    try:
        while True:
            report = inspect_run(args.run_dir)
            display(report, tail=3 if args.watch else None)
            if args.output:
                with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=False) as handle:
                    temporary = Path(handle.name)
                    handle.write((json.dumps(report, indent=2) + "\n").encode("utf-8"))
                try:
                    os.replace(temporary, args.output)
                finally:
                    temporary.unlink(missing_ok=True)
            if not args.watch or report["status"] in ("COMPLETED", "FAILED", "BLOCKED", "PAUSED", "CANCELLED"):
                return 0
            if time.monotonic() + args.interval > deadline:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0  # Monitoring stops; the workflow process is untouched.
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Performance monitor: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
