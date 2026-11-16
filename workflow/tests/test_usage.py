"""Usage accounting must count inference requests, not context size or repeated telemetry."""

import unittest

from ..src.usage import CodexUsage, summarize


def event(kind, **payload):
    return {"kind": kind, "payload": payload}


def snapshot(input, output, cached):
    return {"inputTokens": input, "outputTokens": output, "cachedInputTokens": cached}


class UsageTests(unittest.TestCase):
    def test_codex_request_counts_decrease_but_thread_totals_accumulate(self):
        counter = CodexUsage()
        first = {"total": snapshot(1100, 110, 600), "last": snapshot(100, 10, 50)}
        second = {"total": snapshot(1140, 117, 620), "last": snapshot(40, 7, 20)}
        self.assertEqual(counter.update(first), {"input": 100, "output": 10, "cacheRead": 50})
        self.assertEqual(counter.update(first), {"input": 0, "output": 0, "cacheRead": 0})
        self.assertEqual(counter.update(second), {"input": 40, "output": 7, "cacheRead": 20})
        self.assertFalse(counter.partial)

    def test_resumed_threads_do_not_count_previous_run_usage(self):
        counter = CodexUsage()
        self.assertEqual(counter.update({"total": snapshot(10000, 500, 8000),
                                         "last": snapshot(200, 20, 150)}),
                         {"input": 200, "output": 20, "cacheRead": 150})
        self.assertIsNone(counter.update({"total": snapshot(50, 10, 0), "last": snapshot(50, 10, 0)}))
        self.assertTrue(counter.partial)

    def test_all_attempts_count_including_failures_and_retries_without_cache_double_counting(self):
        events = [
            event("execution.started", execution={"harness": "pi"}),
            event("runtime.usage", input=100, output=10, cacheRead=80),
            event("runtime.usage", input=200, output=20, cacheRead=150),
            event("execution.failed"),
            event("execution.started", execution={"harness": "codex"}),
            event("runtime.usage", accounting="delta-v1", input=50, output=5, cacheRead=30),
            event("execution.result"),
        ]
        usage = summarize(events)
        self.assertEqual((usage["input_tokens"], usage["output_tokens"], usage["cached_input_tokens"],
                          usage["total_tokens"]), (350, 35, 260, 385))
        self.assertEqual((usage["reported_attempts"], usage["attempts"]), (2, 2))
        self.assertFalse(usage["partial"])

    def test_unknown_usage_is_not_fabricated_as_zero_and_legacy_codex_is_flagged(self):
        self.assertIsNone(summarize([])["total_tokens"])
        events = [event("execution.started"), event("runtime.usage", input=100, output=10, cacheRead=80),
                  event("execution.started")]
        usage = summarize(events)
        self.assertEqual(usage["total_tokens"], 110)
        self.assertTrue(usage["partial"])
        self.assertEqual(len(usage["warnings"]), 2)
        self.assertEqual(usage["reported_attempts"], 1)
        zero = summarize([event("execution.started"),
                          event("runtime.usage", accounting="delta-v1", input=0, output=0, cacheRead=0)])
        self.assertEqual(zero["total_tokens"], 0)
        self.assertFalse(zero["partial"])

    def test_old_raw_codex_events_deduplicate_resume_and_repeated_usage(self):
        first = {"total": snapshot(100, 10, 80), "last": snapshot(100, 10, 80)}
        second = {"total": snapshot(140, 17, 100), "last": snapshot(40, 7, 20)}
        events = [
            event("execution.started"),
            event("turn/started", turn={"id": "one"}),
            event("thread/tokenUsage/updated", threadId="thread", turnId="one", tokenUsage=first),
            event("thread/tokenUsage/updated", threadId="thread", turnId="one", tokenUsage=first),
            event("execution.started"),
            event("thread/tokenUsage/updated", threadId="thread", turnId="one", tokenUsage=first),
            event("turn/started", turn={"id": "two"}),
            event("thread/tokenUsage/updated", threadId="thread", turnId="two", tokenUsage=second),
        ]
        usage = summarize(events)
        self.assertEqual((usage["input_tokens"], usage["output_tokens"], usage["total_tokens"]), (140, 17, 157))
        self.assertFalse(usage["partial"])

    def test_partial_provider_counters_are_labeled(self):
        usage = summarize([event("execution.started"),
                           event("runtime.usage", accounting="delta-v1", input=40, output=5, partial=True)])
        self.assertTrue(usage["partial"])


if __name__ == "__main__":
    unittest.main()
