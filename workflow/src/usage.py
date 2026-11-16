"""Read-only run accounting from persisted usage, including failed/retried attempts."""

from __future__ import annotations

import json

FIELDS = {"input": "inputTokens", "output": "outputTokens", "cacheRead": "cachedInputTokens"}


def count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


class CodexUsage:
    """Difference thread totals, not `last` (which is one model request)."""

    def __init__(self):
        self.previous = None
        self.partial = False

    def update(self, usage):
        total, last = usage.get("total"), usage.get("last", {})
        if not total or not all(count(total.get(k)) for k in FIELDS.values()):
            self.partial = True
            return None
        if self.previous is None:
            if not all(count(last.get(k)) for k in FIELDS.values()):
                self.previous, self.partial = total, True
                return None
            previous = {k: max(0, total[k] - last[k]) for k in FIELDS.values()}
        else:
            previous = self.previous
        if any(total[k] < previous[k] for k in FIELDS.values()):
            self.partial = True
            self.previous = total
            return None
        result = {key: total[field] - previous[field] for key, field in FIELDS.items()}
        self.previous = total
        return result


def summarize(events):
    attempts, counters, current, turn = [], {}, None, None
    for event in events:
        kind, payload = event["kind"], event["payload"]
        if kind == "execution.started":
            current = {"canonical": [], "raw": [], "legacy": False,
                       "harness": (payload.get("execution") or {}).get("harness"), "partial": False}
            attempts.append(current)
            turn = None
        elif current is not None:
            if kind == "turn/started":
                turn = payload["turn"]["id"]
            elif kind == "runtime.usage":
                current["canonical"].append(payload)
                current["partial"] |= bool(payload.get("partial"))
                if payload.get("accounting") != "delta-v1" and current["harness"] != "pi":
                    current["legacy"] = True
            elif kind == "thread/tokenUsage/updated":
                counter = counters.setdefault(payload["threadId"], CodexUsage())
                value = counter.update(payload["tokenUsage"])
                if turn and payload.get("turnId") == turn and value is not None:
                    current["raw"].append(value)
                current["partial"] |= counter.partial

    totals = {key: 0 for key in FIELDS}
    known = {key: False for key in FIELDS}
    reported, partial, legacy = 0, False, False
    for attempt in attempts:
        values = attempt["canonical"] or attempt["raw"]
        metered = False
        for value in values:
            if count(value.get("input")) and count(value.get("output")):
                metered = True
            else:
                partial = True
            for key in FIELDS:
                if count(value.get(key)):
                    totals[key] += value[key]
                    known[key] = True
        reported += metered
        partial |= attempt["partial"]
        legacy |= attempt["legacy"]
    warnings = []
    if partial:
        warnings.append("Some token counters were incomplete or reset.")
    if reported < len(attempts):
        warnings.append("Some agent turns have not reported token usage.")
    if legacy:
        warnings.append("Older Codex usage events may undercount tokens; these are recorded partial totals.")
    partial |= legacy or reported < len(attempts)
    return {
        "input_tokens": totals["input"] if known["input"] else None,
        "output_tokens": totals["output"] if known["output"] else None,
        "cached_input_tokens": totals["cacheRead"] if known["cacheRead"] else None,
        "total_tokens": totals["input"] + totals["output"] if known["input"] and known["output"] else None,
        "reported_attempts": reported, "attempts": len(attempts),
        "partial": bool(partial), "warnings": warnings,
    }


def run_usage(store):
    kinds = ("execution.started", "runtime.usage", "turn/started", "thread/tokenUsage/updated")
    rows = store.db.execute(
        f"SELECT kind,payload FROM events WHERE kind IN ({','.join('?' for _ in kinds)}) ORDER BY id", kinds)
    return summarize({"kind": kind, "payload": json.loads(payload)} for kind, payload in rows)
