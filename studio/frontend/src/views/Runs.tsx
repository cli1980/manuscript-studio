import { useState } from "react";
import { api } from "../api";
import { ErrorBox, reviewName, Status, useLoad, when } from "./common";
import { workflowUI } from "../workflows";
import { allRuns, useLive } from "../live";

const PENDING: Record<string, string> = {
  WAITING_FOR_HUMAN: "Your review", WAITING_FOR_ACCEPTANCE: "Final acceptance", BLOCKED: "Resolve blocker",
  FAILED: "Retry or restart", PAUSED: "Resume", READY: "Ready to run", RUNNING: "Agent working",
};

// Workflow dashboard: every run with what it is doing and what it needs from the user.
export function Runs({ initialWork }: { initialWork?: string }) {
  const { data, error } = useLoad(api.runs, [], useLive(allRuns));
  return (
    <section>
      <h1>Workflows</h1>
      <NewRun initialWork={initialWork} />
      <h2>Runs</h2>
      <ErrorBox error={error} />
      {data && data.length === 0 && <p className="muted">No runs yet.</p>}
      {data && data.length > 0 && (
        <table>
          <thead><tr><th>Run</th><th>Workflow</th><th>Work</th><th>Status</th><th>Stage</th><th>Progress</th><th>Needs</th><th>Created</th></tr></thead>
          <tbody>
            {data.map((run) => (
              <tr key={run.id}>
                <td><a className="mono" href={`#/runs/${run.id}`}>{run.id.slice(0, 8)}</a></td>
                <td>{run.template_id}</td>
                <td><a className="mono" href={`#/works/${encodeURIComponent(run.work_id)}`}>{run.work_id}</a></td>
                <td><Status value={run.status} />{run.worker.paused && <span className="tag">paused</span>}</td>
                <td>{run.stage}{run.chapter_id ? ` · ${run.chapter_id === "_whole" ? "whole-book review" : run.chapter_id}` : ""}</td>
                <td>{run.progress ? `${run.progress.completed}/${run.progress.total}` : ""}</td>
                <td>{run.status === "WAITING_FOR_HUMAN" && run.gate_chapter_id && run.gate_kind && run.engine_current
                  ? <a href={workflowUI(run.workflow).gateLink(run)}>{run.gate_kind === "chapter_sanity" ? "Approve" : run.gate_review ? `Review ${reviewName(run.gate_kind)} on`
                    : `Decide (${run.gate_kind.replaceAll("_", " ")})`} {run.gate_chapter_id === "_whole" ? "whole book" : run.gate_chapter_id}</a>
                  : <>{run.engine_current ? (PENDING[run.status] ?? "") : (run.status === "COMPLETED" || run.status === "CANCELLED" ? "" : "Restart (engine updated)")}
                  {run.gate_kind ? ` (${run.gate_kind.replaceAll("_", " ")})` : ""}</>}</td>
                <td>{when(run.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function NewRun({ initialWork }: { initialWork?: string }) {
  const templates = useLoad(api.templates, []);
  const works = useLoad(api.works, []);
  const execution = useLoad(api.execution, []);
  const [templateId, setTemplateId] = useState("literary-translation-v1");
  const [modelKey, setModelKey] = useState("");
  const [workId, setWorkId] = useState(initialWork ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const template = templates.data?.find((t) => t.id === templateId);
  const configured = !!execution.data?.models.length;
  const models = execution.data?.models.filter((m) =>
    !m.workflows.length || (template && m.workflows.includes(template.workflow))) ?? [];
  const model = modelKey || models.find((m) => m.model_key === execution.data?.default_model)?.model_key || "";

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const run = await api.create({ template_id: templateId, work_id: workId, ...(model ? { model } : {}) });
      window.location.hash = workflowUI(run.workflow).landingPage(run.id);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={(e) => void submit(e)}>
      <h2>Start a workflow</h2>
      <div className="row">
        <label>Workflow{" "}
          <select value={templateId} onChange={(e) => { setTemplateId(e.target.value); setModelKey(""); }}>
            {templates.data?.filter((t) => !t.consumes).map((t) => <option key={t.id} value={t.id}>{t.title} ({t.id})</option>)}
          </select>
        </label>
        {configured && <label>Model{" "}
          <select value={model} onChange={(e) => setModelKey(e.target.value)}>
            <option value="">Select a compatible model…</option>
            {models.map((m) => <option key={m.model_key} value={m.model_key}>
              {m.model} · {m.endpoint ?? m.harness}
            </option>)}
          </select>
        </label>}
        <label>Work{" "}
          <select value={workId} onChange={(e) => setWorkId(e.target.value)}>
            <option value="">Select a work…</option>
            {works.data?.map((w) => (
              <option key={w.id} value={w.id} disabled={!!w.unfinished_run}>
                {w.title} ({w.id}, {w.manuscript_language}){w.unfinished_run ? " — run in progress" : ""}
              </option>
            ))}
          </select>
        </label>
      </div>
      {configured && <p className="muted">Execution profile: {execution.data?.name} ({execution.data?.harness}).
        {execution.data?.harness === "pi" && " Pi POC runs trusted local tools without an OS sandbox."}</p>}
      {template && <p className="muted">{workflowUI(template.workflow).stageSummary(template)}</p>}
      <ErrorBox error={error ?? templates.error ?? execution.error} />
      <button type="submit" disabled={busy || !workId || !execution.data || (configured && !model)}>
        {busy ? "Starting…" : "Create and start"}</button>
      <p className="muted">Add new manuscripts on the <a href="#/works">Works</a> page. Preparation is the workflow's first
        stage; the agent then runs automatically until it needs you.</p>
    </form>
  );
}
