import { useEffect, useRef, useState } from "react";
import { api, type Action, type RunDetail, type WorkflowEvent } from "../api";
import { ErrorBox, Status, useLoad, when } from "./common";
import { GatePanel } from "./GatePanel";
import { workflowUI } from "../workflows";
import { runEvents, runState, useLive } from "../live";
import { TokenUsage } from "./TokenUsage";

export function RunView({ runId }: { runId: string }) {
  const { data: run, error, reload, setData } = useLoad(() => api.run(runId), [runId], useLive(runState(runId)));
  // When the workflow makes its decisions elsewhere (translation: the chapter viewer), go there once per decision.
  const ui = workflowUI(run?.workflow);
  const page = run ? ui.decisionPage(run) : null;
  const decisionId = run?.gate?.id ?? run?.acceptance?.acceptance_id;
  useEffect(() => {
    if (!page || !decisionId) return;
    const key = `chapter-gate-opened:${decisionId}`;
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, "1");
    window.location.hash = page;
  }, [page, decisionId]);
  const [actionError, setActionError] = useState<string | null>(null);

  async function perform(operation: () => Promise<RunDetail>) {
    try {
      const next = await operation();
      setActionError(null);
      if (next.id !== runId) window.location.hash = `#/runs/${next.id}`;
      else setData(next);
    } catch (exc) {
      setActionError(exc instanceof Error ? exc.message : String(exc));
      void reload();
    }
  }

  if (!run) return <ErrorBox error={error ?? null} />;
  const actions = Object.fromEntries(run.available_actions.map((a) => [a.action, a])) as Record<string, Action>;
  const live = run.status === "RUNNING" || run.worker.active;
  return (
    <section>
      <p><a href="#/runs">← Workflows</a> · <a href={`#/works/${encodeURIComponent(run.work_id)}`}>Work {run.work_id}</a></p>
      <h1>{run.template_title ?? run.template_id} <span className="mono muted">{run.id.slice(0, 8)}</span></h1>
      {run.finalized && (
        <div className="banner final">This run is final: its output is an accepted version of {run.workflow} on this work and cannot change. Start a new run on the work to publish the next version.</div>
      )}
      {!run.engine_current && run.status !== "COMPLETED" && run.status !== "CANCELLED" && (
        <div className="banner warn">The workflow engine changed after this run was created. Only reading and restarting the workflow are available.</div>
      )}
      {run.superseded_by && <div className="banner">Restarted as <a href={`#/runs/${run.superseded_by}`}>{run.superseded_by.slice(0, 8)}</a>.</div>}
      <div className="facts">
        <div><span>Status</span><Status value={run.status} />{live && <span className="tag busy">agent working</span>}{run.worker.paused && <span className="tag">paused</span>}</div>
        <div><span>Stage</span>{run.stage}{run.chapter_id ? ` · ${run.chapter_id === "_whole" ? "whole-book review" : run.chapter_id}` : ""}</div>
        <div><span>Progress</span>{run.progress ? `${run.progress.completed}/${run.progress.total} chapters` : "—"}</div>
        {run.whole_book_status && <div><span>Whole book</span>{run.whole_book_status.replaceAll("_", " ")}</div>}
        <div><span>Stages</span>{run.stages.map((s) => <span key={s} className={`tag ${s === run.stage ? "busy" : ""}`}>{s}</span>)}</div>
        {!!run.passes?.length && <div><span>Passes</span>{run.passes.map((p) => (
          <span key={p.number} className={`tag ${p.accepted ? "" : "busy"}`}>
            {p.number} · {ui.stageTitle(run, p.stage)} · {p.accepted ? "accepted" : p.completed ? "awaiting acceptance" : "in progress"}
          </span>))}</div>}
        <div><span>Turns</span>{run.attempts}</div>
        {run.execution && <div><span>Execution</span>{run.execution.profile} · {run.execution.harness} ·{" "}
          {run.execution.model} · {run.execution.endpoint ?? "installed provider"}
          <small className="muted"> · {run.execution.sandbox}</small></div>}
        {run.settings?.passage_size && <div><span>Passage size</span>at most {run.settings.passage_size}
          {["zh", "ja", "ko"].includes(run.manuscript_language.split("-")[0].toLowerCase()) ? " characters" : " words"}</div>}
        {ui.hasChapterViewer && <div><span>Chapters</span><a href={`#/runs/${run.id}/chapters`}>Open chapter browser</a></div>}
      </div>
      {run.error && <div className="error"><strong>Last error:</strong> {run.error}</div>}
      {run.worker.error && <div className="error"><strong>Worker:</strong> {run.worker.error}</div>}
      {run.document_path && <p>Formatted document: <span className="mono">{run.document_path}</span></p>}
      {run.handed_off_work && <div className="banner final">The formatted document is now a work of its own, ready for further
        workflows: <a href={`#/works/${encodeURIComponent(run.handed_off_work)}`}>{run.handed_off_work}</a>.</div>}
      {run.export_path && !run.document_path && <p>Export: <span className="mono">{run.export_path}</span></p>}
      {run.finalized && run.template_id !== "manuscript-formatting-v1" && (
        <p><button className="primary" onClick={() => perform(async () => {
          const work = await api.work(run.work_id);
          const publication = work.publications.find((p) => p.run_id === run.id && p.contract === "accepted-markdown-chapters/1");
          if (!publication) throw new Error("This run has no accepted output to format.");
          return api.create({ template_id: "manuscript-formatting-v1", derived: true, work_id: run.work_id,
            publication_id: publication.id, options: { renderer: "word" } });
        })}>Format this output as DOCX</button>
        <span className="muted"> Uses Microsoft Word; choose another renderer or output on the work page.</span></p>
      )}
      <Controls run={run} actions={actions} perform={perform} />
      <ErrorBox error={actionError} />
      <GatePanel run={run} perform={perform} />
      <TokenUsage usage={run.usage} />
      <Timeline runId={runId} />
    </section>
  );
}

function Controls({ run, actions, perform }: { run: RunDetail; actions: Record<string, Action>; perform: (op: () => Promise<RunDetail>) => void }) {
  const disabled = (name: string) => !actions[name]?.enabled;
  const title = (name: string) => actions[name]?.reason ?? actions[name]?.confirmation ?? undefined;
  const confirmed = (name: string) => window.confirm(actions[name]?.confirmation ?? `Run ${name}?`);
  const terminal = run.status === "COMPLETED" || run.status === "CANCELLED";
  return (
    <div className="controls">
      {!terminal && (run.worker.paused
        ? <button onClick={() => perform(() => api.action(run.id, "resume"))}>Resume</button>
        : <button onClick={() => perform(() => api.action(run.id, "pause"))} title="Stop after the current agent turn">Pause after turn</button>)}
      <button disabled={disabled("retry")} title={title("retry")}
        onClick={() => {
          const stopped = run.status === "RUNNING";
          if (!stopped || confirmed("retry")) perform(() => api.action(run.id, "retry", { confirm_stopped: stopped }));
        }}>Retry</button>
      <button disabled={run.status !== "WAITING_FOR_HUMAN" || !!run.finalized} title="Ask the agent for a fresh review revision"
        onClick={() => perform(() => api.action(run.id, "retry", { refresh_gate: true }))}>Refresh review</button>
      <button disabled={disabled("restart_chapter")} title={title("restart_chapter")}
        onClick={() => {
          const chapter = window.prompt("Chapter ID to restart", run.chapter_id === "_whole" ? "" : run.chapter_id ?? "");
          const reason = chapter && window.prompt("Reason for restarting this chapter");
          if (chapter && reason && confirmed("restart_chapter")) perform(() => api.action(run.id, "restart-chapter", { chapter_id: chapter, reason }));
        }}>Restart chapter</button>
      {run.workflow === "literary-translation" && run.whole_book_status && run.whole_book_status !== "pending" && (
        <button disabled={disabled("restart_chapter")} onClick={() => {
          const reason = window.prompt("Reason for restarting whole-book consistency");
          if (reason && window.confirm("Restart whole-book consistency? Completed chapter outputs are kept.")) {
            perform(() => api.action(run.id, "restart-chapter", { chapter_id: "_whole", reason }));
          }
        }}>Restart consistency</button>
      )}
      <button disabled={disabled("restart_stage")} title={title("restart_stage")}
        onClick={() => {
          const stage = window.prompt(`Stage to restart (${run.stages.join(", ")})`, run.stage);
          const reason = stage && window.prompt("Reason for restarting this stage");
          if (stage && reason && confirmed("restart_stage")) perform(() => api.action(run.id, "restart-stage", { stage, reason }));
        }}>Restart stage</button>
      <button disabled={disabled("restart_workflow")} title={title("restart_workflow")}
        onClick={() => {
          const reason = window.prompt("Reason for restarting the workflow");
          if (reason && confirmed("restart_workflow")) perform(() => api.action(run.id, "restart", { reason, confirm_stopped: run.status === "RUNNING" && !run.worker.active }));
        }}>Restart workflow</button>
      <button className="danger" disabled={disabled("stop")} title={title("stop")}
        onClick={() => { if (confirmed("stop")) perform(() => api.action(run.id, "stop")); }}>Stop</button>
    </div>
  );
}

// The run's events, fetched incrementally whenever the live feed reports a new visible one.
function Timeline({ runId }: { runId: string }) {
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const last = useRef(0);
  const changed = useLive(runEvents(runId));
  useEffect(() => { setEvents([]); last.current = 0; }, [runId]);
  useEffect(() => {
    let cancelled = false;
    api.events(runId, last.current).then((page) => {
      if (cancelled) return;
      if (page.events.length) setEvents((old) => [...old, ...page.events].slice(-400));
      last.current = page.last_id;
    }, () => undefined);  // The run view shows load errors.
    return () => { cancelled = true; };
  }, [runId, changed]);
  return (
    <details className="panel">
      <summary><h2>Timeline</h2></summary>
      <ol className="timeline">
        {events.slice().reverse().map((event) => (
          <li key={event.id}>
            <span className="muted">{when(event.created_at)}</span> <strong>{event.kind}</strong>{" "}
            <span className="muted">{summarize(event.payload)}</span>
          </li>
        ))}
      </ol>
    </details>
  );
}

function summarize(payload: Record<string, unknown>) {
  const keys = ["stage", "chapter_id", "outcome", "gate", "error", "field", "reason", "acceptance_id"];
  return keys.filter((k) => payload[k] !== undefined && payload[k] !== null).map((k) => `${k}: ${String(payload[k])}`).join(" · ");
}
