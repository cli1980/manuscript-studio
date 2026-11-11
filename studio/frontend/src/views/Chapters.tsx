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
  const isFrontMatter = index.data?.chapters.find((chapter) => chapter.chapter_id === chapterId)?.role === "front_matter";
  const detail = useLoad(() => (chapterId ? api.chapter(runId, chapterId) : Promise.resolve(null)), [runId, chapterId],
    isFrontMatter ? 4000 : undefined);
  const run = useLoad(() => api.run(runId), [runId], 4000);
  const ui = workflowUI(run.data?.workflow);
  const [notice, setNotice] = useState<string | null>(null);
  // Annotation callbacks can arrive after navigation; keep each draft under its own review key.
  const [commentsByKey, setCommentsByKey] = useState<Record<string, InlineComment[]>>({});
  const [exchangeError, setExchangeError] = useState<string | null>(null);
  // Every decision follows the reading area, whatever its kind: a chapter's decision under that chapter's text,
  // and decisions not tied to one chapter (whole-book jobs, pass choices, final acceptance) at the end of the
  // content column. Before chapters exist, the decision is the page's only content.
  const waiting = run.data?.status === "WAITING_FOR_HUMAN" && run.data.gate ? run.data.gate : null;
  const pending = waiting?.chapter_id && waiting.chapter_id !== WHOLE_BOOK ? waiting : null;
  const unattached = !!waiting && !pending;
  const here = pending && pending.chapter_id === chapterId ? pending : null;
  const active = here ?? (unattached && index.data?.prepared ? waiting : null);
  const panes = detail.data ? ui.panes(detail.data, here) : [];
  const commentable = panes.find((pane) => pane.commentKey);
  const comments = commentable?.commentKey ? commentsByKey[commentable.commentKey] ?? [] : [];
  const reviewed = panes.find((pane) => pane.reviewTarget && pane.text != null);
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

  // Bring a pending decision into view once per decision (on arrival, and when the agent answers feedback with a
  // new request), so the reviewer lands on the form instead of the top of the page.
  const decisionRef = useRef<HTMLDivElement>(null);
  const shown = useRef<string | null>(null);
  useEffect(() => {
    if (!active || (chapterId && !detail.data) || shown.current === active.id) return;
    shown.current = active.id;
    requestAnimationFrame(() => decisionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }, [active?.id, detail.data]);  // eslint-disable-line react-hooks/exhaustive-deps

  async function performExchange(operation: () => Promise<RunDetail>) {
    try {
      await operation();
      setExchangeError(null);
    } catch (exc) {
      setExchangeError(exc instanceof Error ? exc.message : String(exc));
    }
    void run.reload(); void index.reload(); void detail.reload();
  }

  // One decision slot, used under a chapter's text (with its inline comments) and at the end of the content column.
  const decision = (beside: boolean) => run.data && (
    <>
      <GatePanel run={run.data} inViewer perform={(operation) => void performExchange(operation)}
        reviewedText={beside && reviewed?.reviewTarget && reviewed.text != null
          ? { text: reviewed.text } : undefined}
        comments={beside && commentable ? comments : undefined} commentLabel={commentable?.commentLabel}
        onSent={(gate, text) => {
          if (beside && commentable?.commentKey) {
            const key = commentable.commentKey;
            clearComments(key);
            setCommentsByKey((old) => ({ ...old, [key]: [] }));
          }
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
      {unattached && data && !data.prepared && decision(false)}
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
              <li key={stage} className="muted">{run.data?.workflow === "literary-translation"
                ? "Whole-book consistency" : `Whole book, ${stageTitle(stage)}`}: {status?.replaceAll("_", " ")}</li>
            ))}
          </ol>
          <div>
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
                {detail.data.chapter.supplied_title && (
                  <div className="banner warn">The source has no title. The heading “{detail.data.chapter.supplied_title.text}” was
                    supplied from {SUPPLIED_BASIS[detail.data.chapter.supplied_title.basis]} ({detail.data.chapter.supplied_title.evidence}).
                    {" "}If it is wrong, correct the title in the metadata and restart preparation from <a href={`#/runs/${runId}`}>run management</a>.</div>
                )}
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
                      <div key={review.kind}>
                        {!!review.current_documents?.length && (
                          <div className="current-documents">
                            <h3>{run.data?.finalized ? "Final" : "Current"} {reviewName(review.kind)}</h3>
                            <p className="muted">{run.data?.finalized
                              ? "Documents saved with the accepted output."
                              : "Latest saved documents, including corrections and additions made during translation."}</p>
                            <Documents documents={review.current_documents} />
                          </div>
                        )}
                        <details>
                          <summary><span className="tag ready">{review.kind === "metadata_review"
                            ? `metadata confirmed (revision ${review.record_revision})`
                            : `Approved ${reviewName(review.kind)} — snapshot`}</span>{" "}
                            <span className="muted">{review.decision_source !== "human" ? review.decision_source : ""} {when(review.created_at)}</span></summary>
                          {review.kind === "metadata_review"
                            ? <p className="muted">The metadata is kept on the <a href={`#/works/${encodeURIComponent(run.data?.work_id ?? "")}`}>work page</a>.</p>
                            : <Documents documents={review.documents} />}
                        </details>
                      </div>
                    ))}
                  </div>
                )}
                <ChapterPanes panes={panes}
                  onComments={(key, comments) => setCommentsByKey((old) => ({ ...old, [key]: comments }))} />
                {detail.data.outputs.flatMap((output) => output.consistency_changes ?? []).length > 0 && (
                  <details className="panel">
                    <summary>Applied consistency fixes</summary>
                    {detail.data.outputs.flatMap((output) => output.consistency_changes ?? []).map((fix) => (
                      <div key={`${fix.receipt_id}:${fix.id}`}>
                        <h3>{fix.id}</h3><p>{fix.reason}</p>
                        <dl><dt>Before</dt><dd>{fix.before}</dd><dt>After</dt><dd>{fix.after}</dd></dl>
                      </div>
                    ))}
                  </details>
                )}
                {/* The decision sits under the text, after the reviewer has read it. */}
                {here && <div ref={decisionRef} className="decision-anchor">{decision(true)}</div>}
              </>
            )}
            {unattached && <div ref={decisionRef} className="decision-anchor">{decision(false)}</div>}
            {run.data?.status === "WAITING_FOR_ACCEPTANCE" && run.data.acceptance && (
              <div className="decision-anchor">{decision(false)}</div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

const SUPPLIED_BASIS = { metadata: "the work's metadata", document_properties: "the document's properties",
  source_name: "the file name" } as const;

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
      {run.workflow === "literary-translation" && run.whole_book_status && run.progress?.completed === run.progress?.total && (
        <div className="banner">
          All chapters translated. {run.whole_book_status === "completed" ? "Whole-book consistency complete."
            : run.status === "FAILED" || run.status === "BLOCKED" ? "Whole-book consistency needs recovery."
            : run.worker.paused ? "Whole-book consistency is paused."
            : run.gate?.kind === "translation_consistency" ? "Whole-book consistency needs your review."
            : run.whole_book_status === "in_progress" ? "Checking whole-book consistency."
            : "Whole-book consistency is next."}
        </div>
      )}
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
