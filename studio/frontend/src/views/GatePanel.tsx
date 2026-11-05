import { useEffect, useState } from "react";
import { api, type Gate, type RunDetail, type Sheet } from "../api";
import { Documents, documentTitle, reviewName, TextBlock } from "./common";
import { Markdown } from "./Markdown";
import { workflowUI } from "../workflows";
import { clearComments, CommentSummary, composeComments, loadComments, type InlineComment } from "./CommentableText";
import { MetadataTable } from "./Metadata";
import { SheetReview } from "./SheetReview";
import { SamplePoll } from "./SamplePoll";

// Gate kinds reviewed with the item-by-item SheetReview; add editorial gates here when editing adopts it.
const REVIEW_GATES = new Set(["translation_issue"]);

type Perform = (op: () => Promise<RunDetail>) => void;

// Native forms for each human gate. They only compose the exact reply; the server validates it.
export function GatePanel({ run, perform, inViewer = false }: { run: RunDetail; perform: Perform; inViewer?: boolean }) {
  // The workflow decides where its decisions are made; elsewhere the panel only links there.
  const page = inViewer ? null : workflowUI(run.workflow).decisionPage(run);
  if (page) {
    return (
      <div className="panel gate">
        <h2>{run.status === "WAITING_FOR_ACCEPTANCE" ? "Ready to finalize" : `Your review: ${reviewName(run.gate?.kind ?? "")}`}</h2>
        <p>Decisions happen in the review viewer, beside the text.</p>
        <a className="button" href={page}>Open the review viewer</a>
      </div>
    );
  }
  if (run.status === "WAITING_FOR_ACCEPTANCE" && run.acceptance) return <Acceptance run={run} perform={perform} />;
  if (run.status !== "WAITING_FOR_HUMAN" || !run.gate) return null;
  const gate = run.gate;
  return (
    <div className="panel gate">
      <h2>Your review: {reviewName(gate.kind)}{gate.chapter_id ? ` · ${gate.chapter_id}` : ""}</h2>
      {gate.kind === "metadata_review" && run.metadata
        ? <MetadataGate run={run} gate={gate} perform={perform} />
        : <>
            {/* Approval sheets carry everything the reviewer needs; the agent's raw message and bound
                checkpoint stay internal. Questions without a sheet still show the agent's message. */}
            {gate.documents?.length > 0 ? <DocumentReview run={run} gate={gate} perform={perform} />
              : !gate.sheet && <Markdown text={gate.message} />}
            {gate.documents?.length > 0 ? null : gate.sheet && gate.kind === "brief_samples"
              ? <SamplePoll key={gate.id} sheet={gate.sheet} onSubmit={(text) => perform(() => api.reply(run.id, gate.id, text))} />
              : gate.sheet && REVIEW_GATES.has(gate.kind)
              ? <SheetReview key={`${gate.id}`} sheet={gate.sheet} onSubmit={(text) => perform(() => api.reply(run.id, gate.id, text))} />
              : gate.sheet ? <SheetForm run={run} gate={gate} sheet={gate.sheet} perform={perform} />
              : <FreeReply run={run} gate={gate} perform={perform} />}
          </>}
    </div>
  );
}

function SheetForm({ run, gate, sheet, perform }: { run: RunDetail; gate: Gate; sheet: Sheet; perform: Perform }) {
  const [choices, setChoices] = useState<Record<string, { decision: string; note: string }>>({});
  useEffect(() => setChoices({}), [gate.id]);
  const decisions = Object.fromEntries(sheet.decisions.map((d) => [d.id, d]));
  const open = sheet.items.filter((item) => item.status !== "resolved");
  const closure = open.length === 0 && sheet.gate.closure_required && sheet.gate.final_closure === "pending";
  const lines = open.flatMap((item) => {
    const choice = choices[item.id];
    if (!choice?.decision) return [];
    const command = decisions[choice.decision].command;
    return [choice.note.trim() ? `${item.id} ${command}: ${choice.note.trim()}` : `${item.id} ${command}`];
  });
  const missingNote = open.some((item) => {
    const choice = choices[item.id];
    return choice?.decision && decisions[choice.decision].requires_note && !choice.note.trim();
  });
  return (
    <>
      <p className="muted">{sheet.submission.instruction}</p>
      {sheet.items.map((item) => (
        <div key={item.id} className={`item ${item.status}`}>
          <h3>{item.id} <span className="muted">[{item.status_label ?? item.status}]</span> {item.summary}</h3>
          {item.details.map((row, index) => (
            <div key={index}><div className="label">{row.label}</div><TextBlock text={row.value} /></div>
          ))}
          {item.status !== "resolved" && (
            <div className="row">
              {item.allowed_decisions.map((id) => (
                <label key={id}>
                  <input type="radio" name={`${gate.id}-${item.id}`} checked={choices[item.id]?.decision === id}
                    onChange={() => setChoices({ ...choices, [item.id]: { decision: id, note: choices[item.id]?.note ?? "" } })} />
                  {" "}{decisions[id].label}{decisions[id].requires_note ? " (note required)" : ""}
                </label>
              ))}
              <input placeholder="Note" value={choices[item.id]?.note ?? ""}
                onChange={(e) => setChoices({ ...choices, [item.id]: { decision: choices[item.id]?.decision ?? "", note: e.target.value } })} />
            </div>
          )}
        </div>
      ))}
      {closure ? (
        <p>All items are resolved. Final closure is a separate decision:{" "}
          <button onClick={() => perform(() => api.reply(run.id, gate.id, sheet.submission.closure_command))}>
            {sheet.submission.closure_label || sheet.submission.closure_command}
          </button></p>
      ) : (
        <>
          <button disabled={!lines.length || missingNote} onClick={() => perform(() => api.reply(run.id, gate.id, lines.join("\n")))}>
            Submit {lines.length} decision{lines.length === 1 ? "" : "s"}
          </button>
          <span className="muted"> Undecided items stay pending.</span>
        </>
      )}
    </>
  );
}

// A review of presented documents (e.g. the translation brief): the agent's summary, the documents as tabs,
// then approve or request changes. Changes are feedback for the agent, which presents a revised version.
function DocumentReview({ run, gate, perform }: { run: RunDetail; gate: Gate; perform: Perform }) {
  const [text, setText] = useState("");
  const commentKey = `comments:${gate.id}`;
  const load = () => Object.fromEntries(gate.documents.map((d) => [d.path, loadComments(`${commentKey}:${d.path}`)]));
  const [comments, setComments] = useState<Record<string, InlineComment[]>>(load);
  useEffect(() => { setText(""); setComments(load()); }, [gate.id]);  // eslint-disable-line react-hooks/exhaustive-deps
  const approve = gate.commands[0];
  const all = Object.values(comments).flat();
  function send() {
    const message = [...gate.documents.map((d) => composeComments(comments[d.path] ?? [], "", documentTitle(d.path)))
      .filter(Boolean), text.trim() ? `General: ${text.trim()}` : ""].filter(Boolean).join("\n\n");
    perform(async () => {
      const next = await api.reply(run.id, gate.id, message);
      gate.documents.forEach((d) => clearComments(`${commentKey}:${d.path}`));
      return next;
    });
  }
  return (
    <div className="document-review">
      {gate.answer_to && (
        <div className="conversation"><div className="label">Your request</div><TextBlock text={gate.answer_to.text} /></div>
      )}
      <div className="summary-card">
        <div className="label">{gate.answer_to ? "Revised" : "Summary"}</div>
        <Markdown text={gate.message} />
        <p className="muted">Please review: {gate.documents.map((d) => documentTitle(d.path)).join(", ")}.</p>
      </div>
      <Documents documents={gate.documents} commentKey={commentKey}
        onComments={(path, list) => setComments((old) => ({ ...old, [path]: list }))} />
      <div className="decision-bar">
        {approve && <button className="primary" onClick={() => perform(() => api.reply(run.id, gate.id, approve))}>
          {approve.charAt(0).toUpperCase() + approve.slice(1)}</button>}
        <CommentSummary comments={all} general={text} onGeneral={setText} onSend={send} sendLabel="Request changes" />
      </div>
      <p className="muted">Select text in a document to comment on it; the translator revises and presents the brief again.</p>
    </div>
  );
}

function FreeReply({ run, gate, perform }: { run: RunDetail; gate: Gate; perform: Perform }) {
  const [text, setText] = useState("");
  useEffect(() => setText(""), [gate.id]);
  return (
    <>
      {gate.commands.length > 0 && (
        <p>{gate.commands.map((command) => (
          <button key={command} onClick={() => perform(() => api.reply(run.id, gate.id, command))}>{command}</button>
        ))}<span className="muted"> or reply with feedback below.</span></p>
      )}
      <textarea rows={5} value={text} onChange={(e) => setText(e.target.value)} placeholder="Your response" />
      <button disabled={!text.trim()} onClick={() => perform(() => api.reply(run.id, gate.id, text))}>Send response</button>
    </>
  );
}

function MetadataGate({ run, gate, perform }: { run: RunDetail; gate: Gate; perform: Perform }) {
  const view = run.metadata!;
  return (
    <>
      <p>Inspect the shared metadata (record revision {view.record_revision}). Unknown: {view.unknown.join(", ") || "none"}.
        Stale: {view.stale.join(", ") || "none"}. Each edit creates a new revision and a new gate.</p>
      <MetadataTable metadata={view.metadata} provenance={view.provenance} locked={view.locked} fields={run.metadata_fields ?? []}
        onSave={async (field, value, rationale) => {
          await api.editMetadata(run.id, { field, value, rationale, gate_id: gate.id });
          perform(() => api.run(run.id));
        }} />
      <p><button onClick={() => perform(() => api.confirmMetadata(run.id, gate.id, view.record_revision))}>
        Confirm metadata (revision {view.record_revision})
      </button></p>
    </>
  );
}

function Acceptance({ run, perform }: { run: RunDetail; perform: Perform }) {
  const acceptance = run.acceptance!;
  const [understood, setUnderstood] = useState(false);
  return (
    <div className="panel gate">
      <h2>Final acceptance</h2>
      <p>Read every chapter before accepting:</p>
      <ul>{acceptance.outputs.map((o) => <li key={o.chapter_id}>{workflowUI(run.workflow).hasChapterViewer
        ? <a href={`#/runs/${run.id}/chapters/${encodeURIComponent(o.chapter_id)}`}>{o.chapter_id}</a> : o.chapter_id}{" "}
        <span className="mono muted">{o.sha256.slice(0, 12)}</span></li>)}</ul>
      <div className="banner warn"><strong>This is irreversible.</strong> {acceptance.notice}</div>
      <label><input type="checkbox" checked={understood} onChange={(e) => setUnderstood(e.target.checked)} /> I understand that accepting finalizes this run.</label>
      <p><button className="danger" disabled={!understood}
        onClick={() => perform(() => api.accept(run.id, acceptance.acceptance_id, true))}>Accept and finalize</button></p>
    </div>
  );
}
