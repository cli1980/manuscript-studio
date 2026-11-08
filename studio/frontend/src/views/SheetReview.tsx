import { useEffect, useMemo, useState } from "react";
import type { Sheet, SheetItem } from "../api";
import { repeatsReviewedText, type ReviewedText } from "../reviewText";

// Reusable item-by-item review for every approval sheet (used by the shared AgentFeedback widget).
// Decisions stay in the browser (per sheet revision) until one complete submission of every open item.

type Draft = { decision: string; note: string };

export function SheetReview({ sheet, onSubmit, busy = false, runId, reviewedText }: {
  sheet: Sheet;
  onSubmit: (text: string) => void;
  busy?: boolean;
  runId?: string;
  reviewedText?: ReviewedText;
}) {
  const key = `sheet-review:${runId ?? "local"}:${sheet.sheet_id}:${sheet.revision}`;
  const [drafts, setDrafts] = useState<Record<string, Draft>>(() => {
    try { return JSON.parse(localStorage.getItem(key) ?? "{}"); } catch { return {}; }
  });
  const open = useMemo(() => sheet.items.filter((item) => item.status !== "resolved"), [sheet]);
  const [selected, setSelected] = useState<string>(() => (open[0] ?? sheet.items[0])?.id);
  const decisions = useMemo(() => Object.fromEntries(sheet.decisions.map((d) => [d.id, d])), [sheet]);

  useEffect(() => { localStorage.setItem(key, JSON.stringify(drafts)); }, [key, drafts]);

  const problem = (item: SheetItem) => {
    const draft = drafts[item.id];
    if (!draft?.decision) return "undecided";
    return decisions[draft.decision].requires_note && !draft.note.trim() ? "needs note" : null;
  };
  const reviewed = open.filter((item) => !problem(item)).length;
  const closure = open.length === 0 && sheet.gate.closure_required && sheet.gate.final_closure === "pending";
  const index = sheet.items.findIndex((item) => item.id === selected);
  const item = sheet.items[index];

  function update(itemId: string, change: Partial<Draft>) {
    setDrafts((old) => ({ ...old, [itemId]: { ...(old[itemId] ?? { decision: "", note: "" }), ...change } }));
  }

  function submit() {
    const lines = open.map((entry) => {
      const draft = drafts[entry.id];
      const command = decisions[draft.decision].command;
      return draft.note.trim() ? `${entry.id} ${command}: ${draft.note.trim().replace(/\s*\n\s*/g, " ")}` : `${entry.id} ${command}`;
    });
    onSubmit(lines.join("\n"));
    localStorage.removeItem(key);
  }

  if (closure) {
    return (
      <div className="review">
        <p>All {sheet.items.length} items are resolved. Final closure is a separate decision.</p>
        <button className="primary" disabled={busy} onClick={() => onSubmit(sheet.submission.closure_command)}>
          {sheet.submission.closure_label || sheet.submission.closure_command}
        </button>
      </div>
    );
  }

  return (
    <div className="review">
      <p className="review-summary"><strong>{reviewed} of {open.length} reviewed</strong>
        {item && <span className="muted"> · {item.id} selected</span>}</p>
      <div className="chips">
        {sheet.items.map((entry) => {
          const state = entry.status === "resolved" ? "resolved" : problem(entry) ?? "decided";
          return (
            <button key={entry.id} type="button" className={`chip-item ${state.replace(" ", "-")} ${entry.id === selected ? "selected" : ""}`}
              title={`${entry.id}: ${state}`} onClick={() => setSelected(entry.id)}>{entry.id}</button>
          );
        })}
      </div>
      {item && (
        <div className="review-card">
          <h3>{item.id} <span className="tag">{item.status_label ?? item.status}</span></h3>
          <p className="review-title">{item.summary}</p>
          {runId && item.chapter_id && <p><a href={`#/runs/${runId}/chapters/${encodeURIComponent(item.chapter_id)}`}>
            Read {item.chapter_id} beside its source</a></p>}
          <dl className="review-details">
            {item.details.filter((row) => !repeatsReviewedText(row.value, reviewedText))
              .map((row, i) => <div key={i}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}
          </dl>
          {item.status !== "resolved" ? (
            <>
              <label className="review-note-label" htmlFor={`note-${item.id}`}>Note or full replacement text</label>
              <textarea id={`note-${item.id}`} rows={3} value={drafts[item.id]?.note ?? ""}
                placeholder="Required for decisions marked with *; otherwise optional."
                onChange={(e) => update(item.id, { note: e.target.value })} />
              <div className="row">
                {item.allowed_decisions.map((id) => (
                  <button key={id} type="button" className={`decision ${drafts[item.id]?.decision === id ? "chosen" : ""}`}
                    onClick={() => update(item.id, { decision: id })}>
                    {decisions[id].label}{decisions[id].requires_note ? " *" : ""}
                  </button>
                ))}
                <button type="button" className="link" onClick={() => update(item.id, { decision: "", note: "" })}>Clear</button>
              </div>
              {problem(item) === "needs note" && <div className="error">This decision needs a note.</div>}
            </>
          ) : <p className="muted">Resolved in an earlier revision.</p>}
          <div className="review-nav">
            <button type="button" className="link" disabled={index <= 0} onClick={() => setSelected(sheet.items[index - 1].id)}>Previous</button>
            <button type="button" className="link" disabled={index >= sheet.items.length - 1} onClick={() => setSelected(sheet.items[index + 1].id)}>Next</button>
            {reviewed < open.length && (
              <span className="muted review-blocked">
                {(() => {
                  const undecided = open.filter((entry) => problem(entry) === "undecided").map((entry) => entry.id);
                  const notes = open.filter((entry) => problem(entry) === "needs note").map((entry) => entry.id);
                  return [undecided.length ? `Decide ${undecided.join(", ")}` : "", notes.length ? `add a note for ${notes.join(", ")}` : ""]
                    .filter(Boolean).join("; ") + " to submit.";
                })()}
              </span>
            )}
            <button type="button" className="primary" disabled={busy || reviewed < open.length} onClick={submit}>
              Submit all {open.length} decisions
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
