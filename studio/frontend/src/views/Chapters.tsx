import { useEffect, useState } from "react";
import { api, type Gate, type RunDetail } from "../api";
import { Documents, ErrorBox, reviewName, Status, TextBlock, useLoad, when } from "./common";
import { SheetReview } from "./SheetReview";
import { GatePanel } from "./GatePanel";
import { Markdown } from "./Markdown";
import { clearComments, CommentableText, CommentSummary, composeComments, type InlineComment } from "./CommentableText";

// Chapter browser inside a workflow run: prepared chapters and each stage's completed outputs.
export function Chapters({ runId, chapterId }: { runId: string; chapterId?: string }) {
  const index = useLoad(() => api.chapters(runId), [runId], 4000);
  const detail = useLoad(() => (chapterId ? api.chapter(runId, chapterId) : Promise.resolve(null)), [runId, chapterId]);
  const run = useLoad(() => api.run(runId), [runId], 4000);
  const [approved, setApproved] = useState<string | null>(null);
  const gate = run.data?.status === "WAITING_FOR_HUMAN" && run.data.gate?.kind === "chapter_sanity" ? run.data.gate : null;
  const draft = gate && chapterId && gate.chapter_id === chapterId ? gate.binding_text : null;
  // Feedback on the assembled draft is given as inline comments on the translation, drafted in the browser.
  const commentKey = gate && !gate.sheet ? `comments:${gate.id}:draft` : null;
  const [comments, setComments] = useState<InlineComment[]>([]);
  // Any human exchange for a chapter (translation advice, questions, map exceptions) is shown with that chapter.
  const pending = run.data?.status === "WAITING_FOR_HUMAN" && run.data.gate?.chapter_id ? run.data.gate : null;
  const unattached = run.data?.status === "WAITING_FOR_HUMAN" && run.data.gate && !run.data.gate.chapter_id;
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
      {run.data && <RunStatusBar run={run.data} />}
      <ErrorBox error={index.error} />
      {/* Decisions not tied to a chapter, such as a question during preparation. */}
      {unattached && run.data && (
        <>
          <GatePanel run={run.data} inViewer perform={(operation) => void performExchange(operation)} />
          <ErrorBox error={exchangeError} />
        </>
      )}
      {data && !data.prepared && !unattached && <p className="muted">The agent is preparing the manuscript; chapters appear here
        once preparation completes, and you are brought to each decision as it comes up.</p>}
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
                    const status = chapterStatus(chapter.outputs[stage], stage, pending?.chapter_id === chapter.chapter_id ? awaiting(pending) : null, !!run.data?.finalized);
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
            {run.data?.status === "WAITING_FOR_ACCEPTANCE" && run.data.acceptance && (
              <>
                <GatePanel run={run.data} inViewer perform={(operation) => void performExchange(operation)} />
                <ErrorBox error={exchangeError} />
              </>
            )}
            {!chapterId && gate && <p><a className="button" href={`#/runs/${runId}/chapters/${encodeURIComponent(gate.chapter_id ?? "")}`}>Review {gate.chapter_id} for approval</a></p>}
            {approved && (
              <div className="banner final">{approved} is approved. Translation continues with the next chapter; you will be brought back here when it is ready.</div>
            )}
            {!chapterId && <p className="muted">Select a chapter to read it.</p>}
            <ErrorBox error={detail.error} />
            {detail.data && (
              <>
                <h2>{detail.data.chapter.title ?? detail.data.chapter.chapter_id} <span className="muted">({detail.data.chapter.role})</span>{" "}
                  {data.stages.map((stage) => {
                    const entry = data.chapters.find((c) => c.chapter_id === chapterId);
                    const status = chapterStatus(entry?.outputs[stage], stage, pending && pending.chapter_id === chapterId ? awaiting(pending) : null, !!run.data?.finalized);
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
                {detail.data.reviews?.length > 0 && (
                  <div className="panel reviews">
                    {detail.data.reviews.map((review) => (
                      <details key={review.kind}>
                        <summary><span className="tag ready">{review.kind === "metadata_review"
                          ? `metadata confirmed (revision ${review.record_revision})`
                          : `${reviewName(review.kind)} approved`}</span>{" "}
                          <span className="muted">{review.decision_source !== "human" ? review.decision_source : ""} {when(review.created_at)}</span></summary>
                        {review.kind === "metadata_review"
                          ? <p className="muted">The metadata is kept on the <a href={`#/works/${encodeURIComponent(run.data?.work_id ?? "")}`}>work page</a>.</p>
                          : <Documents documents={review.documents} />}
                      </details>
                    ))}
                  </div>
                )}
                <div className="columns">
                  <div><h3>Prepared</h3><Markdown text={detail.data.prepared_text} /></div>
                  {detail.data.outputs.map((output) => (
                    <div key={output.stage}><h3>{output.stage} <span className="muted mono">attempt {output.attempt} · {output.sha256.slice(0, 10)}</span></h3>
                      <Markdown text={output.text} /></div>
                  ))}
                  {draft != null && (
                    <div className="awaiting"><h3>Translation <span className="tag busy">awaiting your approval</span></h3>
                      {commentKey
                        ? <CommentableText key={commentKey} storageKey={commentKey} onChange={setComments}><Markdown text={draft} /></CommentableText>
                        : <Markdown text={draft} />}</div>
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
                  <ChapterApproval run={run.data} comments={comments} commentKey={commentKey} onDone={(closed) => {
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

// Where the run stands, so the viewer is enough to follow it; problems link to run management.
function RunStatusBar({ run }: { run: RunDetail }) {
  const working = run.status === "RUNNING" || run.worker.active;
  const state = working ? "agent working" : run.status === "WAITING_FOR_HUMAN" ? "waiting for you"
    : run.status === "WAITING_FOR_ACCEPTANCE" ? "ready to finalize" : null;
  const ended = run.status === "COMPLETED" || run.status === "CANCELLED";
  const problem = !run.engine_current && !ended && !run.finalized
    ? "The workflow engine changed after this run started; it can only be restarted."
    : run.status === "FAILED" ? `The last step failed${run.error ? `: ${run.error}` : "."}`
    : run.status === "BLOCKED" ? `The run is blocked${run.error ? `: ${run.error}` : "."}`
    : run.worker.paused ? "The run is paused." : null;
  return (
    <>
      <div className="run-bar">
        <strong>{run.template_title ?? run.template_id}</strong>
        <span>stage {run.stage}</span>
        {run.progress && <span>{run.progress.completed}/{run.progress.total} chapters</span>}
        <Status value={run.status} />
        {state && <span className={`tag ${working ? "busy" : "awaiting-tag"}`}>{state}</span>}
      </div>
      {problem && <div className="banner warn">{problem} <a href={`#/runs/${run.id}`}>Open run management</a> to retry, resume, or restart.</div>}
    </>
  );
}

// Chapter approval happens here, beside the source: approve the assembled draft or review proposed edits.
function ChapterApproval({ run, comments, commentKey, onDone }: {
  run: RunDetail; comments: InlineComment[]; commentKey: string | null; onDone: (closed: boolean) => void;
}) {
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
      if (commentKey) clearComments(commentKey);
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
              <Markdown text={gate.message} />
            </div>
          ) : (
            <p className="muted">The final check proposes no changes. Read the translation beside the source, then approve it, or
              select text in the translation to comment on it and send your comments (comments are feedback and do not
              approve the chapter).</p>
          )}
          <div className="row">
            <button className="primary" disabled={busy} onClick={() => void reply(gate.commands[0] ?? "approve chapter")}>Approve chapter</button>
          </div>
          <CommentSummary comments={comments} general={feedback} onGeneral={setFeedback} busy={busy}
            onSend={() => void reply(composeComments(comments, feedback))} />
        </>
      )}
      <ErrorBox error={error} />
    </div>
  );
}

const STAGE_VERBS: Record<string, string> = { translate: "translating", line: "line editing", copy: "copyediting",
  developmental: "developmental review" };

// Front-matter reviews (metadata, or a workflow's documents such as a translation brief) are reviews; the rest decisions.
function awaiting(gate: Gate) {
  if (gate.kind === "chapter_sanity") return "chapter_sanity";
  return gate.kind === "metadata_review" || gate.documents?.length > 0
    ? `awaiting your review: ${reviewName(gate.kind)}` : `awaiting your decision: ${gate.kind.replaceAll("_", " ")}`;
}

// One readable status per chapter and stage: not started, working, awaiting approval, approved, or final.
function chapterStatus(output: { status: string; ready: boolean; saving?: boolean } | undefined, stage: string, awaiting: string | null, finalized: boolean) {
  if (awaiting === "chapter_sanity") return { label: "awaiting your approval", cls: "awaiting-tag" };
  if (awaiting) return { label: awaiting, cls: "awaiting-tag" };
  if (output?.ready || output?.status === "completed") return finalized ? { label: "final", cls: "ready" } : { label: "approved", cls: "ready" };
  if (output?.status === "in_progress" && output.saving) return { label: "approved — saving", cls: "ready" };
  if (output?.status === "in_progress") return { label: STAGE_VERBS[stage] ?? "in progress", cls: "busy" };
  return { label: "not started", cls: "" };
}
