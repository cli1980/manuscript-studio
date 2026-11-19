import { useState } from "react";
import { api, readBase64, type WorkDetail, type WorkVersion } from "../api";
import { ErrorBox, Status, TextBlock, useLoad, when } from "./common";
import { Markdown } from "./Markdown";
import { workflowUI } from "../workflows";
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
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const work = await api.createWork({ upload: { name: file!.name, data: await readBase64(file!) } });
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
        <button type="submit" disabled={busy || !file}>{busy ? "Adding…" : "Add as a new work"}</button>
      </div>
      <ErrorBox error={error} />
      <p className="muted">Each upload creates a new work. Then prepare it on the Work page: review metadata,
        run manuscript analysis once, and reuse that ready version in future workflows.</p>
    </form>
  );
}

export function WorkView({ workId }: { workId: string }) {
  // The work's library and log, and the state of runs (the page lists this work's runs).
  const { data, error, reload } = useLoad(() => api.work(workId), [workId],
    useLive((live) => `${live.works[workId] ?? ""}|${allRuns(live)}`));
  const [viewing, setViewing] = useState<{ path: string; text: string } | null>(null);
  const [viewError, setViewError] = useState<string | null>(null);

  async function open(path: string, version?: string) {
    try {
      setViewing({ path, text: version ? await api.versionArtifact(workId, version, path) : await api.artifact(workId, path) });
      setViewError(null);
    } catch (exc) {
      setViewError(exc instanceof Error ? exc.message : String(exc));
    }
  }

  if (!data) return <ErrorBox error={error ?? null} />;
  return (
    <section className="work-detail">
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
      <WorkPreparation work={data} onOpen={(path, version) => void open(path, version)} />
      <StartWorkflow workId={workId} versions={data.versions ?? []} unfinishedRun={data.unfinished_run}
        preparing={(data.preparation_jobs ?? []).some((job) => job.id === data.unfinished_run)}
        workflows={data.workflows} onStarted={() => void reload()} />
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
      <div className="table-scroll" role="region" aria-label="Work runs" tabIndex={0}><table>
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
      </table></div>
      <h2>Metadata</h2>
      {data.metadata ? (
        <>
          <p className="muted">Record revision {data.metadata.record_revision}; {data.metadata_history.length} published versions.
            {" "}Work preparation reviews metadata before freezing each prepared version.</p>
          {data.metadata_editor_run
            ? <a href={(data.preparation_jobs ?? []).some((job) => job.id === data.metadata_editor_run)
              ? `#/works/${encodeURIComponent(workId)}/preparations/${data.metadata_editor_run}`
              : `#/runs/${data.metadata_editor_run}/overview`}>Review metadata</a>
            : <p className="muted">Prepare this Work to review its metadata.</p>}
        </>
      ) : <p className="muted">No metadata record (imported before metadata existed).</p>}
      <h2>Library</h2>
      <div className="split">
        <ul className="list">
          {Object.entries(data.heads).filter(([path]) => !/^work-versions\/[^/]+\/objects\//.test(path))
            .sort(([a], [b]) => a.localeCompare(b)).map(([path, head]) => (
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
      <div className="table-scroll" role="region" aria-label="Work publication history" tabIndex={0}><table>
        <thead><tr><th>When</th><th>Artifact</th><th>Version</th><th>Stage</th><th>Status</th></tr></thead>
        <tbody>
          {data.publications.slice().reverse().map((p) => (
            <tr key={p.id}><td>{when(p.created_at)}</td><td className="mono">{p.artifact}</td><td>{p.version ?? ""}</td><td>{p.stage}</td><td>{p.status}</td></tr>
          ))}
        </tbody>
      </table></div>
    </section>
  );
}

function WorkPreparation({ work, onOpen }: { work: WorkDetail; onOpen: (path: string, version: string) => void }) {
  const selection = useModelSelection("work-preparation");
  const [sourceVersion, setSourceVersion] = useState("");
  const [refreshAnalysis, setRefreshAnalysis] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const versions = work.versions ?? [];
  const sourceReady = versions.some((version) => version.version_id === sourceVersion && version.status === "ready");

  async function prepare() {
    setBusy(true);
    setError(null);
    try {
      const job = await api.prepareWork(work.id, {
        ...(sourceVersion ? { source_version_id: sourceVersion } : {}),
        ...(sourceReady && refreshAnalysis ? { refresh_analysis: true } : {}),
        ...(selection.model ? { model: selection.model } : {}),
      });
      window.location.hash = `#/works/${encodeURIComponent(work.id)}/preparations/${job.id}`;
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  }

  return <section className="panel">
    <h2>Work preparation</h2>
    <p>Prepare the source, review metadata, and analyze the complete manuscript once. Future workflows select
      the ready version without repeating extraction or analysis.</p>
    <div className="row">
      <label>Preparation source{" "}
        <select value={sourceVersion} onChange={(e) => { setSourceVersion(e.target.value); setRefreshAnalysis(false); }}>
          <option value="">Original upload</option>
          {versions.map((version) => <option key={version.version_id} value={version.version_id}>
            {version.version_id} · {version.kind} · {version.language ?? "detect language"}
          </option>)}
        </select>
      </label>
      <ModelPicker selection={selection} />
      {sourceReady && <label><input type="checkbox" checked={refreshAnalysis}
        onChange={(e) => setRefreshAnalysis(e.target.checked)} /> Re-run analysis after metadata review</label>}
      <button disabled={busy || !!work.unfinished_run || !selection.ready} onClick={() => void prepare()}>
        {busy ? "Starting preparation..." : sourceReady && !refreshAnalysis ? "Review metadata (reuse analysis)" : "Prepare and analyze"}
      </button>
    </div>
    <p className="muted">{sourceReady && !refreshAnalysis
      ? "Metadata-only revisions reuse the exact prepared text and original reading without a model call."
      : "This starts agent work and uses time and tokens. Reuse a ready version below instead unless you intend to create a fresh preparation/analysis revision."}</p>
    <ExecutionProfileNotice selection={selection} />
    <ErrorBox error={error ?? selection.error} />
    {(work.preparation_jobs ?? []).map((job) => <p key={job.id}>
      <a href={`#/works/${encodeURIComponent(work.id)}/preparations/${job.id}`}>Preparation {job.id.slice(0, 8)}</a>
      {" "}· <Status value={job.status} /> · {job.stage}
    </p>)}
    <h3>Manuscript versions</h3>
    {!versions.length && <p className="muted">No prepared versions yet.</p>}
    {versions.map((version) => <details key={version.version_id}>
      <summary>{version.version_id} · {version.kind} · {version.language ?? "language pending"} ·{" "}
        {version.status === "ready" ? `ready (analysis ${version.analysis_status})` : "preparation/analysis pending"}</summary>
      {version.parent_version_id && <p>Derived from {version.parent_version_id}.</p>}
      {version.analysis_id && <p className="mono">Analysis: {version.analysis_id}</p>}
      <p className="muted">Technical readiness is not approval of story claims or catalogue metadata.</p>
      <ul>{version.documents.map((document) => <li key={document.artifact}>
        <button className="link" onClick={() => onOpen(document.path, version.version_id)}>{document.path}</button>
      </li>)}</ul>
    </details>)}
  </section>;
}

// The selected input is immutable; workflow outputs are separate derived versions.
function StartWorkflow({ workId, versions, unfinishedRun, preparing, workflows, onStarted }: {
  workId: string;
  versions: WorkVersion[];
  unfinishedRun: string | null;
  preparing: boolean;
  workflows: Record<string, { status: string }>;
  onStarted: () => void;
}) {
  const templates = useLoad(api.templates, []);
  const [templateId, setTemplateId] = useState("");
  const [versionId, setVersionId] = useState("");
  const [passageSize, setPassageSize] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const available = (templates.data ?? []).filter((t) => !t.consumes);
  const template = available.find((t) => t.id === templateId);
  const selection = useModelSelection(template?.workflow);
  const ready = versions.filter((version) => version.status === "ready");
  const selected = ready.find((version) => version.version_id === versionId);
  const language = selected?.language;
  // Passage size is counted in characters for Chinese, Japanese, and Korean, otherwise in words.
  const unit = language ? (["zh", "ja", "ko"].includes(language.split("-")[0].toLowerCase()) ? "cjk_chars" : "words") : null;
  const defaultSize = unit ? template?.passage_size?.[unit] : undefined;

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const settings = template?.passage_size && passageSize.trim() ? { passage_size: Number(passageSize) } : undefined;
      const run = await api.create({ template_id: templateId, work_id: workId, work_version_id: versionId, settings,
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
    {preparing ? "Preparation" : "A workflow"} is still unfinished on this work. <a href={preparing
      ? `#/works/${encodeURIComponent(workId)}/preparations/${unfinishedRun}` : `#/runs/${unfinishedRun}`}>Open it</a>
    {" "}and finish or stop it before starting another.
  </div>;
  return (
    <div className="panel">
      <h2>Start a workflow</h2>
      {!ready.length && <p className="muted">Prepare a Work version first. Workflows reuse its verified Markdown,
        front matter and analysis without repeating intake.</p>}
      <div className="row">
        <label>Prepared version{" "}
          <select aria-label="Prepared version" value={versionId} onChange={(e) => setVersionId(e.target.value)}>
            <option value="">Choose a ready version...</option>
            {ready.map((version) => <option key={version.version_id} value={version.version_id}>
              {version.version_id} · {version.kind} · {version.language}
            </option>)}
          </select>
        </label>
        <label>Workflow{" "}<select aria-label="Workflow" value={templateId} onChange={(e) => { setTemplateId(e.target.value); setPassageSize(""); }}>
          <option value="">Choose a workflow…</option>
          {available.map((t) => (
            <option key={t.id} value={t.id}>
              {t.title}{workflows[t.workflow]?.status === "completed" ? " (next version)" : ""}
            </option>
          ))}
        </select></label>
        <ModelPicker selection={selection} />
        <button className="primary" disabled={!templateId || !selected || busy || !selection.ready} onClick={() => void start()}>{busy ? "Starting…" : "Start"}</button>
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
