import { useState } from "react";
import type { MetadataField, MetadataView } from "../api";
import { FieldEditor, prepare, type Person } from "./widgets";

type Provenance = Record<string, { origin: string; review_status: string; confidence: string | null; evidence?: unknown[] }>;

const GROUPS: { id: MetadataField["group"]; title: string; note: string }[] = [
  { id: "suggested", title: "Review and complete", note: "Correct source-supported suggestions or add missing information. Optional fields may stay empty; your corrections take precedence." },
  { id: "computed", title: "Detected or measured", note: "Language is detected from the manuscript during preparation; extent is measured from the prepared text." },
];

const LABELS: Record<string, string> = {
  "/title": "Title", "/subtitle": "Subtitle", "/contributors": "Contributors", "/audience": "Audience",
  "/edition/label": "Edition", "/edition/status": "Edition status", "/series/name": "Series",
  "/series/position": "Position in series", "/series/relationship": "Series relationship",
  "/work_type": "Work type", "/form": "Form", "/genres": "Genres", "/keywords": "Keywords",
  "/description": "Description", "/original_language": "Original language",
  "/manuscript_language": "Manuscript language", "/extent": "Extent",
};

const CLUES: Record<string, string> = {
  "/title": "As it should appear on the cover.",
  "/subtitle": "Optional; leave empty if the book has none.",
  "/contributors": "Everyone who should be credited, each with at least one role.",
  "/audience": "Who you are writing for.",
  "/edition/label": "Leave empty for a first manuscript.",
  "/edition/status": "How finished this manuscript is.",
  "/series/name": "Only if the book belongs to a series.",
  "/series/position": "For example 2 or \"Book Two\".",
  "/series/relationship": "Standalone, could become a series, or already part of one.",
  "/genres": "Add each genre and press Enter.",
  "/keywords": "Themes, settings, and subjects; press Enter after each.",
  "/description": "Two to four sentences, as for a back cover.",
  "/original_language": "Only if this manuscript is a translation, e.g. zh.",
};

function valueAt(metadata: Record<string, unknown>, field: string): unknown {
  return field.split("/").filter(Boolean).reduce<unknown>((value, key) =>
    value && typeof value === "object" ? (value as Record<string, unknown>)[key] : undefined, metadata);
}

function empty(value: unknown) {
  return value === null || value === undefined || value === "" || (Array.isArray(value) && !value.length);
}

function display(field: MetadataField, value: unknown): string {
  if (empty(value)) return "—";
  if (field.kind === "people") return (value as Person[]).map((p) => p.roles.length ? `${p.name} (${p.roles.join(", ")})` : p.name).join("; ");
  if (field.kind === "list") return (value as string[]).join(", ");
  if (field.kind === "enum") return String(value).replaceAll("_", " ");
  if (field.kind === "extent") {
    const extent = value as { word_count: number | null; non_whitespace_character_count: number; unit_count: number };
    return [extent.word_count != null ? `${extent.word_count} words` : null,
      `${extent.non_whitespace_character_count} characters`, `${extent.unit_count} units`].filter(Boolean).join(", ");
  }
  return String(value);
}

export function MetadataTable({ metadata, fields, provenance = {}, locked = [], onSave }: {
  metadata: Record<string, unknown>;
  fields: MetadataField[];
  provenance?: Provenance;
  locked?: string[];
  onSave?: (field: string, value: unknown, reason: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<unknown>(null);
  const [reason, setReason] = useState("User correction");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save(field: MetadataField) {
    const checked = prepare(field, draft);
    if (checked.error) { setError(checked.error); return; }
    setBusy(true);
    setError(null);
    try {
      await onSave!(field.field, checked.value, reason);
      setEditing(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="metadata">
      {GROUPS.map((group) => (
        <div key={group.id} className="metadata-group">
          <h3>{group.title}</h3>
          <p className="muted">{group.note}</p>
          <table className="metadata">
            <tbody>
              {fields.filter((field) => field.group === group.id).map((field) => {
                const value = valueAt(metadata, field.field);
                const note = provenance[field.field];
                const editable = onSave && group.id !== "computed" && !locked.includes(field.field);
                return (
                  <tr key={field.field}>
                    <th>{LABELS[field.field] ?? field.field}</th>
                    <td>
                      {editing === field.field ? (
                        <div>
                          <FieldEditor field={field} value={draft} onChange={setDraft} />
                          {CLUES[field.field] && <div className="muted">{CLUES[field.field]}</div>}
                          <div className="row">
                            <label>Reason for change <input value={reason} onChange={(e) => setReason(e.target.value)} size={24} /></label>
                            <button disabled={busy} onClick={() => void save(field)}>Save</button>
                            <button disabled={busy} onClick={() => setEditing(null)}>Cancel</button>
                          </div>
                          {error && <div className="error">{error}</div>}
                        </div>
                      ) : (
                        <>
                          <span className={empty(value) ? "muted" : ""}>{display(field, value)}</span>
                          {empty(value) && CLUES[field.field] && <div className="muted clue">{CLUES[field.field]}</div>}
                        </>
                      )}
                    </td>
                    <td className="muted">
                      {note ? `${note.origin.replaceAll("_", " ")} · ${note.review_status}${note.confidence ? ` · ${note.confidence} confidence` : ""}${note.evidence?.length ? ` · ${note.evidence.length} quotes` : ""}` : ""}
                    </td>
                    <td>{editable && editing !== field.field && (
                      <button className="link" onClick={() => { setEditing(field.field); setDraft(structuredClone(value ?? null)); setError(null); }}>
                        {empty(value) ? "Add" : "Edit"}
                      </button>)}
                      {onSave && !editable && <span className="muted">locked</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

export function MetadataDifferences({ view, fields }: { view: MetadataView; fields: MetadataField[] }) {
  const differences = view.source_differences ?? [];
  if (!differences.length) return null;
  return <details>
    <summary>Prepared source differs from previously reviewed metadata ({differences.length})</summary>
    <p>Your reviewed values are retained. You can correct them in this editor.</p>
    <ul>{differences.map((difference) => {
      const field = fields.find((item) => item.field === difference.field);
      return field && <li key={difference.field}>
        {LABELS[field.field]}: previous review: {display(field, difference.reviewed_value)};
        {" "}source suggests: {display(field, difference.source_value)}.
      </li>;
    })}</ul>
  </details>;
}
