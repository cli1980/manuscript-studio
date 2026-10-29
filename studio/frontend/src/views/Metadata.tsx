import { useState } from "react";
import type { MetadataField } from "../api";
import { FieldEditor, prepare, type Person } from "./widgets";

type Provenance = Record<string, { origin: string; review_status: string; confidence: string | null; evidence?: unknown[] }>;

const GROUPS: { id: MetadataField["group"]; title: string; note: string }[] = [
  { id: "author", title: "Provided by you", note: "Only you know these. They start empty when the manuscript is added; agents never fill them." },
  { id: "suggested", title: "Suggested from the manuscript", note: "Agents propose these with evidence during preparation. Confirm or correct them." },
  { id: "computed", title: "Computed", note: "Fixed when the work was added or measured from the prepared manuscript." },
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
  const [reason, setReason] = useState("Author input");
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
                            <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason" size={24} />
                            <button disabled={busy} onClick={() => void save(field)}>Save</button>
                            <button disabled={busy} onClick={() => setEditing(null)}>Cancel</button>
                          </div>
                          {error && <div className="error">{error}</div>}
                        </div>
                      ) : (
                        <>
                          <span className={empty(value) ? "muted" : ""}>{display(field, value)}</span>
                          {empty(value) && group.id === "author" && CLUES[field.field] && <div className="muted clue">{CLUES[field.field]}</div>}
                        </>
                      )}
                    </td>
                    <td className="muted">
                      {note ? `${note.origin.replaceAll("_", " ")} · ${note.review_status}${note.confidence ? ` · ${note.confidence} confidence` : ""}${note.evidence?.length ? ` · ${note.evidence.length} quotes` : ""}` : ""}
                    </td>
                    <td>{editable && editing !== field.field && (
                      <button className="link" onClick={() => { setEditing(field.field); setDraft(structuredClone(value ?? null)); setError(null); }}>
                        {empty(value) && group.id === "author" ? "Add" : "Edit"}
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

// Open form for the fields only the user can provide, shown on a work before any workflow has run.
export function AuthorForm({ metadata, fields, onSave, onDone }: {
  metadata: Record<string, unknown>;
  fields: MetadataField[];
  onSave: (field: string, value: unknown, reason: string) => Promise<void>;
  onDone: () => void;
}) {
  const author = fields.filter((field) => field.group === "author");
  const initial = () => Object.fromEntries(author.map((f) => [f.field, structuredClone(valueAt(metadata, f.field) ?? null)]));
  const [values, setValues] = useState<Record<string, unknown>>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const changed = author.filter((f) => JSON.stringify(values[f.field] ?? null) !== JSON.stringify(valueAt(metadata, f.field) ?? null));

  async function save() {
    const problems: Record<string, string> = {};
    const ready = changed.map((field) => {
      const checked = prepare(field, values[field.field]);
      if (checked.error) problems[field.field] = checked.error;
      return { field, value: checked.value };
    });
    setErrors(problems);
    if (Object.keys(problems).length) return;
    setBusy(true);
    try {
      for (const { field, value } of ready) {
        try {
          await onSave(field.field, value, "Provided by the author before starting a workflow");
        } catch (exc) {
          problems[field.field] = exc instanceof Error ? exc.message : String(exc);
        }
      }
      setErrors({ ...problems });
      setSaved(!Object.keys(problems).length);
      onDone();
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel author-form" onSubmit={(e) => { e.preventDefault(); void save(); }}>
      <h2>About this manuscript</h2>
      <p className="muted">Fill in what you know before starting a workflow. Everything is optional and can be changed later;
        agents suggest the remaining fields (genres, description, …) during preparation.</p>
      {author.map((field) => (
        <div key={field.field} className="form-row">
          <label>{LABELS[field.field] ?? field.field}</label>
          <div>
            <FieldEditor field={field} value={values[field.field]} onChange={(v) => { setSaved(false); setValues({ ...values, [field.field]: v }); }} />
            {CLUES[field.field] && <div className="muted clue">{CLUES[field.field]}</div>}
            {errors[field.field] && <div className="error">{errors[field.field]}</div>}
          </div>
        </div>
      ))}
      <button type="submit" disabled={busy || !changed.length}>{busy ? "Saving…" : `Save ${changed.length || ""} change${changed.length === 1 ? "" : "s"}`.replace("  ", " ")}</button>
      {saved && !changed.length && <span className="muted"> Saved.</span>}
    </form>
  );
}
