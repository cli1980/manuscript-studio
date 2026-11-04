import { useEffect, useState } from "react";
import { Works, WorkView } from "./views/Works";
import { Runs } from "./views/Runs";
import { RunView } from "./views/RunView";
import { Chapters } from "./views/Chapters";
import { api, type RunSummary } from "./api";
import { reviewName } from "./views/common";

function useHash() {
  const [hash, setHash] = useState(() => window.location.hash || "#/runs");
  useEffect(() => {
    const update = () => setHash(window.location.hash || "#/runs");
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  return hash;
}

export function App() {
  const parts = useHash().replace(/^#\/?/, "").split("?")[0].split("/").map(decodeURIComponent);
  let view;
  if (parts[0] === "works" && parts[1]) view = <WorkView workId={parts[1]} />;
  else if (parts[0] === "works") view = <Works />;
  else if (parts[0] === "runs" && parts[1] === "new") view = <Runs initialWork={parts[2]} />;
  else if (parts[0] === "runs" && parts[1] && parts[2] === "chapters") view = <Chapters runId={parts[1]} chapterId={parts[3]} />;
  else if (parts[0] === "runs" && parts[1]) view = <RunView runId={parts[1]} />;
  else view = <Runs />;
  return (
    <>
      <header className="top">
        <strong>Manuscript Studio</strong>
        <nav>
          <a href="#/runs" className={parts[0] !== "works" ? "active" : ""}>Workflows</a>
          <a href="#/works" className={parts[0] === "works" ? "active" : ""}>Works</a>
        </nav>
        <span className="muted">Local workspace</span>
      </header>
      <ApprovalNotice />
      <main>{view}</main>
    </>
  );
}

// On every page: chapters waiting for approval, linking straight to the chapter viewer.
function ApprovalNotice() {
  const [waiting, setWaiting] = useState<RunSummary[]>([]);
  useEffect(() => {
    const poll = () => api.runs().then((runs) => setWaiting(runs.filter(
      (r) => r.status === "WAITING_FOR_HUMAN" && !!r.gate_chapter_id && !!r.gate_kind && r.engine_current)))
      .catch(() => undefined);
    void poll();
    const timer = window.setInterval(poll, 8000);
    return () => window.clearInterval(timer);
  }, []);
  if (!waiting.length) return null;
  return (
    <div className="approval-notice">
      {waiting.map((r) => (
        <a key={r.id} href={`#/runs/${r.id}/chapters/${encodeURIComponent(r.gate_chapter_id ?? "")}`}>
          {r.gate_chapter_id} of {r.work_id} {r.gate_kind === "chapter_sanity" ? "is translated and awaits your approval"
            : r.gate_review ? `awaits your review (${reviewName(r.gate_kind ?? "")})`
            : `awaits your decision (${(r.gate_kind ?? "").replaceAll("_", " ")})`} →
        </a>
      ))}
    </div>
  );
}
