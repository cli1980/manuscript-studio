import { useState } from "react";
import { api, type Gate, type InteriorSpec, type JsonSchema, type JsonValue, type RunDetail } from "../api";
import { Markdown } from "./Markdown";

const label = (name: string) => name.replaceAll("_", " ").replaceAll("-", " ");
const internalFields = ["id", "vendor_id", "binding", "vendor_profile_ref"];

export function InteriorDesignReview({ run, gate, perform }: {
  run: RunDetail; gate: Gate; perform: (op: () => Promise<RunDetail>) => void;
}) {
  const { proposal, sha256, schema } = gate.design_review!;
  const initial: InteriorSpec = {
    edition_brief: proposal.edition_brief, design_system: proposal.design_system,
    role_styles: Object.fromEntries(proposal.text_roles.map((r) => [r.id, r.style_id])),
  };
  const [spec, setSpec] = useState<InteriorSpec>(initial);
  const [pending, setPending] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState("");
  const dirty = JSON.stringify(spec) !== JSON.stringify(initial);
  const blocking = proposal.questions.filter((q) => q.blocking);
  const styles = (spec.design_system as { styles: { id: string }[] }).styles;
  const { purpose, ...briefFields } = spec.edition_brief as Record<string, JsonValue>;

  function submit(action: "save" | "approve" | "request-revision") {
    setPending(true);
    perform(async () => {
      try {
        return await api.reviewInteriorDesign(run.id, {
          gate_id: gate.id, expected_sha256: sha256, action,
          ...(action === "save" ? { spec } : {}),
          ...(action === "approve" ? { answers } : {}),
          ...(action === "request-revision" ? { feedback } : {}),
        });
      } finally { setPending(false); }
    });
  }

  return <div className="interior-review">
    <p>{gate.message}</p>
    <p className="muted">Specification revision {proposal.revision}. Geometry is in millimeters (inches);
      type and paragraph spacing are in points. The gutter is additional to the inside margin.</p>
    <div className="banner warn">Design review only. A selected vendor profile informs the proposal, not compliance.
      Deterministic production and rendered-page review are not connected yet. Approval stops before production.</div>
    <p>Print vendor: {proposal.vendor_profile
      ? `${proposal.vendor_profile.data.name} / ${proposal.vendor_profile.data.variant.name}`
      : "No vendor profile"}</p>
    {!!gate.design_review!.vendor_warnings.length && <div className="banner warn">
      <strong>Profile checks requiring attention</strong>
      <ul>{gate.design_review!.vendor_warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
    </div>}
    <p className="muted">Purpose, vendor and binding are fixed from formatting entry.
      Reopen manuscript approval to choose a different target before authoring a new proposal.</p>
    <details>
      <summary>Literary reading and design rationale</summary>
      <p>{proposal.reading.essence}</p>
      <p>{proposal.reading.genres.join(" / ")}; {proposal.reading.mood.join(", ")}</p>
      <Markdown text={proposal.reading.synopsis} />
      {proposal.recommendations.map((r) => <div key={r.id}>
        <p>{r.rationale}</p>
        {!!r.alternatives.length && <ul>{r.alternatives.map((s) => <li key={s}>{s}</li>)}</ul>}
      </div>)}
      <p className="muted">These are the agent's original recommendations; your edited values below take precedence.</p>
    </details>
    <fieldset disabled={pending}>
      <legend>Editable specification</legend>
      <p>Proposal purpose: {purpose === "print-ready" ? "Print-ready" : label(String(purpose))}.
        This is read-only.</p>
      <SchemaFields name="Edition brief" value={briefFields} schema={schema.properties?.edition_brief ?? {}}
        root={schema} onChange={(edition_brief) => setSpec({
          ...spec, edition_brief: { ...edition_brief as Record<string, JsonValue>, purpose },
        })} />
      <SchemaFields name="Design system" value={spec.design_system} schema={schema.properties?.design_system ?? {}}
        root={schema} onChange={(design_system) => setSpec({ ...spec, design_system })} />
      <details open>
        <summary>Special text roles</summary>
        {proposal.text_roles.map((role) => <div key={role.id} className="design-field">
          <label>{role.name}: style
            <select aria-label={`${role.name} style`} value={spec.role_styles[role.id] ?? ""}
              onChange={(e) => setSpec({ ...spec, role_styles: { ...spec.role_styles, [role.id]: e.target.value } })}>
              {styles.map((style) => <option key={style.id} value={style.id}>{label(style.id)}</option>)}
            </select>
          </label>
          <p className="muted">{role.function} ({role.occurrences.length} bound occurrences)</p>
        </div>)}
        <p className="muted">Scope and literary classification stay bound to the manuscript. This form edits their style
          mapping, not the text or occurrence boundaries.</p>
      </details>
    </fieldset>
    <div className="controls">
      <button disabled={pending || !dirty} onClick={() => submit("save")}>Save specification changes</button>
      {dirty && <span className="muted">Save changes before approval or requesting an agent revision.</span>}
    </div>
    {!!proposal.questions.length && <>
    <h3>Author/design questions</h3>
    <p className="muted">Respond to the required author decisions before approval.
      Request a design revision if your answer calls for a change to the specification.</p>
    {proposal.questions.map((q) => <div className="design-field" key={q.id}>
      <label>{q.question} <span className="tag">{q.blocking ? "required" : "optional"}</span>
        {q.blocking && <textarea rows={2} disabled={pending} value={answers[q.id] ?? ""}
          onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })} />}
      </label>
      {!!q.options.length && <p className="muted">Options: {q.options.join(" / ")}</p>}
    </div>)}
    </>}
    <button className="primary" disabled={pending || dirty || blocking.some((q) => !answers[q.id]?.trim())}
      onClick={() => submit("approve")}>Approve this design specification</button>
    <h3>Ask the agent to revise</h3>
    <textarea aria-label="Interior design revision request" rows={3} value={feedback} disabled={pending}
      onChange={(e) => setFeedback(e.target.value)} />
    <button disabled={pending || dirty || !feedback.trim()} onClick={() => submit("request-revision")}>Request design revision</button>
  </div>;
}

function SchemaFields({ name, value, schema, root, onChange, geometry = false }: {
  name: string; value: JsonValue; schema: JsonSchema; root: JsonSchema; onChange: (v: JsonValue) => void;
  geometry?: boolean;
}) {
  if (internalFields.includes(name)) return null;
  const mm = geometry || name.endsWith("_mm");
  if (schema.$ref) {
    const key = schema.$ref.split("/").at(-1)!;
    schema = root.$defs?.[key] ?? {};
  }
  const types = Array.isArray(schema.type) ? schema.type : [schema.type];
  if (schema.enum || schema.const !== undefined) {
    const options = schema.enum ?? [schema.const!];
    return <label className="design-field">{label(name)}
      <select value={JSON.stringify(value)} onChange={(e) => onChange(JSON.parse(e.target.value) as JsonValue)}>
          {options.map((o) => <option key={JSON.stringify(o)} value={JSON.stringify(o)}>{o === null ? "Not set" : label(String(o))}</option>)}
      </select>
    </label>;
  }
  if (value === null) {
    const type = types.find((t) => t !== "null");
    return <div className="design-field">{label(name)}: not set
      <button type="button" onClick={() => onChange(type === "number" || type === "integer" ? 0
        : type === "object" ? {} : type === "array" ? [] : "")}>Set value</button>
    </div>;
  }
  let field;
  if (Array.isArray(value)) {
    field = <details><summary>{label(name)} ({value.length})</summary>
      {value.map((v, i) => <SchemaFields key={i}
        name={name === "production_targets" ? `Output ${i + 1}`
          : v && typeof v === "object" && !Array.isArray(v) && typeof v.id === "string" ? v.id : String(i + 1)}
        value={v} schema={schema.items ?? {}} root={root} geometry={mm}
        onChange={(next) => onChange(value.map((old, index) => index === i ? next : old))} />)}
    </details>;
  } else if (typeof value === "object") {
    field = <details open={name === "Design system" || name === "Edition brief" || name === "page"}>
      <summary>{label(name)}</summary>
      {Object.entries(value).map(([key, v]) => <SchemaFields key={key} name={key} value={v} schema={schema.properties?.[key] ?? {}}
        root={root} geometry={mm} onChange={(next) => onChange({ ...value, [key]: next })} />)}
    </details>;
  } else if (typeof value === "boolean") {
    field = <label className="design-field"><input type="checkbox" checked={value}
      onChange={(e) => onChange(e.target.checked)} /> {label(name)}</label>;
  } else {
    field = <label className="design-field">{label(name)}
      <input aria-label={label(name)} type={typeof value === "number" ? "number" : "text"} step="any" value={value}
        min={schema.minimum} max={schema.maximum}
        onChange={(e) => onChange(typeof value === "number" ? Number(e.target.value) : e.target.value)} />
      {mm && typeof value === "number" && <span className="muted" aria-label={`${label(name)} in inches`}>
        ({new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 }).format(value / 25.4)} in)
      </span>}
    </label>;
  }
  return <div className="design-node">{field}
    {types.includes("null") && <button className="link" type="button" onClick={() => onChange(null)}>Clear {label(name)}</button>}
  </div>;
}
