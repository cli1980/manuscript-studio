import { useEffect, useState } from "react";
import { api, type Gate, type GateOption, type RunDetail } from "../api";
import { Documents, documentTitle, TextBlock } from "./common";
import { Markdown } from "./Markdown";
import { workflowUI } from "../workflows";
import { clearComments, CommentSummary, composeComments, loadComments, type InlineComment } from "./CommentableText";
import { MetadataTable } from "./Metadata";
import { AgentFeedback } from "./AgentFeedback";
import { SamplePoll } from "./SamplePoll";

type Perform = (op: () => Promise<RunDetail>) => void;
// Sends an exact reply; `sent` runs only after the server accepted it (e.g. to clear drafted comments).
type Reply = (text: string, sent?: () => void) => void;

// The decision panel for every workflow: one frame (heading and explanation from the run's WorkflowUI), with a
// body by the decision's shape. Bodies only compose the exact reply; the server validates it.
export function GatePanel({ run, perform, inViewer = false, comments, commentLabel, onSent }: {
  run: RunDetail;
  perform: Perform;
  inViewer?: boolean;
  // Inline comments drafted on the text under review (a commentable pane), sent as feedback with this decision.
  comments?: InlineComment[];
  commentLabel?: string;
  onSent?: (gate: Gate, text: string) => void;
}) {
  const ui = workflowUI(run.workflow);
  // The workflow decides where its decisions are made; elsewhere the panel only links there.
  const page = inViewer ? null : ui.decisionPage(run);
  if (page) {
    return (
      <div className="panel gate">
        <h2>{run.status === "WAITING_FOR_ACCEPTANCE" ? "Ready to finalize" : run.gate ? ui.decisionCopy(run.gate).heading : ""}</h2>
        <p>Decisions happen in the review viewer, beside the text.</p>
        <a className="button" href={page}>Open the review viewer</a>
      </div>
    );
  }
  if (run.status === "WAITING_FOR_ACCEPTANCE" && run.acceptance) return <Acceptance run={run} perform={perform} />;
  if (run.status !== "WAITING_FOR_HUMAN" || !run.gate) return null;
  const gate = run.gate;
  const copy = ui.decisionCopy(gate);
  const reply: Reply = (text, sent) => perform(async () => {
    const next = await api.reply(run.id, gate.id, text);
    sent?.();
    onSent?.(gate, text);
    return next;
  });
  return (
    <div className="panel gate">
      <h2>{copy.heading}</h2>
      {copy.intro && <p className="muted">{copy.intro}</p>}
      {gate.kind === "metadata_review" && run.metadata
        ? <MetadataGate run={run} gate={gate} perform={perform} />
        : gate.options?.length
        ? <ChoiceDecision gate={gate} options={gate.options} reply={reply} />
        : gate.documents?.length > 0 ? <DocumentReview gate={gate} agent={ui.agentName} reply={reply} />
        : gate.sheet && gate.kind === "brief_samples"
        ? <SamplePoll key={gate.id} sheet={gate.sheet} onSubmit={reply} />
        // Every other exchange with the agent, in any workflow, uses the same feedback widget.
        : <AgentFeedback gate={gate} agent={ui.agentName} onReply={reply} commandLabels={copy.commandLabels}
            comments={comments} commentLabel={commentLabel} />}
    </div>
  );
}

// A review of presented documents (e.g. the translation brief): the agent's summary, the documents as tabs,
// then approve or request changes. Changes are feedback for the agent, which presents a revised version.
function DocumentReview({ gate, agent, reply }: { gate: Gate; agent: string; reply: Reply }) {
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
    reply(message, () => gate.documents.forEach((d) => clearComments(`${commentKey}:${d.path}`)));
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
        {approve && <button className="primary" onClick={() => reply(approve)}>
          {approve.charAt(0).toUpperCase() + approve.slice(1)}</button>}
        <CommentSummary comments={all} general={text} onGeneral={setText} onSend={send} sendLabel="Request changes"
          hint="Select text in a document to comment on it." />
      </div>
      <p className="muted">Select text in a document to comment on it; the {agent} revises the documents and presents them again.</p>
    </div>
  );
}

// An engine-owned choice, such as accepting an editing pass or choosing the next one. Stages to choose from are
// a drop-down list showing the picked stage's description; other options (accept, finish) are buttons.
function ChoiceDecision({ gate, options, reply: send }: { gate: Gate; options: GateOption[]; reply: Reply }) {
  const [picked, setPicked] = useState("");
  useEffect(() => setPicked(""), [gate.id]);
  const stages = options.filter((o) => o.stage);
  const choice = stages.find((o) => o.command === picked);
  return (
    <>
      <Markdown text={gate.message} />
      {stages.length > 0 && (
        <div className="choice-pick">
          <div className="row">
            <select aria-label="Next pass" value={picked} onChange={(e) => setPicked(e.target.value)}>
              <option value="">Choose a pass…</option>
              {stages.map((o) => <option key={o.command} value={o.command}>{o.title}</option>)}
            </select>
            <button className="primary" disabled={!choice} onClick={() => choice && send(choice.command)}>Start pass</button>
          </div>
          {choice?.description && <p className="muted">{choice.description}</p>}
        </div>
      )}
      <div className="choices">
        {options.filter((o) => !o.stage).map((o) => (
          <button key={o.command} className={o.finish ? "" : "primary"} onClick={() => send(o.command)}>{o.title}</button>
        ))}
      </div>
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
