import { useEffect, useState } from "react";
import { api, type RunDetail } from "../api";
import { ErrorBox, TextBlock, useLoad } from "./common";
import { SheetReview } from "./SheetReview";
import { GatePanel } from "./GatePanel";

// Chapter browser inside a workflow run: prepared chapters and each stage's completed outputs.
export function Chapters({ runId, chapterId }: { runId: string; chapterId?: string }) {
  const index = useLoad(() => api.chapters(runId), [runId], 4000);
  const detail = useLoad(() => (chapterId ? api.chapter(runId, chapterId) : Promise.resolve(null)), [runId, chapterId]);
  const run = useLoad(() => api.run(runId), [runId], 4000);
  const [approved, setApproved] = useState<string | null>(null);
  const gate = run.data?.status === "WAITING_FOR_HUMAN" && run.data.gate?.kind === "chapter_sanity" ? run.data.gate : null;
  const draft = gate && chapterId && gate.chapter_id === chapterId ? gate.binding_text : null;
  // Any human exchange for a chapter (translation advice, questions, map exceptions) is shown with that chapter.
  const pending = run.data?.status === "WAITING_FOR_HUMAN" && run.data.gate?.chapter_id ? run.data.gate : null;
  const [exchangeError, setExchangeError] = useState<string | null>(null);
  // Keep the chapter list, text, and status in step with the run as it moves.
  const progressKey = `${run.data?.status}|${run.data?.gate?.id ?? ""}|${run.data?.progress?.completed ?? ""}|${run.data?.chapter_id ?? ""}`;
  useEffect(() => { void index.reload(); void detail.reload(); }, [progressKey]);  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    // A new decision on another chapter: switch to that chapter once, so its form is in view.
    if (!pending || pending.chapter_id === chapterId) return;
    const key = `chapter-gate-opened:${pending.id}`;
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, "1");
    window.location.hash = `#/runs/${runId}/chapters/${encodeURIComponent(pending.chapter_id ?? "")}`;
  }, [pending?.id]);  // eslint-disable-line react-hooks/exhaustive-deps

  async function performExchange(operation: () => Promise<RunDetail>) {
    try {
      await operation();
      setExchangeError(null);
    } catch (exc) {
      setExchangeError(exc instanceof Error ? exc.message : String(exc));
    }
    void run.reload(); void index.reload(); void detail.reload();
  }
  const data = index.data;
  return (
    <section>
      <p><a href={`#/runs/${runId}`}>← Run {runId.slice(0, 8)}</a></p>
      <h1>Chapters</h1>
      <ErrorBox error={index.error} />
      {data && !data.prepared && <p className="muted">Chapters appear here once preparation completes.</p>}
      {data && data.prepared && (
        <div className="split">
          <ol className="list chapters">
            {data.chapters.map((chapter) => (
              <li key={chapter.chapter_id} className={chapter.chapter_id === chapterId ? "selected" : ""}>
                <a href={`#/runs/${runId}/chapters/${encodeURIComponent(chapter.chapter_id)}`}>
                  {chapter.order}. {chapter.title ?? chapter.chapter_id}
                </a>
                <div>
                  <span className="tag ready">prepared</span>
                  {data.stages.map((stage) => {
                    const status = chapterStatus(chapter.outputs[stage], stage, pending?.chapter_id === chapter.chapter_id ? pending.kind : null, !!run.data?.finalized);
                    return <span key={stage} className={`tag ${status.cls}`}>{data.stages.length > 1 ? `${stage}: ` : ""}{status.label}</span>;
                  })}
                </div>
              </li>
            ))}
            {Object.entries(data.whole_book).filter(([, status]) => status).map(([stage, status]) => (
              <li key={stage} className="muted">Whole-book {stage} pass: {status?.replaceAll("_", " ")}</li>
            ))}
          </ol>
          <div>
            {!chapterId && gate && <p><a className="button" href={`#/runs/${runId}/chapters/${encodeURIComponent(gate.chapter_id ?? "")}`}>Review {gate.chapter_id} for approval</a></p>}
            {approved && (
              <div className="banner final">{approved} is approved. Translation continues with the next chapter; you will be brought back here when it is ready. <a href={`#/runs/${runId}`}>Back to the run</a></div>
            )}
            {!chapterId && <p className="muted">Select a chapter to read it.</p>}
            <ErrorBox error={detail.error} />
            {detail.data && (
              <>
                <h2>{detail.data.chapter.title ?? detail.data.chapter.chapter_id} <span className="muted">({detail.data.chapter.role})</span>{" "}
                  {data.stages.map((stage) => {
                    const entry = data.chapters.find((c) => c.chapter_id === chapterId);
                    const status = chapterStatus(entry?.outputs[stage], stage, pending && pending.chapter_id === chapterId ? pending.kind : null, !!run.data?.finalized);
                    return <span key={stage} className={`tag status ${status.cls}`}>{data.stages.length > 1 ? `${stage}: ` : ""}{status.label}</span>;
                  })}
                </h2>
                {detail.data.passage_map && (
                  <details className="panel"><summary>Passage map (internal): {detail.data.passage_map.passages.length} passages,
                    {" "}{detail.data.passage_map.exceptions.length} exceptions</summary>
                    <ul>{detail.data.passage_map.passages.map((p) => <li key={p.id}>{p.id}: paragraphs {p.first_paragraph}–{p.last_paragraph}</li>)}</ul>
                    {detail.data.passage_map.exceptions.map((x) => <div key={x.id} className="banner warn">{x.id} · {x.kind} · paragraphs {x.first_paragraph}–{x.last_paragraph}: {x.reason}</div>)}
                  </details>
                )}
                <div className="columns">
                  <div><h3>Prepared</h3><TextBlock text={detail.data.prepared_text} /></div>
                  {detail.data.outputs.map((output) => (
                    <div key={output.stage}><h3>{output.stage} <span className="muted mono">attempt {output.attempt} · {output.sha256.slice(0, 10)}</span></h3>
                      <TextBlock text={output.text} /></div>
                  ))}
                  {draft != null && (
                    <div className="awaiting"><h3>Translation <span className="tag busy">awaiting your approval</span></h3>
                      <TextBlock text={draft} /></div>
                  )}
                  {detail.data.outputs.length === 0 && draft == null &&
                    <div className="muted">No stage output is ready for this chapter yet.</div>}
                </div>
                {pending && pending.chapter_id === chapterId && pending.kind !== "chapter_sanity" && run.data && (
                  <>
                    <GatePanel run={run.data} inViewer perform={(operation) => void performExchange(operation)} />
                    <ErrorBox error={exchangeError} />
                  </>
                )}
                {/* Approval sits under the side-by-side text, after the reviewer has read it. */}
                {chapterId && gate?.chapter_id === chapterId && run.data && (
                  <ChapterApproval run={run.data} onDone={(closed) => {
                    if (closed) setApproved(chapterId);
                    void run.reload(); void detail.reload(); void index.reload();
                  }} />
                )}
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

// Chapter approval happens here, beside the source: approve the assembled draft or review proposed edits.
function ChapterApproval({ run, onDone }: { run: RunDetail; onDone: (closed: boolean) => void }) {
  const gate = run.gate!;
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function reply(text: string) {
    setBusy(true);
    setError(null);
    try {
      await api.reply(run.id, gate.id, text);
      setFeedback("");
      // Only the approval command or the edits sheet's closure approves the chapter; item decisions do not.
      onDone(text === (gate.commands[0] ?? "approve chapter") || text === gate.sheet?.submission.closure_command);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel gate chapter-approval">
      <h2>Approve {gate.chapter_id}</h2>
      {gate.sheet ? (
        <>
          <p className="muted">The final check proposes edits. Decide each one; the chapter is approved at closure.</p>
          <SheetReview key={gate.id} sheet={gate.sheet} busy={busy} onSubmit={(text) => void reply(text)} />
        </>
      ) : (
        <>
          {gate.answer_to ? (
            <div className="conversation">
              <div className="label">Your feedback</div>
              <TextBlock text={gate.answer_to.text} />
              <div className="label">Translator's answer</div>
              <TextBlock text={gate.message} />
            </div>
          ) : (
            <p className="muted">The final check proposes no changes. Read the translation beside the source, then approve it or
              send corrections (corrections are feedback and do not approve the chapter).</p>
          )}
          <div className="row">
            <button className="primary" disabled={busy} onClick={() => void reply(gate.commands[0] ?? "approve chapter")}>Approve chapter</button>
          </div>
          <textarea rows={3} value={feedback} placeholder="Corrections or questions for the translator"
            onChange={(e) => setFeedback(e.target.value)} />
          <button disabled={busy || !feedback.trim()} onClick={() => void reply(feedback)}>Send feedback</button>
        </>
      )}
      <ErrorBox error={error} />
    </div>
  );
}

const STAGE_VERBS: Record<string, string> = { translate: "translating", line: "line editing", copy: "copyediting",
  developmental: "developmental review" };

// One readable status per chapter and stage: not started, working, awaiting approval, approved, or final.
function chapterStatus(output: { status: string; ready: boolean; saving?: boolean } | undefined, stage: string, awaiting: string | null, finalized: boolean) {
  if (awaiting === "chapter_sanity") return { label: "awaiting your approval", cls: "awaiting-tag" };
  if (awaiting === "metadata_review") return { label: "awaiting your review: metadata", cls: "awaiting-tag" };
  if (awaiting) return { label: `awaiting your decision: ${awaiting.replaceAll("_", " ")}`, cls: "awaiting-tag" };
  if (output?.ready || output?.status === "completed") return finalized ? { label: "final", cls: "ready" } : { label: "approved", cls: "ready" };
  if (output?.status === "in_progress" && output.saving) return { label: "approved — saving", cls: "ready" };
  if (output?.status === "in_progress") return { label: STAGE_VERBS[stage] ?? "in progress", cls: "busy" };
  return { label: "not started", cls: "" };
}
