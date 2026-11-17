import { useEffect, useRef, useState } from "react";
import { api, type RunDetail } from "../api";
import { ErrorBox, Status, useLoad } from "./common";
import { WHOLE_BOOK, workflowUI } from "../workflows";
import { GatePanel } from "./GatePanel";
import { ChapterPanes } from "./ChapterPanes";
import { clearComments, type InlineComment } from "./CommentableText";
import { runState, useLive } from "../live";
import { TokenUsage } from "./TokenUsage";
import { DocxDelivery } from "./DocxDelivery";
import { Overview } from "./Overview";
import { ApprovedSheets } from "./ApprovedSheets";

// The chapter viewer: a run's review page, generic across workflows. It lays out the chapter list, the reading
// panes, and the decision slots; the run's WorkflowUI decides what differs (the panes, decision wording, statuses).
export function Chapters({ runId, chapterId }: { runId: string; chapterId?: string }) {
  // The chapter list, text, and status follow the run as it moves: all three reload when its state changes.
  const changed = useLive(runState(runId));
  const index = useLoad(() => api.chapters(runId), [runId], changed);
  const overview = useLoad(() => (!chapterId ? api.overview(runId) : Promise.resolve(null)), [runId, chapterId], changed);
  const chapter = useLoad(() => (chapterId ? api.chapter(runId, chapterId) : Promise.resolve(null)), [runId, chapterId],
    changed);
  const detail = chapterId ? chapter : { ...overview, data: overview.data?.source ?? null };
  const run = useLoad(() => api.run(runId), [runId], changed);
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
  const selectedId = chapterId ?? index.data?.overview?.source_unit_id;
  const here = pending && pending.chapter_id === selectedId ? pending : null;
  const active = here ?? (unattached && index.data?.prepared ? waiting : null);
  const panes = detail.data ? ui.panes(detail.data, here) : [];
  const commentable = panes.find((pane) => pane.commentKey);
  const comments = commentable?.commentKey ? commentsByKey[commentable.commentKey] ?? [] : [];
  const reviewed = panes.find((pane) => pane.reviewTarget && pane.text != null);
  const data = index.data;
  const stageTitle = (stage: string) => data?.stage_info?.[stage]?.title ?? stage;
  const stageKind = (stage: string) => data?.stage_info?.[stage]?.stage ?? stage;
  const currentPass = run.data?.passes?.slice(-1)[0];
  const pendingStage = (stage: string) => !!pending && pending.stage === stageKind(stage)
    && (!data?.stage_info?.[stage] || stage === `${currentPass?.number}-${pending.stage}`);
  useEffect(() => {
    // A new decision on another chapter: switch to that chapter once, so its form is in view.
    if (!pending) return;
    const destination = ui.decisionPage(run.data!);
    if (!destination || window.location.hash === destination) return;
    const key = `chapter-gate-opened:${pending.id}`;
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, "1");
    window.location.hash = destination;
  }, [waiting?.id]);  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    // Whole-book findings can link to any source unit, including front matter.
    if (chapterId && chapterId === index.data?.overview?.source_unit_id) {
      window.location.replace(`#/runs/${runId}/overview`);
    }
  }, [runId, chapterId, index.data?.overview?.source_unit_id]);

  // Bring a pending decision into view once per decision (on arrival, and when the agent answers feedback with a
  // new request), so the reviewer lands on the form instead of the top of the page.
  const decisionRef = useRef<HTMLDivElement>(null);
  const shown = useRef<string | null>(null);
  useEffect(() => {
    if (!active || (here && !detail.data) || (!chapterId && !overview.data) || shown.current === active.id) return;
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
    void run.reload(); void index.reload(); void chapter.reload(); void overview.reload();
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
          setNotice(ui.afterReply(gate, text, run.data?.viewer_target));
        }} />
      <ErrorBox error={exchangeError} />
    </>
  );
  const statusTags = (outputs: Record<string, { status: string; ready: boolean; saving?: boolean }> | undefined,
    id: string, className: string) => data?.stages.map((stage) => {
    const status = chapterStatus(outputs?.[stage], ui.stageVerb(stageKind(stage)),
      pending?.chapter_id === id && pendingStage(stage) ? ui.awaitingLabel(pending) : null, !!run.data?.finalized);
    return <span key={stage} className={`${className} ${status.cls}`}>{data.stages.length > 1 ? `${stageTitle(stage)}: ` : ""}{status.label}</span>;
  });
  return (
    <section>
      <p><a href={`#/runs/${runId}`}>← Run {runId.slice(0, 8)}</a></p>
      <h1>{!chapterId ? data?.overview?.title ?? "Overview" : "Chapters"}</h1>
      {run.data && <RunStatusBar run={run.data} />}
      {run.data && <TokenUsage usage={run.data.usage} />}
      <ErrorBox error={index.error} />
      <ErrorBox error={overview.error} />
      {data && !data.prepared && !unattached && <p className="muted">The agent is preparing the manuscript; chapters appear here
        once preparation completes, and you are brought to each decision as it comes up.</p>}
      {data && (
        <div className="split">
          <nav className="viewer-navigation" aria-label="Manuscript navigation">
            <div className={!chapterId ? "selected overview-entry" : "overview-entry"}>
              <a href={`#/runs/${runId}/overview`}>{data.overview?.title ?? "Overview"}</a>
              <div><span className="tag">Overview</span>
                {waiting && run.data?.viewer_target?.kind === "overview"
                  && !(pending?.chapter_id === data.overview?.source_unit_id && data.stages.some(pendingStage))
                  && <span className="tag awaiting-tag">{ui.awaitingLabel(waiting)}</span>}
                {data.overview && statusTags(data.overview.outputs,
                  data.overview.source_unit_id ?? "", "tag")}</div>
              {Object.entries(data.whole_book).filter(([, status]) => status).map(([stage, status]) => (
                <p key={stage} className="muted">{run.data?.workflow === "literary-translation"
                  ? "Whole-book consistency" : `Whole book, ${stageTitle(stage)}`}: {status?.replaceAll("_", " ")}</p>
              ))}
            </div>
            <h2>Chapters</h2>
            <ol className="list chapters">
              {data.chapters.map((chapter) => (
                <li key={chapter.chapter_id} className={chapter.chapter_id === chapterId ? "selected" : ""}>
                  <a href={`#/runs/${runId}/chapters/${encodeURIComponent(chapter.chapter_id)}`}>
                    {chapter.display_number != null ? `${chapter.display_number}. ` : ""}{chapter.title ?? chapter.chapter_id}
                  </a>
                  <div><span className="tag ready">prepared</span>{statusTags(chapter.outputs, chapter.chapter_id, "tag")}</div>
                </li>
              ))}
            </ol>
            <ApprovedSheets key={runId} runId={runId} changed={changed} />
          </nav>
          <div>
            {!chapterId && pending && !here && <p><a className="button" href={ui.gateLink(run.data!)}>
              Open {pending.chapter_id} for your decision</a></p>}
            {notice && <div className="banner final">{notice}</div>}
            {!chapterId && overview.data && run.data && <Overview data={overview.data} run={run.data} />}
            <ErrorBox error={detail.error} />
            {detail.data && (
              <>
                <h2>{!chapterId ? ui.frontMatterLabel : detail.data.chapter.title ?? detail.data.chapter.chapter_id}{" "}
                  {statusTags(!chapterId ? data.overview?.outputs
                    : data.chapters.find((c) => c.chapter_id === chapterId)?.outputs, selectedId ?? "", "tag status")}
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
            {run.data?.production?.docx && run.data.status !== "WAITING_FOR_ACCEPTANCE"
              && <DocxDelivery run={run.data} perform={(operation) => void performExchange(operation)} />}
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
  const state = working ? (run.stage === "produce-docx" ? "formatter working" : "agent working")
    : run.status === "WAITING_FOR_HUMAN" ? "waiting for you"
    : run.status === "WAITING_FOR_ACCEPTANCE" ? run.acceptance?.title : null;
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
        {run.progress && <span>{run.progress.completed}/{run.progress.total} manuscript units</span>}
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
