import { useState } from "react";
import type { MetadataField } from "../api";

export type Person = { id: string; name: string; roles: string[] };

// Typed editors generated from the metadata schema. Each returns a schema-shaped value; `validate` mirrors
// the schema's constraints so most mistakes are caught before the server's authoritative check.

export function TermsEditor({ value, onChange, placeholder }: { value: string[]; onChange: (v: string[]) => void; placeholder?: string }) {
  const [text, setText] = useState("");
  const add = () => {
    const term = text.trim();
    if (term && !value.includes(term)) onChange([...value, term]);
    setText("");
  };
  return (
    <div className="terms">
      {value.map((term) => (
        <span key={term} className="chip">{term}
          <button type="button" aria-label={`Remove ${term}`} onClick={() => onChange(value.filter((t) => t !== term))}>×</button>
        </span>
      ))}
      <input value={text} placeholder={placeholder ?? "Add and press Enter"} onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(); } }} onBlur={add} />
    </div>
  );
}

export function PeopleEditor({ value, roles, onChange }: { value: Person[]; roles: string[]; onChange: (v: Person[]) => void }) {
  const update = (index: number, change: Partial<Person>) => onChange(value.map((p, i) => (i === index ? { ...p, ...change } : p)));
  return (
    <div className="people">
      {value.map((person, index) => (
        <div key={index} className="person">
          <input value={person.name} placeholder="Full name" onChange={(e) => update(index, { name: e.target.value })} />
          {roles.map((role) => (
            <label key={role}>
              <input type="checkbox" checked={person.roles.includes(role)}
                onChange={(e) => update(index, { roles: e.target.checked ? [...person.roles, role] : person.roles.filter((r) => r !== role) })} />
              {" "}{role}
            </label>
          ))}
          <button type="button" className="link" onClick={() => onChange(value.filter((_, i) => i !== index))}>Remove</button>
        </div>
      ))}
      <button type="button" onClick={() => onChange([...value, { id: "", name: "", roles: [roles[0]] }])}>Add person</button>
    </div>
  );
}

const LANGUAGES = ["zh", "zh-CN", "zh-TW", "en", "en-US", "en-GB", "ja", "ko", "fr", "de", "es", "ru"];

export function FieldEditor({ field, value, onChange }: { field: MetadataField; value: unknown; onChange: (v: unknown) => void }) {
  switch (field.kind) {
    case "enum":
      return (
        <select value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value || null)}>
          <option value="">— not set —</option>
          {field.options.map((option) => <option key={option} value={option}>{option.replaceAll("_", " ")}</option>)}
        </select>
      );
    case "list":
      return <TermsEditor value={(value as string[]) ?? []} onChange={onChange} />;
    case "people":
      return <PeopleEditor value={(value as Person[]) ?? []} roles={field.options} onChange={onChange} />;
    case "number":
      return <input type="number" min={field.minimum ?? undefined} step="any" value={value == null ? "" : String(value)}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))} />;
    case "language":
      return (
        <>
          <input list="language-tags" value={(value as string) ?? ""} placeholder="e.g. zh" size={10}
            onChange={(e) => onChange(e.target.value.trim() || null)} />
          <datalist id="language-tags">{LANGUAGES.map((tag) => <option key={tag} value={tag} />)}</datalist>
        </>
      );
    default:
      return field.field === "/description"
        ? <textarea rows={4} value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value || null)} />
        : <input value={(value as string) ?? ""} size={50} onChange={(e) => onChange(e.target.value || null)} />;
  }
}

function slug(name: string, index: number) {
  return name.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || `person-${index + 1}`;
}

// Normalize to the schema shape and return an error message if a constraint is violated.
export function prepare(field: MetadataField, value: unknown): { value: unknown; error: string | null } {
  if (typeof value === "string") value = value.trim() || null;
  if (field.kind === "people") {
    const people = (value as Person[]).map((p) => ({ ...p, name: p.name.trim() }));
    if (people.some((p) => !p.name)) return { value, error: "Every person needs a name." };
    if (people.some((p) => !p.roles.length)) return { value, error: "Every person needs at least one role." };
    const ids = new Set<string>();
    const shaped = people.map((p, i) => {
      let id = p.id || slug(p.name, i);
      while (ids.has(id)) id = `${id}-${i + 1}`;
      ids.add(id);
      return { id, name: p.name, roles: p.roles };
    });
    return { value: shaped, error: null };
  }
  if (field.kind === "language" && value !== null && field.pattern && !new RegExp(field.pattern).test(String(value))) {
    return { value, error: "Use a language tag such as zh, zh-CN, or en-US." };
  }
  if (field.kind === "number" && value !== null && (Number.isNaN(value) || (field.minimum != null && (value as number) < field.minimum))) {
    return { value, error: `Enter a number of at least ${field.minimum ?? 0}.` };
  }
  return { value, error: null };
}
