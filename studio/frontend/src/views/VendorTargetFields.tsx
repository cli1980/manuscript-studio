import type { FormatTarget, VendorProfileOption } from "../api";

export function VendorTargetFields({ profiles, target, onChange, disabled = false }: {
  profiles: VendorProfileOption[]; target: FormatTarget;
  onChange: (target: FormatTarget) => void; disabled?: boolean;
}) {
  const selected = profiles.find((p) => p.id === target.vendor_id)?.variants.find((v) => v.binding === target.binding);
  return <fieldset disabled={disabled}>
    <legend>Formatting target</legend>
    <div className="row">
      <label>Purpose <select aria-label="Purpose" value={target.purpose}
        onChange={(e) => onChange({ ...target, purpose: e.target.value as FormatTarget["purpose"] })}>
        <option value="print-ready">Print-ready</option>
        <option value="submission">Submission</option>
        <option value="editorial-review">Editorial review</option>
      </select></label>
      <label>Binding <select aria-label="Binding" value={target.binding}
        onChange={(e) => onChange({ ...target, binding: e.target.value as FormatTarget["binding"] })}>
        <option value="paperback">Paperback</option><option value="hardcover">Hardcover</option>
      </select></label>
      <label>Print vendor <select aria-label="Print vendor" value={target.vendor_id ?? ""}
        onChange={(e) => onChange({ ...target, vendor_id: e.target.value || null })}>
        <option value="">No vendor profile</option>
        {profiles.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
      </select></label>
    </div>
    <p className="muted">Purpose guides the agent's proposal. Print-ready is the intended use, not verified print compliance.</p>
    {selected && <div className="banner">
      <strong>Loaded profile: {selected.profile.data.name} / {selected.name}</strong>
      <p>The binding variant switches automatically.</p>
      <p>{selected.profile.data.docx_guidance.page_size} Safety recommendation: {selected.profile.data.docx_guidance.recommended_safety_mm} mm.</p>
      <p>{selected.profile.data.docx_guidance.gutter}</p>
      <details><summary>Profile requirements and binding notes</summary>
        <ul>{selected.profile.data.variant.notes.map((note) => <li key={note}>{note}</li>)}</ul>
        <ul>{selected.profile.data.rules.map((rule) => <li key={rule.id}>
          {rule.statement} <span className="muted">({rule.classification.replaceAll("_", " ")}; p. {rule.pages.join(", ")})</span>
        </li>)}</ul>
        <p>Source: {selected.profile.data.source.title}, {selected.profile.data.source.edition}.</p>
      </details>
      <p className="muted">This profile informs the proposal. Product availability and rendered-PDF compliance are not verified.</p>
    </div>}
  </fieldset>;
}
