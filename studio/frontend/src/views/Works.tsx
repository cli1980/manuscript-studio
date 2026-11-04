import { useState } from "react";
import { api, readBase64, type Publication } from "../api";
import { ErrorBox, Status, TextBlock, useLoad, when } from "./common";
import { AuthorForm, MetadataTable } from "./Metadata";

// Works: manuscript intake and workflow outcomes. Every work and its library is viewable without a run.
export function Works() {
  const { data, error } = useLoad(api.works, [], 15000);
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
                <td>{work.manuscript_language}</td>
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
  const [language, setLanguage] = useState("zh-CN");
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
        <label>Manuscript language <input value={language} onChange={(e) => setLanguage(e.target.value)} size={8} /></label>
        <button type="submit" disabled={busy || !file || !language}>{busy ? "Adding…" : "Add as a new work"}</button>
      </div>
      <ErrorBox error={error} />
      <p className="muted">Each upload creates a new work, even for an identical file. Preparation runs as the first stage of a workflow.</p>
    </form>
  );
}

export function WorkView({ workId }: { workId: string }) {
  const { data, error, reload } = useLoad(() => api.work(workId), [workId], 15000);
  const [viewing, setViewing] = useState<{ path: string; text: string } | null>(null);
  const [viewError, setViewError] = useState<string | null>(null);
  const [formatError, setFormatError] = useState<string | null>(null);

  async function open(path: string) {
    try {
      setViewing({ path, text: await api.artifact(workId, path) });
      setViewError(null);
    } catch (exc) {
      setViewError(exc instanceof Error ? exc.message : String(exc));
    }
  }

  async function format(renderer: string, publicationId: string) {
    try {
      const run = await api.create({ template_id: "manuscript-formatting-v1", derived: true, work_id: workId,
        publication_id: publicationId, options: { renderer } });
      window.location.hash = `#/runs/${run.id}`;
    } catch (exc) {
      setFormatError(exc instanceof Error ? exc.message : String(exc));
    }
  }

  if (!data) return <ErrorBox error={error ?? null} />;
  // Every finalized run's accepted output can be formatted; newest first.
  const accepted = data.publications.filter((p) => p.contract === "accepted-markdown-chapters/1").reverse();
  return (
    <section>
      <p><a href="#/works">← Works</a></p>
      <h1>{data.title}</h1>
      <p className="muted mono">{data.id} · {data.manuscript_language} · source {data.source_name} · owner {data.owner}</p>
      <ErrorBox error={error} />
      {data.metadata && data.runs.length === 0 && !data.unfinished_run && (
        <AuthorForm metadata={data.metadata.metadata} fields={data.metadata_fields}
          onSave={async (field, value, rationale) => { await api.editWorkMetadata(workId, { field, value, rationale }); }}
          onDone={() => void reload()} />
      )}
      <StartWorkflow workId={workId} unfinishedRun={data.unfinished_run} workflows={data.workflows} onStarted={() => void reload()} />
      <h2>Workflows</h2>
      {Object.keys(data.workflows).length === 0 && <p className="muted">No workflow has been finalized on this work.</p>}
      {Object.entries(data.workflows).map(([name, flow]) => (
        <div key={name} className="banner">
          <strong>{name}</strong>: {flow.status === "completed"
            ? <>latest accepted version {flow.version ?? ""} (run <a href={`#/runs/${flow.finalized_run_id}`}>{flow.finalized_run_id?.slice(0, 8)}</a>). A new run publishes the next version.</>
            : flow.status}
        </div>
      ))}
      {accepted.length > 0 && (
        <FormatPanel workId={workId} accepted={accepted} busy={!!data.unfinished_run} onFormat={(renderer, id) => void format(renderer, id)} />
      )}
      <ErrorBox error={formatError} />
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
              <button className="link" onClick={() => void open(path)}>{path}</button>
              <span className="muted"> v{head.version} · {head.status}{head.review_status === "unreviewed" ? " (unreviewed)" : ""}</span>
            </li>
          ))}
        </ul>
        <div>
          <ErrorBox error={viewError} />
          {viewing && <><h3 className="mono">{viewing.path}</h3><TextBlock text={viewing.text} /></>}
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
function StartWorkflow({ workId, unfinishedRun, workflows, onStarted }: {
  workId: string;
  unfinishedRun: string | null;
  workflows: Record<string, { status: string }>;
  onStarted: () => void;
}) {
  const templates = useLoad(api.templates, []);
  const [templateId, setTemplateId] = useState("");
  const [skip, setSkip] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const available = (templates.data ?? []).filter((t) => !t.consumes);
  const template = available.find((t) => t.id === templateId);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      await api.create({ template_id: templateId, work_id: workId, skip_stages: skip });
      setTemplateId("");
      setSkip([]);
      onStarted();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  }

  // While a run is unfinished the Runs section already shows it; the start panel simply stays hidden.
  if (unfinishedRun) return null;
  return (
    <div className="panel">
      <h2>Start a workflow</h2>
      <div className="row">
        <select value={templateId} onChange={(e) => { setTemplateId(e.target.value); setSkip([]); }}>
          <option value="">Choose a workflow…</option>
          {available.map((t) => (
            <option key={t.id} value={t.id}>
              {t.title}{workflows[t.workflow]?.status === "completed" ? " (next version)" : ""}
            </option>
          ))}
        </select>
        {template?.optional_stages.map((stage) => (
          <label key={stage}>
            <input type="checkbox" checked={skip.includes(stage)}
              onChange={(e) => setSkip(e.target.checked ? [...skip, stage] : skip.filter((s) => s !== stage))} /> skip {stage}
          </label>
        ))}
        <button className="primary" disabled={!templateId || busy} onClick={() => void start()}>{busy ? "Starting…" : "Start"}</button>
      </div>
      {template && <p className="muted">Stages: {template.stages.filter((s) => !skip.includes(s)).join(" → ")}. Preparation runs first;
        the agent then works until it needs you. Open the run below to follow it.</p>}
      <ErrorBox error={error ?? templates.error} />
    </div>
  );
}

// Formatting: choose a version, preview its key data, then format it.
interface RunRecord {
  version: string; workflow: string; template_id: string; run_id: string; accepted_at: string;
  acceptance: { decision_source: string }; manuscript_language: string; output_language: string;
  prepared_revision: string; metadata_confirmed: { record_revision: number } | null; restarts: number;
  chapters: { chapter_id: string; bytes: number; attempts: number | null }[];
  decisions: Record<string, { replies: number; decided_by: Record<string, number> }>;
}

function versionOf(publication: Publication) {
  return publication.artifact.match(/\/(v\d{3,})\//)?.[1] ?? "";
}

function FormatPanel({ workId, accepted, busy, onFormat }: {
  workId: string;
  accepted: Publication[];
  busy: boolean;
  onFormat: (renderer: string, publicationId: string) => void;
}) {
  const [choice, setChoice] = useState("");
  const [renderer, setRenderer] = useState("word");
  const [preview, setPreview] = useState<{ run: RunRecord; titles: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selected = accepted.find((p) => p.id === choice);

  async function choose(id: string) {
    setChoice(id);
    setPreview(null);
    setError(null);
    const publication = accepted.find((p) => p.id === id);
    if (!publication) return;
    try {
      const folder = publication.artifact.replace(/manifest\.json$/, "");
      const [run, manifest] = await Promise.all([
        api.artifact(workId, folder + "run.json"), api.artifact(workId, publication.artifact)]);
      const parse = (value: unknown) => (typeof value === "string" ? JSON.parse(value) : value);
      const chapters = (parse(manifest) as { chapters: { chapter_id: string; title: string | null }[] }).chapters;
      setPreview({ run: parse(run) as RunRecord, titles: chapters.map((c) => c.title ?? c.chapter_id) });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    }
  }

  return (
    <div className="panel">
      <h2>Format as DOCX</h2>
      <div className="row">
        <label>Version{" "}
          <select value={choice} onChange={(e) => void choose(e.target.value)}>
            <option value="">Choose a version…</option>
            {accepted.map((p) => (
              <option key={p.id} value={p.id}>{p.workflow ?? "workflow"} {versionOf(p)} · {when(p.created_at)}</option>
            ))}
          </select>
        </label>
        <label>Renderer{" "}
          <select value={renderer} onChange={(e) => setRenderer(e.target.value)}>
            <option value="word">Microsoft Word</option>
            <option value="libreoffice">LibreOffice</option>
          </select>
        </label>
        <button className="primary" disabled={busy || !selected || !preview} onClick={() => onFormat(renderer, choice)}>Format</button>
      </div>
      <ErrorBox error={error} />
      {preview && selected && (
        <div className="version-preview">
          <dl className="review-details">
            <div><dt>Version</dt><dd>{preview.run.workflow} {preview.run.version} → manuscript-{preview.run.version}.docx</dd></div>
            <div><dt>Run</dt><dd><a href={`#/runs/${preview.run.run_id}`}>{preview.run.run_id.slice(0, 8)}</a> ({preview.run.template_id})</dd></div>
            <div><dt>Accepted</dt><dd>{when(preview.run.accepted_at)} by {preview.run.acceptance.decision_source === "human" ? "you" : preview.run.acceptance.decision_source}</dd></div>
            <div><dt>Languages</dt><dd>{preview.run.manuscript_language} → {preview.run.output_language}</dd></div>
            <div><dt>Chapters</dt><dd>{preview.titles.length}: {preview.titles.join(", ")}</dd></div>
            <div><dt>Size</dt><dd>{preview.run.chapters.reduce((total, c) => total + c.bytes, 0).toLocaleString()} bytes</dd></div>
            <div><dt>Basis</dt><dd>prepared revision {preview.run.prepared_revision}; metadata revision {preview.run.metadata_confirmed?.record_revision ?? "—"}</dd></div>
            <div><dt>Decisions</dt><dd>{Object.entries(preview.run.decisions).map(([gate, d]) => `${gate.replaceAll("_", " ")}: ${d.replies}`).join(" · ") || "none"}
              {preview.run.restarts ? ` · ${preview.run.restarts} restarts` : ""}</dd></div>
          </dl>
        </div>
      )}
      {busy && <p className="muted">A run is unfinished on this work; formatting can start when it finishes.</p>}
    </div>
  );
}
