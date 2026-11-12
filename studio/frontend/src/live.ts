import { useSyncExternalStore } from "react";
import { api, type LiveSnapshot } from "./api";

// One change feed for the whole page. The server pushes fingerprints of every run and work when they change
// (server-sent events); pages refetch only the data whose fingerprint moved, instead of polling on timers. If the
// stream stays silent (for example behind a buffering proxy), the feed falls back to polling the small snapshot.

const SILENCE_MS = 40_000;  // The server pings every 15 seconds.
const POLL_MS = 3_000;

let snapshot: LiveSnapshot | null = null;
let started = false;
const listeners = new Set<() => void>();

function publish(next: LiveSnapshot) {
  snapshot = next;
  listeners.forEach((listener) => listener());
}

function connect() {
  const source = new EventSource("/api/live/stream");
  let watchdog = window.setTimeout(fallBack, SILENCE_MS);
  const alive = () => {
    window.clearTimeout(watchdog);
    watchdog = window.setTimeout(fallBack, SILENCE_MS);
  };
  source.onmessage = (event) => { alive(); publish(JSON.parse(event.data) as LiveSnapshot); };
  source.addEventListener("ping", alive);
  function fallBack() {
    source.close();
    const poll = () => api.live().then(publish, () => undefined);
    void poll();
    window.setInterval(poll, POLL_MS);
  }
}

function subscribe(listener: () => void) {
  if (!started) {
    started = true;
    connect();
  }
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

/** A string that changes whenever the selected part of the server's state changes; null before the first snapshot. */
export function useLive(select: (live: LiveSnapshot) => string): string | null {
  return useSyncExternalStore(subscribe, () => (snapshot ? select(snapshot) : null));
}

const runKey = (run: LiveSnapshot["runs"][string] | undefined) => (run ? `${run.revision}|${JSON.stringify(run.worker)}` : "");

/** One run's state: its saved revision and its worker (agent working, paused, stopped). */
export const runState = (runId: string) => (live: LiveSnapshot) => runKey(live.runs[runId]);

/** One run's timeline: its last event shown by default. */
export const runEvents = (runId: string) => (live: LiveSnapshot) => String(live.runs[runId]?.event ?? 0);

/** Every run's state, including runs being added. */
export const allRuns = (live: LiveSnapshot) =>
  Object.keys(live.runs).sort().map((id) => `${id}:${runKey(live.runs[id])}`).join(",");

/** Every work's publication log, and every run (work pages list their runs). */
export const allWorks = (live: LiveSnapshot) =>
  `${Object.keys(live.works).sort().map((id) => `${id}:${live.works[id]}`).join(",")}|${allRuns(live)}`;
