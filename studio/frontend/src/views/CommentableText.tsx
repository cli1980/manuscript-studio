import { useEffect, useRef, useState, type ReactNode } from "react";
import { Annotorious, useAnnotations, useAnnotator } from "@annotorious/react";
import {
  createBody, TextAnnotationPopup, TextAnnotator,
  type RecogitoTextAnnotator, type TextAnnotation, type TextAnnotationPopupContentProps,
} from "@recogito/react-text-annotator";

// Inline comments on rendered text (translations and translation documents), drafted in the browser until the
// reviewer sends them as feedback. Each comment keeps its quote, character range, and paragraph number, so a
// later source/translation alignment can show it beside the matching original paragraph.

export interface InlineComment {
  id: string;
  quote: string;
  start: number;
  end: number;
  paragraph: number | null;  // 1-based top-level block of the rendered text, like the passage map's numbering.
  note: string;
}

type Stored = { id: string; quote: string; start: number; end: number; note: string; paragraph: number | null };

export function loadComments(storageKey: string): InlineComment[] {
  try { return JSON.parse(localStorage.getItem(storageKey) ?? "[]"); } catch { return []; }
}

export function clearComments(storageKey: string) {
  localStorage.removeItem(storageKey);
}

// Which top-level block (paragraph) of the rendered text a range starts in.
function paragraphOf(container: HTMLElement | null, range?: Range): number | null {
  const root = container?.querySelector(".markdown") ?? container;
  if (!root || !range) return null;
  let node: Node | null = range.startContainer;
  while (node && node.parentNode !== root) node = node.parentNode;
  return node ? Array.prototype.indexOf.call(root.children, node) + 1 : null;
}

function toComment(annotation: TextAnnotation, container: HTMLElement | null): InlineComment {
  const selector = annotation.target.selector[0] as TextAnnotation["target"]["selector"][number] & { range?: Range };
  const note = annotation.bodies.find((b) => b.purpose === "commenting")?.value ?? "";
  return { id: annotation.id, quote: selector?.quote ?? "", start: selector?.start ?? 0, end: selector?.end ?? 0,
    paragraph: paragraphOf(container, selector?.range), note };
}

function Sync({ storageKey, container, onChange }: {
  storageKey: string; container: React.RefObject<HTMLDivElement | null>; onChange: (comments: InlineComment[]) => void;
}) {
  const annotator = useAnnotator<RecogitoTextAnnotator>();
  const annotations = useAnnotations<TextAnnotation>(150);
  const restored = useRef(false);
  useEffect(() => {
    if (!annotator || restored.current) return;
    restored.current = true;
    const saved: Stored[] = loadComments(storageKey);
    annotator.setAnnotations(saved.map((c) => ({
      id: c.id, bodies: c.note ? [{ id: `${c.id}-note`, annotation: c.id, purpose: "commenting", value: c.note }] : [],
      target: { annotation: c.id, selector: [{ quote: c.quote, start: c.start, end: c.end }] },
    })) as unknown as TextAnnotation[], true);
  }, [annotator, storageKey]);
  useEffect(() => {
    if (!restored.current) return;
    const comments = annotations.map((a) => toComment(a, container.current));
    localStorage.setItem(storageKey, JSON.stringify(comments));
    onChange(comments);
  }, [annotations]);  // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

function CommentPopup({ annotation }: TextAnnotationPopupContentProps) {
  const annotator = useAnnotator<RecogitoTextAnnotator>();
  const existing = annotation.bodies.find((b) => b.purpose === "commenting")?.value ?? "";
  const [note, setNote] = useState(existing);
  // Focus without scrolling: the popup is positioned after its first render, so a plain autofocus would
  // scroll the page to where it first appears (the top).
  const input = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    const frame = requestAnimationFrame(() => input.current?.focus({ preventScroll: true }));
    return () => cancelAnimationFrame(frame);
  }, []);
  const save = () => {
    const others = annotation.bodies.filter((b) => b.purpose !== "commenting");
    annotator.updateAnnotation({ ...annotation, bodies: note.trim()
      ? [...others, createBody(annotation, { purpose: "commenting", value: note.trim() })] : others });
    annotator.cancelSelected?.();
  };
  const remove = () => { annotator.removeAnnotation(annotation.id); };
  return (
    <div className="comment-popup">
      <div className="muted">“{annotation.target.selector[0]?.quote?.slice(0, 80)}”</div>
      <textarea ref={input} rows={3} value={note} placeholder="Your comment on this passage"
        onChange={(e) => setNote(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) save(); }} />
      <div className="row">
        <button className="primary" onClick={save}>Save comment</button>
        <button onClick={remove}>Delete</button>
      </div>
    </div>
  );
}

// Select text to comment on it; click a highlight to edit or delete the comment.
export function CommentableText({ storageKey, onChange, children }: {
  storageKey: string; onChange: (comments: InlineComment[]) => void; children: ReactNode;
}) {
  const container = useRef<HTMLDivElement>(null);
  return (
    <Annotorious>
      <div ref={container} className="commentable">
        <TextAnnotator>{children}</TextAnnotator>
      </div>
      <TextAnnotationPopup popup={(props) => <CommentPopup {...props} />} />
      <Sync storageKey={storageKey} container={container} onChange={onChange} />
    </Annotorious>
  );
}

// The feedback text sent to the agent: one line per comment, anchored by paragraph and quote.
export function composeComments(comments: InlineComment[], general: string, label = "the translation") {
  const lines = comments.filter((c) => c.note.trim()).sort((a, b) => a.start - b.start).map((c) => {
    const quote = c.quote.length > 120 ? c.quote.slice(0, 117) + "…" : c.quote;
    return `- ${c.paragraph ? `P${c.paragraph} ` : ""}“${quote.replace(/\s+/g, " ")}”: ${c.note.trim().replace(/\s*\n\s*/g, " ")}`;
  });
  const parts = lines.length ? [`Comments on ${label} (paragraphs numbered as displayed):`, ...lines] : [];
  if (general.trim()) parts.push(`${lines.length ? "General: " : ""}${general.trim()}`);
  return parts.join("\n");
}

// The list of drafted comments and the send controls shared by every feedback panel.
export function CommentSummary({ comments, general, onGeneral, onSend, busy, sendLabel = "Send comments" }: {
  comments: InlineComment[]; general: string; onGeneral: (text: string) => void; onSend: () => void;
  busy?: boolean; sendLabel?: string;
}) {
  const written = comments.filter((c) => c.note.trim());
  return (
    <div className="comment-summary">
      <div className="label">Your comments ({written.length})</div>
      {written.length === 0 && <p className="muted">Select text in the translation to comment on it.</p>}
      <ul>
        {written.map((c) => (
          <li key={c.id}><span className="muted">{c.paragraph ? `P${c.paragraph} ` : ""}“{c.quote.slice(0, 60)}{c.quote.length > 60 ? "…" : ""}”</span> {c.note}</li>
        ))}
      </ul>
      {comments.length > written.length && <p className="muted">{comments.length - written.length} highlight(s) without a comment are not sent.</p>}
      <input value={general} onChange={(e) => onGeneral(e.target.value)} placeholder="General comment (optional)" />
      <button disabled={busy || (!written.length && !general.trim())} onClick={onSend}>{sendLabel}</button>
    </div>
  );
}
