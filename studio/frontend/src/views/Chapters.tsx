import { useEffect, useRef, useState } from "react";
import { api, type RunDetail } from "../api";
import { Documents, ErrorBox, reviewName, Status, useLoad, when } from "./common";
import { WHOLE_BOOK, workflowUI } from "../workflows";
import { GatePanel } from "./GatePanel";
import { ChapterPanes } from "./ChapterPanes";
import { clearComments, type InlineComment } from "./CommentableText";

// The chapter viewer: a run's review page, generic across workflows. It lays out the chapter list, the reading
// panes, and the decision slots; the run's WorkflowUI decides what differs (the panes, decision wording, statuses).
export function Chapters({ runId, chapterId }: { runId: string; chapterId?: string }) {
  const index = useLoad(() => api.chapters(runId), [runId], 4000);
  const detail = useLoad(() => (chapterId ? api.chapter(runId, chapterId) : Promise.resolve(null)), [runId, chapterId]);
  const run = useLoad(() => api.run(runId), [runId], 4000);
  const ui = workflowUI(run.data?.workflow);
  const [notice, setNotice] = useState<string | null>(null);
  const [comments, setComments] = useState<InlineComment[]>([]);
  const [exchangeError, setExchangeError] = useState<string | null>(null);
  // A decision on a chapter is made beside that chapter's text; the rest (preparation questions, pass choices,
  // whole-book passes) at the top.
  const waiting = run.data?.status === "WAITING_FOR_HUMAN" && run.data.gate ? run.data.gate : null;
  const pending = waiting?.chapter_id && waiting.chapter_id !== WHOLE_BOOK ? waiting : null;
  const unattached = !!waiting && !pending;
  const here = pending && pending.chapter_id === chapterId ? pending : null;
  const panes = detail.data ? ui.panes(detail.data, here) : [];
  const commentable = panes.find((pane) => pane.commentKey);
  const data = index.data;
  const stageTitle = (stage: string) => data?.stage_info?.[stage]?.title ?? stage;
  const stageKind = (stage: string) => data?.stage_info?.[stage]?.stage ?? stage;
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

  // Bring a chapter's pending decision into view once per decision (on arrival, and when the agent answers
  // feedback with a new request), so the reviewer lands on the form instead of the top of the page.
  const decisionRef = useRef<HTMLDivElement>(null);
  const shown = useRef<string | null>(null);
  useEffect(() => {
    if (!here || !detail.data || shown.current === here.id) return;
    shown.current = here.id;
    requestAnimationFrame(() => decisionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }, [here?.id, detail.data]);  // eslint-disable-line react-hooks/exhaustive-deps

  async function performExchange(operation: () => Promise<RunDetail>) {
    try {
      await operation();
      setExchangeError(null);
    } catch (exc) {
      setExchangeError(exc instanceof Error ? exc.message : String(exc));
    }
    void run.reload(); void index.reload(); void detail.reload();
  }

  // One decision slot, used at the top, beside a chapter's text (with its inline comments), and for final acceptance.
  const decision = (beside: boolean) => run.data && (
    <>
      <GatePanel run={run.data} inViewer perform={(operation) => void performExchange(operation)}
        comments={beside && commentable ? comments : undefined} commentLabel={commentable?.commentLabel}
        onSent={(gate, text) => {
          if (beside && commentable?.commentKey) clearComments(commentable.commentKey);
          setNotice(ui.afterReply(gate, text));
        }} />
      <ErrorBox error={exchangeError} />
    </>
  );
  const statusTags = (outputs: Record<string, { status: string; ready: boolean; saving?: boolean }> | undefined,
    id: string, className: string) => data?.stages.map((stage) => {
    const status = chapterStatus(outputs?.[stage], ui.stageVerb(stageKind(stage)),
      pending?.chapter_id === id ? ui.awaitingLabel(pending) : null, !!run.data?.finalized);
    return <span key={stage} className={`${className} ${status.cls}`}>{data.stages.length > 1 ? `${stageTitle(stage)}: ` : ""}{status.label}</span>;
  });
  return (
    <section>
      <p><a href={`#/runs/${runId}`}>← Run {runId.slice(0, 8)}</a></p>
      <h1>Chapters</h1>
      {run.data && <RunStatusBar run={run.data} />}
      <ErrorBox error={index.error} />
      {unattached && decision(false)}
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
                <div><span className="tag ready">prepared</span>{statusTags(chapter.outputs, chapter.chapter_id, "tag")}</div>
              </li>
            ))}
            {Object.entries(data.whole_book).filter(([, status]) => status).map(([stage, status]) => (
              <li key={stage} className="muted">Whole book, {stageTitle(stage)}: {status?.replaceAll("_", " ")}</li>
            ))}
          </ol>
          <div>
            {run.data?.status === "WAITING_FOR_ACCEPTANCE" && run.data.acceptance && decision(false)}
            {!chapterId && pending && <p><a className="button" href={`#/runs/${runId}/chapters/${encodeURIComponent(pending.chapter_id ?? "")}`}>
              Open {pending.chapter_id} for your decision</a></p>}
            {notice && <div className="banner final">{notice}</div>}
            {!chapterId && <p className="muted">Select a chapter to read it.</p>}
            <ErrorBox error={detail.error} />
            {detail.data && (
              <>
                <h2>{detail.data.chapter.title ?? detail.data.chapter.chapter_id} <span className="muted">({detail.data.chapter.role})</span>{" "}
                  {statusTags(data.chapters.find((c) => c.chapter_id === chapterId)?.outputs, chapterId ?? "", "tag status")}
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
                <ChapterPanes panes={panes} onComments={setComments} />
                {/* The decision sits under the text, after the reviewer has read it. */}
                {here && <div ref={decisionRef} className="decision-anchor">{decision(true)}</div>}
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

// One readable status per chapter and stage: not started, working, awaiting approval, approved, or final.
function chapterStatus(output: { status: string; ready: boolean; saving?: boolean } | undefined, verb: string, awaiting: string | null, finalized: boolean) {
  if (awaiting) return { label: awaiting, cls: "awaiting-tag" };
  if (output?.ready || output?.status === "completed") return finalized ? { label: "final", cls: "ready" } : { label: "approved", cls: "ready" };
  if (output?.status === "in_progress" && output.saving) return { label: "approved — saving", cls: "ready" };
  if (output?.status === "in_progress") return { label: verb, cls: "busy" };
  return { label: "not started", cls: "" };
}
