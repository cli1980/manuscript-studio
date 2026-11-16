import { useState } from "react";
import { api, readBase64 } from "../api";
import { ErrorBox, Status, TextBlock, useLoad, when } from "./common";
import { Markdown } from "./Markdown";
import { workflowUI } from "../workflows";
import { AuthorForm, MetadataTable } from "./Metadata";
import { allRuns, allWorks, useLive } from "../live";
import { ExecutionProfileNotice, ModelPicker, useModelSelection } from "./ModelSelection";

// Works: manuscript intake and workflow outcomes. Every work and its library is viewable without a run.
export function Works() {
  const { data, error } = useLoad(api.works, [], useLive(allWorks));
  return (
    <section>
      <h1>Works</h1>
      <AddManuscript onAdded={(id) => { window.location.hash = `#/works/${encodeURIComponent(id)}`; }} />
      <h2>All works</h2>
      <ErrorBox error={error} />
      {data && data.length === 0 && <p className="muted">No works yet. Add a manuscript above.</p>}
      {data && data.length > 0 && (
        <table>
          <thead><tr><th>Title</th><th>Work ID</th><th>Language</th><th>Workflows</th><th>Runs</th><th>Created</th></tr></thead>
          <tbody>
            {data.map((work) => (
              <tr key={work.id}>
                <td><a href={`#/works/${encodeURIComponent(work.id)}`}>{work.title}</a></td>
                <td className="mono">{work.id}</td>
                <td>{work.manuscript_language ?? "Awaiting preparation"}</td>
                <td>
                  {Object.entries(work.workflows).map(([name, flow]) => (
                    <span key={name} className="tag">{name}: {flow.status === "read_only" ? "final" : flow.status}</span>
                  ))}
                  {work.unfinished_run && <a className="tag busy" href={`#/runs/${work.unfinished_run}`}>run in progress</a>}
                </td>
                <td>{work.runs}</td>
                <td>{when(work.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function AddManuscript({ onAdded }: { onAdded: (workId: string) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const work = await api.createWork({ upload: { name: file!.name, data: await readBase64(file!) }, manuscript_language: language });
      setFile(null);
      (event.target as HTMLFormElement).reset();
      onAdded(work.id);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={(e) => void submit(e)}>
      <h2>Add a manuscript</h2>
      <div className="row">
        <input type="file" accept=".md,.txt,.docx" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <label>Language hint (optional) <input value={language} placeholder="Auto-detect" onChange={(e) => setLanguage(e.target.value)} size={12} /></label>
        <button type="submit" disabled={busy || !file}>{busy ? "Adding…" : "Add as a new work"}</button>
      </div>
      <ErrorBox error={error} />
      <p className="muted">Each upload creates a new work, even for an identical file. Language can remain blank:
        preparation detects it from the manuscript before downstream work starts.</p>
    </form>
  );
}

export function WorkView({ workId }: { workId: string }) {
  // The work's library and log, and the state of runs (the page lists this work's runs).
  const { data, error, reload } = useLoad(() => api.work(workId), [workId],
    useLive((live) => `${live.works[workId] ?? ""}|${allRuns(live)}`));
  const [viewing, setViewing] = useState<{ path: string; text: string } | null>(null);
  const [viewError, setViewError] = useState<string | null>(null);

  async function open(path: string) {
    try {
      setViewing({ path, text: await api.artifact(workId, path) });
      setViewError(null);
    } catch (exc) {
      setViewError(exc instanceof Error ? exc.message : String(exc));
    }
  }

  if (!data) return <ErrorBox error={error ?? null} />;
  return (
    <section>
      <p><a href="#/works">← Works</a></p>
      <h1>{data.title}</h1>
      <p className="muted mono">{data.id} · {data.manuscript_language ?? "language pending preparation"} · source <a href={api.sourceUrl(data.id)} download
        title="Download the original upload">{data.source_name}</a> · owner {data.owner}</p>
      {data.origin && (
        <p>Created from the formatted <a href={`#/runs/${data.origin.run_id}`}>{data.origin.source_version}</a> output of work{" "}
          <a href={`#/works/${encodeURIComponent(data.origin.work_id)}`}>{data.origin.work_id}</a>.</p>
      )}
      {data.handed_off?.length > 0 && (
        <p>Formatted editions continued as works:{" "}
          {data.handed_off.map((w, i) => (
            <span key={w.work_id}>{i ? ", " : ""}<a href={`#/works/${encodeURIComponent(w.work_id)}`}>{w.title}</a> ({w.source_version})</span>
          ))}</p>
      )}
      <ErrorBox error={error} />
      {data.metadata && data.runs.length === 0 && !data.unfinished_run && (
        <AuthorForm metadata={data.metadata.metadata} fields={data.metadata_fields}
          onSave={async (field, value, rationale) => { await api.editWorkMetadata(workId, { field, value, rationale }); }}
          onDone={() => void reload()} />
      )}
      <StartWorkflow workId={workId} language={data.manuscript_language} unfinishedRun={data.unfinished_run} workflows={data.workflows} onStarted={() => void reload()} />
      <h2>Workflows</h2>
      {Object.keys(data.workflows).length === 0 && <p className="muted">No workflow has been finalized on this work.</p>}
      {Object.entries(data.workflows).map(([name, flow]) => (
        <div key={name} className="banner">
          <strong>{name}</strong>: {flow.status === "completed"
            ? <>latest accepted version {flow.version ?? ""} (run <a href={`#/runs/${flow.finalized_run_id}`}>{flow.finalized_run_id?.slice(0, 8)}</a>). A new run publishes the next version.</>
            : flow.status}
        </div>
      ))}
      <h2>Runs</h2>
      <table>
        <thead><tr><th>Run</th><th>Template</th><th>Status</th><th>Stage</th><th>Created</th></tr></thead>
        <tbody>
          {data.runs.map((run) => (
            <tr key={run.id}>
              <td><a className="mono" href={`#/runs/${run.id}`}>{run.id.slice(0, 8)}</a></td>
              <td>{run.template_id}</td>
              <td><Status value={run.status} /></td>
              <td>{run.stage}</td>
              <td>{when(run.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h2>Metadata</h2>
      {data.metadata ? (
        <>
          <p className="muted">Record revision {data.metadata.record_revision}; {data.metadata_history.length} published versions.
            {data.unfinished_run ? " Edit through the run in progress while it is unfinished." : " Edits are versioned and published to this work."}</p>
          <MetadataTable metadata={data.metadata.metadata} provenance={data.metadata.provenance} fields={data.metadata_fields}
            onSave={data.unfinished_run ? undefined : async (field, value, rationale) => {
              await api.editWorkMetadata(workId, { field, value, rationale });
              await reload();
            }} />
        </>
      ) : <p className="muted">No metadata record (imported before metadata existed).</p>}
      <h2>Library</h2>
      <div className="split">
        <ul className="list">
          {Object.entries(data.heads).sort(([a], [b]) => a.localeCompare(b)).map(([path, head]) => (
            <li key={path}>
              {/* The original upload is downloaded, not viewed; its verified text is in each run's chapter viewer. */}
              {path.startsWith("sources/")
                ? <a href={api.sourceUrl(workId)} download>{path}</a>
                : path.endsWith("/document.docx") ? <a href={api.publishedDocxUrl(workId, head.id)} download>{path}</a>
                : <button className="link" onClick={() => void open(path)}>{path}</button>}
              <span className="muted"> v{head.version} · {head.status}{head.review_status === "unreviewed" ? " (unreviewed)" : ""}</span>
            </li>
          ))}
        </ul>
        <div>
          <ErrorBox error={viewError} />
          {viewing && <><h3 className="mono">{viewing.path}</h3>
            {viewing.path.endsWith(".md") ? <Markdown text={viewing.text} /> : <TextBlock text={viewing.text} />}</>}
        </div>
      </div>
      <h2>Publication log</h2>
      <table>
        <thead><tr><th>When</th><th>Artifact</th><th>Version</th><th>Stage</th><th>Status</th></tr></thead>
        <tbody>
          {data.publications.slice().reverse().map((p) => (
            <tr key={p.id}><td>{when(p.created_at)}</td><td className="mono">{p.artifact}</td><td>{p.version ?? ""}</td><td>{p.stage}</td><td>{p.status}</td></tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

// Start a workflow on this work without leaving the page; the new run appears in the Runs table below.
function StartWorkflow({ workId, language, unfinishedRun, workflows, onStarted }: {
  workId: string;
  language: string | null;
  unfinishedRun: string | null;
  workflows: Record<string, { status: string }>;
  onStarted: () => void;
}) {
  const templates = useLoad(api.templates, []);
  const [templateId, setTemplateId] = useState("");
  const [passageSize, setPassageSize] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const available = (templates.data ?? []).filter((t) => !t.consumes);
  const template = available.find((t) => t.id === templateId);
  const selection = useModelSelection(template?.workflow);
  // Passage size is counted in characters for Chinese, Japanese, and Korean, otherwise in words.
  const unit = language ? (["zh", "ja", "ko"].includes(language.split("-")[0].toLowerCase()) ? "cjk_chars" : "words") : null;
  const defaultSize = unit ? template?.passage_size?.[unit] : undefined;

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const settings = template?.passage_size && passageSize.trim() ? { passage_size: Number(passageSize) } : undefined;
      const run = await api.create({ template_id: templateId, work_id: workId, settings,
        ...(selection.model ? { model: selection.model } : {}) });
      setTemplateId("");
      setPassageSize("");
      onStarted();
      window.location.hash = workflowUI(run.workflow).landingPage(run.id);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  }

  if (unfinishedRun) return <div className="banner warn">
    A workflow is still unfinished on this work. <a href={`#/runs/${unfinishedRun}`}>Open the unfinished workflow</a>
    {" "}and finish or stop it before starting another.
  </div>;
  return (
    <div className="panel">
      <h2>Start a workflow</h2>
      <div className="row">
        <select value={templateId} onChange={(e) => { setTemplateId(e.target.value); setPassageSize(""); }}>
          <option value="">Choose a workflow…</option>
          {available.map((t) => (
            <option key={t.id} value={t.id}>
              {t.title}{workflows[t.workflow]?.status === "completed" ? " (next version)" : ""}
            </option>
          ))}
        </select>
        <ModelPicker selection={selection} />
        <button className="primary" disabled={!templateId || busy || !selection.ready} onClick={() => void start()}>{busy ? "Starting…" : "Start"}</button>
      </div>
      <ExecutionProfileNotice selection={selection} />
      {template?.passage_size && (
        <details>
          <summary>Advanced</summary>
          <label>Maximum passage size{" "}
            <input type="number" min={100} step={100} value={passageSize} placeholder={defaultSize ? String(defaultSize) : "Automatic"}
              onChange={(e) => setPassageSize(e.target.value)} />{" "}{!unit ? "units determined during preparation"
                : unit === "cjk_chars" ? "characters" : "words"}</label>
          <p className="muted">The agent translates and reviews each chapter passage by passage. Smaller passages get closer
            review; a longer passage needs your approval as an exception. Fixed for the run.</p>
        </details>
      )}
      {template && <p className="muted">{workflowUI(template.workflow).stageSummary(template)}</p>}
      <ErrorBox error={error ?? templates.error ?? selection.error} />
    </div>
  );
}
