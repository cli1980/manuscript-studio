import { useCallback, useEffect, useRef, useState } from "react";

export function useLoad<T>(load: () => Promise<T>, deps: unknown[], intervalMs?: number) {
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
  useEffect(() => {
    void reload();
    if (!intervalMs) return;
    const timer = window.setInterval(() => void reload(), intervalMs);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, intervalMs]);
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
  return kind.replace(/_review$/, "").replaceAll("_", " ");
}

// Workspace documents presented for review, such as a translation brief's glossary and voice notes.
export function Documents({ documents, open = true }: { documents: { path: string; text: string }[]; open?: boolean }) {
  return (
    <>
      {documents.map((doc) => (
        <details key={doc.path} className="panel document" open={open}>
          <summary className="mono">{doc.path.split("/").pop()}</summary>
          <TextBlock text={doc.text} />
        </details>
      ))}
    </>
  );
}
