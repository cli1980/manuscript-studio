import { useCallback, useEffect, useRef, useState } from "react";
import { Markdown } from "./Markdown";
import { CommentableText, type InlineComment } from "./CommentableText";

/** Load data when `deps` change, and again whenever `refresh` (a change key from the live feed) moves. */
export function useLoad<T>(load: () => Promise<T>, deps: unknown[], refresh?: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loadRef = useRef(load);
  loadRef.current = load;
  const reload = useCallback(async () => {
    try {
      setData(await loadRef.current());
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    }
  }, []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void reload(); }, deps);
  const seen = useRef(refresh);
  useEffect(() => {
    // The first key also reloads: something may have changed between the initial load and the first snapshot.
    if (refresh == null || refresh === seen.current) return;
    seen.current = refresh;
    void reload();
  }, [refresh, reload]);
  return { data, error, reload, setData };
}

export function ErrorBox({ error }: { error: string | null }) {
  return error ? <div className="error" role="alert">{error}</div> : null;
}

export function Status({ value }: { value: string }) {
  return <span className={`status status-${value.toLowerCase()}`}>{value.replaceAll("_", " ")}</span>;
}

export function TextBlock({ text }: { text: string }) {
  return <pre className="text">{text}</pre>;
}

export function when(value?: string | null) {
  return value ? new Date(value).toLocaleString() : "";
}

// Readable name of a review: metadata_review -> "metadata", translation_brief -> "translation brief".
export function reviewName(kind: string) {
  return REVIEW_NAMES[kind] ?? kind.replace(/_review$/, "").replaceAll("_", " ");
}

const REVIEW_NAMES: Record<string, string> = { pass_review: "pass result", pass_choice: "next pass" };

const DOCUMENT_TITLES: Record<string, string> = { "glossary.md": "Glossary", "voice.md": "Voice notes",
  "brief-samples.md": "Sample translations" };

export function documentTitle(path: string) {
  const name = path.split("/").pop() ?? path;
  return DOCUMENT_TITLES[name] ?? name;
}

// Workspace documents presented for review, such as a translation brief's glossary, voice notes, and samples:
// one tab per document, rendered as formatted text.
export function Documents({ documents, commentKey, onComments }: {
  documents: { path: string; text: string }[];
  commentKey?: string;  // When set, the documents accept inline comments (drafted in the browser under this key).
  onComments?: (path: string, comments: InlineComment[]) => void;
}) {
  const [active, setActive] = useState(0);
  const doc = documents[Math.min(active, documents.length - 1)];
  if (!doc) return null;
  return (
    <div className="documents">
      <div className="doc-tabs" role="tablist">
        {documents.map((d, i) => (
          <button key={d.path} type="button" role="tab" aria-selected={d === doc} className={d === doc ? "active" : ""}
            onClick={() => setActive(i)} title={d.path}>{documentTitle(d.path)}</button>
        ))}
      </div>
      <div className="doc-body" role="tabpanel">
        {commentKey && onComments
          ? <CommentableText key={`${commentKey}:${doc.path}`} storageKey={`${commentKey}:${doc.path}`}
              onChange={(comments) => onComments(doc.path, comments)}><Markdown text={doc.text} /></CommentableText>
          : <Markdown text={doc.text} />}
      </div>
    </div>
  );
}
