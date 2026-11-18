import { useState, type ReactNode } from "react";
import { api, type Gate, type InteriorSpec, type JsonSchema, type JsonValue, type RunDetail } from "../api";
import { Markdown } from "./Markdown";
import { FontFallbackChoices, fontChoices, LineSpacingChoices, NumberFormatChoices, numericChoices, TrimChoices, ValueChoices, withTocHeadingDefaults,
  type PaperRanges, type Trim } from "./DesignInputs";

const label = (name: string) => name.replaceAll("_", " ").replaceAll("-", " ");
const internalFields = ["id", "vendor_id", "binding", "vendor_profile_ref"];
const presetLabels: Record<string, string> = {
  "book-title": "Book title", "chapter-name": "Chapter name", author: "Author",
  "page-number": "Page number", "page-x-of-y": "Page X of Y", custom: "Custom template",
};
interface FieldChoices {
  styles: { id: string; role: string }[];
  units: string[];
  sectionDefaults: JsonValue;
  paperRanges?: PaperRanges;
  paper: string | null;
  changeTrim: (trim: Trim) => void;
}

export function InteriorDesignReview({ run, gate, perform }: {
  run: RunDetail; gate: Gate; perform: (op: () => Promise<RunDetail>) => void;
}) {
  const { proposal, sha256, schema } = gate.design_review!;
  const initial: InteriorSpec = {
    edition_brief: proposal.edition_brief, design_system: proposal.design_system,
    role_styles: Object.fromEntries(proposal.text_roles.map((r) => [r.id, r.style_id])),
  };
  const headingSupported = Boolean(schema.properties?.design_system?.properties?.navigation?.properties?.toc_heading);
  const normalizeDesign = (design: JsonValue) => headingSupported ? withTocHeadingDefaults(design) : design;
  const [spec, setSpec] = useState<InteriorSpec>(() => ({ ...initial, design_system: normalizeDesign(initial.design_system) }));
  const [pending, setPending] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState("");
  const dirty = JSON.stringify(spec) !== JSON.stringify(initial);
  const blocking = proposal.questions.filter((q) => q.blocking);
  const styles = (spec.design_system as { styles: { id: string; role: string }[] }).styles;
  const choices: FieldChoices = {
    styles, units: proposal.basis.preparation.units.map((unit) => unit.chapter_id),
    sectionDefaults: (spec.design_system as { furniture: { default_section: JsonValue } }).furniture.default_section,
    paperRanges: proposal.vendor_profile?.data.variant.custom_trim_ranges_in,
    paper: ((spec.edition_brief as { production_targets: { paper: string | null }[] }).production_targets[0]?.paper) ?? null,
    changeTrim: (trim) => setSpec((previous) => {
      const brief = previous.edition_brief as { production_targets: Record<string, JsonValue>[] };
      const design = previous.design_system as { page: Record<string, JsonValue> };
      return { ...previous,
        edition_brief: { ...brief, production_targets: brief.production_targets.map((target) => ({ ...target, trim_mm: trim })) },
        design_system: { ...design, page: { ...design.page, trim_mm: trim } },
      };
    }),
  };
  const { purpose, ...briefFields } = spec.edition_brief as Record<string, JsonValue>;

  function submit(action: "save" | "generate" | "request-revision") {
    setPending(true);
    perform(async () => {
      try {
        return await api.reviewInteriorDesign(run.id, {
          gate_id: gate.id, expected_sha256: sha256, action,
          ...(action === "save" ? { spec } : {}),
          ...(action === "generate" ? { answers } : {}),
          ...(action === "request-revision" ? { feedback } : {}),
        });
      } finally { setPending(false); }
    });
  }

  return <div className="interior-review">
    <p>{gate.message}</p>
    <p className="muted">Specification revision {proposal.revision}. Geometry is in millimeters (inches);
      type and paragraph spacing are in points. The gutter is additional to the inside margin.</p>
    <div className="banner warn">Generate a draft in one action. Studio records the exact plan without another approval step.
      Download and inspect the DOCX before approving the design and document together.
      Print-ready describes edition intent, not certified output. PDF generation, rendered-page review,
      font verification and print certification are not available. A vendor profile does not establish compliance.</div>
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
        root={schema} choices={choices} onChange={(edition_brief) => setSpec({
          ...spec, edition_brief: { ...edition_brief as Record<string, JsonValue>, purpose },
        })} />
      <SchemaFields name="Design system" value={spec.design_system} schema={schema.properties?.design_system ?? {}}
        root={schema} choices={choices} onChange={(design_system) => setSpec({ ...spec, design_system: normalizeDesign(design_system) })} />
      <details>
        <summary>Source-bound openings ({proposal.opening_structure?.length ?? 0})</summary>
        {(proposal.opening_structure ?? []).map((opening) => <div key={opening.id}>
          <strong>{label(opening.kind)}: {opening.sources.flatMap((source) =>
            source.components.filter((part) => part.kind === "title").map((part) => part.text)).join(" ")
            || (opening.number === null ? label(opening.id) : `Number ${opening.number}`)}</strong>
          <p className="muted">{opening.chapter_ids.length} bound {opening.kind === "part" ? "chapters" : "unit"}.
            Numbering comes from source evidence, not unit order.</p>
        </div>)}
        <p className="muted">Layout settings change the edition, not these source bindings or manuscript text.
          Request an agent revision to correct structural classification or heading components.</p>
      </details>
      <p className="muted">Choose a header/footer content preset, None, or a custom template. Custom templates accept {"{work_title}"}, {"{chapter_title}"}, {"{author}"},
        {" {page}"} and {"{page_count}"}. Page fields are not calculated in this POC.
        An empty, unlinked part is blank; a linked part inherits and must have no local paragraphs.
        Even/first variants need their corresponding different-page option enabled.
        Section overrides replace all furniture settings for the selected unit.</p>
      <p className="muted">For DOCX, widow/orphan values are switches, not exact line counts:
        both zero turns protection off; either nonzero turns the combined protection on.</p>
      <details open>
        <summary>Paragraph roles</summary>
        {proposal.text_roles.map((role) => <div key={role.id} className="design-field">
          <label>{role.name}: style
            <select aria-label={`${role.name} style`} value={spec.role_styles[role.id] ?? ""}
              onChange={(e) => setSpec({ ...spec, role_styles: { ...spec.role_styles, [role.id]: e.target.value } })}>
              {styles.map((style) => <option key={style.id} value={style.id}>{label(style.id)}</option>)}
            </select>
          </label>
          <p className="muted">{role.function} ({role.occurrences.length} bound paragraphs)</p>
        </div>)}
        <p className="muted">Scope and literary classification stay bound to the manuscript. This form edits their style
          mapping, not the text or paragraph boundaries. Inline formatting comes from the original Markdown markers.</p>
      </details>
    </fieldset>
    <div className="controls">
      <button disabled={pending || !dirty} onClick={() => submit("save")}>Save specification changes</button>
      {dirty && <span className="muted">Save changes before preparing a draft or requesting an agent revision.</span>}
    </div>
    {!!proposal.questions.length && <>
    <h3>Author/design questions</h3>
    <p className="muted">Respond to the required author decisions before generating a draft.
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
      onClick={() => submit("generate")}>Generate draft DOCX</button>
    <h3>Ask the agent to revise</h3>
    <textarea aria-label="Interior design revision request" rows={3} value={feedback} disabled={pending}
      onChange={(e) => setFeedback(e.target.value)} />
    <button disabled={pending || dirty || !feedback.trim()} onClick={() => submit("request-revision")}>Request design revision</button>
  </div>;
}

function SchemaFields({ name, value, schema, root, onChange, choices, geometry = false, furnitureKind, styleEditors }: {
  name: string; value: JsonValue; schema: JsonSchema; root: JsonSchema; onChange: (v: JsonValue) => void;
  choices: FieldChoices; geometry?: boolean; furnitureKind?: string; styleEditors?: ReactNode;
}) {
  if (internalFields.includes(name)) return null;
  const mm = geometry || name.endsWith("_mm");
  const definition = schema.$ref?.split("/").at(-1);
  if (schema.$ref) {
    const key = schema.$ref.split("/").at(-1)!;
    schema = root.$defs?.[key] ?? {};
  }
  const types = Array.isArray(schema.type) ? schema.type : [schema.type];
  const kind = name === "headers" || name === "footers" ? name : furnitureKind;
  const context = { choices, furnitureKind: kind };
  if (name === "separator") return <ValueChoices name="Combined separator" value={value as string} schema={schema}
    options={[{ value: ". ", label: "Period" }, { value: ": ", label: "Colon" },
      { value: " - ", label: "Dash" }, { value: " ", label: "Space" }]} onChange={onChange} />;
  if (name === "ornament_text") return <ValueChoices name="Opening ornament" value={value as string | null} schema={schema}
    options={[{ value: null, label: "None" }, { value: "* * *", label: "Spaced asterisks" },
      { value: "***", label: "Three asterisks" }, { value: "~", label: "Tilde" }]}
    hint="Text/glyphs only. Independent of scene breaks; font glyph coverage is not verified." onChange={onChange} />;
  if (name === "offset_mm") return <ValueChoices name="Opening offset (mm)" value={value as number} schema={schema} numeric
    options={[0, 10, 20, 30, 40, 50].map((n) => ({ value: n, label: `${n} mm` }))} onChange={onChange} />;
  if (name === "trim_mm") return <TrimChoices value={value as Trim | null} ranges={choices.paperRanges}
    paper={choices.paper} onChange={choices.changeTrim} />;
  if (name === "paper") return <ValueChoices name="Paper stock" value={value as string | null} schema={schema}
    options={Object.keys(choices.paperRanges ?? {}).map((paper) => ({
      value: paper, label: ({ white: "White", creme: "Cream", groundwood: "Groundwood" } as Record<string, string>)[paper] ?? label(paper),
    }))} onChange={onChange} hint="Choose from the pinned vendor profile, or leave unselected. Profile entries are not confirmed product availability." />;
  if (name === "family") return <ValueChoices name="family" value={value as string} options={fontChoices}
    onChange={onChange} hint="Suggested families; availability, licensing and glyph coverage are not verified." />;
  if (name === "fallback_families") return <FontFallbackChoices value={value as string[]} onChange={onChange} />;
  if (name === "line_spacing") return <LineSpacingChoices value={value as { mode: string; value: number }} onChange={onChange} />;
  if (name === "color") return <ValueChoices name="color" value={value as string} schema={schema}
    options={[{ value: "#000000", label: "Black" }, { value: "#333333", label: "Dark gray" }]} onChange={onChange} />;
  const numbers = numericChoices(name, mm, schema);
  if (numbers.length && (typeof value === "number" || types.includes("number") || types.includes("integer"))) {
    return <div className="design-node">
      <ValueChoices name={label(name)} value={value as number | null} options={numbers} schema={schema} numeric onChange={onChange}
        hint={name === "bleed_mm" ? "The current editable-DOCX producer supports zero bleed only." : undefined} />
      {mm && typeof value === "number" && <span className="muted" aria-label={`${label(name)} in inches`}>
        ({new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 }).format(value / 25.4)} in)
      </span>}
    </div>;
  }
  const templates = root.$defs?.furniture_content?.["x-preset-templates"] ?? {};
  if (definition === "furniture_content" && value && typeof value === "object" && !Array.isArray(value)) {
    const preset = String(value.preset);
    return <div className="design-field">
      <label>Content preset
        <select aria-label="Content preset" value={preset} onChange={(e) => {
          const next = e.target.value;
          onChange(next === "custom"
            ? { preset: next, template: templates[preset] ?? String(value.template ?? "Custom text") }
            : { preset: next });
        }}>
          {[...Object.keys(templates), "custom"].map((p) => <option key={p} value={p}>{presetLabels[p] ?? label(p)}</option>)}
        </select>
      </label>
      {preset === "custom" ? <label>Custom template
        <input aria-label="Custom template" value={String(value.template ?? "")}
          onChange={(e) => onChange({ preset: "custom", template: e.target.value })} />
      </label> : <span className="muted">Template: {templates[preset]}</span>}
    </div>;
  }
  if (name === "style_id" || name.endsWith("_style_id") || name === "chapter_id") {
    const isStyle = name !== "chapter_id";
    const title = isStyle ? name === "style_id" ? "Style" : label(name.replace("_id", "")) : "Section for prepared unit";
    const options = isStyle ? choices.styles.map((style) => style.id) : choices.units;
    return <label className="design-field">{title}
      <select aria-label={title}
        value={value === null ? "" : String(value)} onChange={(e) => onChange(e.target.value || null)}>
        {name === "opening_body_style_id" && <option value="">Normal body treatment</option>}
        {options.map((option, i) => <option key={option} value={option}>
          {name === "chapter_id" ? `${i + 1}: ${label(option)}` : label(option)}
        </option>)}
      </select>
    </label>;
  }
  if (schema.enum || schema.const !== undefined) {
    const options = schema.enum ?? [schema.const!];
    return <label className="design-field">{label(name)}
      <select aria-label={label(name)} value={JSON.stringify(value)} onChange={(e) => onChange(JSON.parse(e.target.value) as JsonValue)}>
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
    const editable = name === "paragraphs" || name === "section_overrides";
    const unusedUnit = choices.units.find((id) => !value.some((v) => v && typeof v === "object"
      && !Array.isArray(v) && v.chapter_id === id));
    function addItem() {
      if (name === "section_overrides" && unusedUnit) {
        onChange([...value as JsonValue[], { chapter_id: unusedUnit, settings: structuredClone(choices.sectionDefaults) }]);
      } else if (name === "paragraphs") {
        const role = kind === "headers" ? "header" : "footer";
        const style = choices.styles.find((s) => s.role === role) ?? choices.styles[0];
        onChange([...value as JsonValue[], {
          style_id: style.id, alignment: role === "header" ? "left" : "center",
          content: { preset: role === "header" ? "book-title" : "page-number" },
        }]);
      }
    }
    field = <details><summary>{label(name)} ({value.length})</summary>
      {value.map((v, i) => <div key={i}><SchemaFields
        name={name === "production_targets" ? `Output ${i + 1}`
          : v && typeof v === "object" && !Array.isArray(v) && typeof v.id === "string" ? v.id : String(i + 1)}
        value={v} schema={schema.items ?? {}} root={root} geometry={mm} {...context}
        onChange={(next) => onChange(value.map((old, index) => index === i ? next : old))} />
        {editable && <button type="button" onClick={() => onChange(value.filter((_, index) => index !== i))}>
          Remove {name === "paragraphs" ? "paragraph" : "section override"}
        </button>}</div>)}
      {editable && <button type="button" disabled={name === "section_overrides" && !unusedUnit} onClick={addItem}>
        Add {name === "paragraphs" ? `${kind === "headers" ? "header" : "footer"} paragraph` : "section override"}
      </button>}
    </details>;
  } else if (typeof value === "object") {
    let presetControl;
    const objectValue = value;
    const designSystem = name === "Design system";
    const styleEntries = (designSystem ? value.styles as Record<string, JsonValue>[] : []).map((style, index) => ({ style, index }));
    const chapterSettings = value.chapter_openings as Record<string, JsonValue> | undefined;
    const partSettings = (value.part_openings as Record<string, JsonValue> | undefined)?.heading as Record<string, JsonValue> | undefined;
    const references = (settings?: Record<string, JsonValue>) => new Set(Object.entries(settings ?? {})
      .filter(([key]) => key.endsWith("_style_id")).map(([, id]) => id));
    const chapterRefs = references(chapterSettings), partRefs = references(partSettings);
    const navigationRefs = references(value.navigation as Record<string, JsonValue> | undefined);
    function styleGroup(style: Record<string, JsonValue>) {
      const role = String(style.role);
      if (role.startsWith("chapter-") || role === "opening-body") return "chapter";
      if (role.startsWith("part-")) return "part";
      if (role === "heading" || role === "special") {
        if (chapterRefs.has(style.id)) return "chapter";
        if (partRefs.has(style.id)) return "part";
      }
      if (navigationRefs.has(style.id)) return "navigation";
      return "text";
    }
    function renderStyles(group: string) {
      return styleEntries.filter(({ style }) => styleGroup(style) === group).map(({ style, index }) =>
        <SchemaFields key={String(style.id)} name={String(style.id)} value={style}
          schema={schema.properties?.styles?.items ?? {}} root={root} {...context}
          onChange={(next) => onChange({ ...objectValue, styles: (objectValue.styles as JsonValue[]).map((old, i) => i === index ? next : old) })} />);
    }
    const layout = String(value.layout);
    if (designSystem && schema.properties?.page?.properties?.section_start) {
      const page = value.page as Record<string, JsonValue>;
      const navigation = value.navigation as Record<string, JsonValue>;
      const starts = [page.section_start ?? "new-page", chapterSettings?.start, partSettings?.start,
        navigation.toc_start ?? "new-page"];
      const selected = starts.every((start) => start === "recto") ? "recto"
        : starts.every((start) => start === "new-page") ? "new-page" : "custom";
      presetControl = <label className="design-field">Section starts
        <select aria-label="Section starts" value={selected} onChange={(event) => {
          const start = event.target.value;
          if (start === "custom") return;
          const parts = value.part_openings as Record<string, JsonValue>;
          onChange({ ...value, page: { ...page, section_start: start,
            ...(start === "recto" ? { blank_policy: "allow-declared-recto-blanks" } : {}) },
            chapter_openings: { ...chapterSettings, start }, part_openings: { ...parts, heading: { ...partSettings, start } },
            navigation: { ...navigation, toc_start: start } });
        }}>
          <option value="custom">Mixed / per-section settings</option>
          <option value="recto">Recto for every section (right-hand page)</option>
          <option value="new-page">New page for every section</option>
        </select>
        <span className="muted">Applies to chapters, parts, TOC and front/back matter.
          Recto permits the blank pages needed for right-hand starts; Word calculates them.</span>
      </label>;
    }
    if (name === "page" && schema.properties?.section_start) {
      presetControl = <label className="design-field">Other section starts
        <select aria-label="Other section starts" value={String(value.section_start ?? "new-page")}
          onChange={(event) => onChange({ ...value, section_start: event.target.value,
            ...(event.target.value === "recto" ? { blank_policy: "allow-declared-recto-blanks" } : {}) })}>
          <option value="new-page">New page</option><option value="recto">Recto (right-hand page)</option>
        </select>
        <span className="muted">Front/back matter; chapters, parts and TOC have their own controls.</span>
      </label>;
    }
    if (name === "navigation") {
      presetControl = <>
        <label className="design-field"><input type="checkbox" checked={Boolean(value.include_toc)}
          aria-label="Include table of contents" onChange={(event) => onChange({ ...value,
            include_toc: event.target.checked, toc_depth: event.target.checked ? Number(value.toc_depth) || 1 : 0,
          })} /> Include table of contents</label>
        {Boolean(value.include_toc) && <>
          {schema.properties?.toc_heading && <>
            <label className="design-field">TOC heading
              <input aria-label="TOC heading" type="text" maxLength={200} value={String(value.toc_heading ?? "Contents")}
                onChange={(event) => onChange({ ...value, toc_heading: event.target.value })} />
            </label>
            <label className="design-field">TOC heading style
              <select aria-label="TOC heading style" value={String(value.toc_heading_style_id ?? "")}
                onChange={(event) => onChange({ ...value, toc_heading_style_id: event.target.value || null })}>
                <option value="">TOC heading (default)</option>
                {choices.styles.map((style) => <option key={style.id} value={style.id}>{label(style.id)}</option>)}
              </select>
            </label>
          </>}
          <label className="design-field">TOC depth
            <select aria-label="TOC depth" value={Number(value.toc_depth)}
              onChange={(event) => onChange({ ...value, toc_depth: Number(event.target.value) })}>
              {[1, 2, 3, 4, 5, 6].map((depth) => <option key={depth} value={depth}>{depth} heading level{depth > 1 ? "s" : ""}</option>)}
            </select>
          </label>
          {schema.properties?.toc_start && <label className="design-field">TOC start
            <select aria-label="TOC start" value={String(value.toc_start ?? "new-page")}
              onChange={(event) => onChange({ ...value, toc_start: event.target.value })}>
              <option value="new-page">New page</option><option value="recto">Recto (right-hand page)</option>
            </select>
          </label>}
          {schema.properties?.toc_before_chapter_id && <label className="design-field">TOC location
            <select aria-label="TOC location" value={String(value.toc_before_chapter_id ?? "")}
              onChange={(event) => onChange({ ...value, toc_before_chapter_id: event.target.value || null })}>
              <option value="">Automatic: before the first part/chapter</option>
              {choices.units.slice(1).map((id) => <option key={id} value={id}>Before {id}</option>)}
            </select>
          </label>}
          {schema.properties?.toc_style_id && <label className="design-field">TOC entry style
            <select aria-label="TOC entry style" value={String(value.toc_style_id ?? "")}
              onChange={(event) => onChange({ ...value, toc_style_id: event.target.value || null })}>
              <option value="">Body style (default)</option>
              {choices.styles.map((style) => <option key={style.id} value={style.id}>{label(style.id)}</option>)}
            </select>
          </label>}
          <p className="muted">Inserts a Word TOC field in its own section with a visible update prompt, using body heading levels and
            excluding front matter. By default it precedes the first part/chapter and uses Body typography.
            TOC styles use 12 pt level indents and dotted page-number tabs. In Word, right-click the TOC and
            choose Update Field / Update entire table (or select all and press F9). Entries and page numbers
            are not calculated or verified here. The plain-text heading defaults to Contents, has its own named
            style and stays outside TOC entries.</p>
          <details>
            <summary>TOC styles</summary>
            <p className="muted">Edit the heading and entry styles here. Shared chapter/part styles keep their single
              editor under the opening section. The default heading is centered, 18 pt bold, using the Body font.
              The heading starts the TOC page and is always kept with the field.</p>
            {styleEditors}
          </details>
        </>}
      </>;
    }
    const openingHidden = new Set<string>();
    if (definition === "opening_settings") {
      openingHidden.add("number_case");
      openingHidden.add("number_template");
      if (layout !== "combined") openingHidden.add("separator");
      if (layout === "preserve-source") openingHidden.add("number_format");
      if (layout === "combined") {
        openingHidden.add("number_style_id");
        openingHidden.add("title_style_id");
      } else if (layout !== "preserve-source") {
        openingHidden.add("combined_style_id");
        if (layout === "title-only") openingHidden.add("number_style_id");
      }
    }
    if (definition === "furniture_part" && Object.keys(templates).length) {
      const paragraphs = value.paragraphs as Record<string, JsonValue>[];
      const first = paragraphs[0];
      const content = first?.content as Record<string, JsonValue> | undefined;
      const selected = value.link_to_previous ? "linked" : !paragraphs.length ? "none"
        : paragraphs.length > 1 ? "multiple" : String(content?.preset);
      const role = kind === "headers" ? "header" : "footer";
      presetControl = <label className="design-field">{role === "header" ? "Header content" : "Footer content"}
        <select aria-label={role === "header" ? "Header content" : "Footer content"} value={selected}
          onChange={(e) => {
            const preset = e.target.value;
            const style = choices.styles.find((s) => s.role === role) ?? choices.styles[0];
            onChange({ ...value, link_to_previous: false, paragraphs: preset === "none" ? [] : [{
              style_id: first?.style_id ?? style.id,
              alignment: first?.alignment ?? (role === "header" ? "left" : "center"),
              content: preset === "custom" ? { preset, template: templates[String(content?.preset)]
                ?? String(content?.template ?? `Custom ${role}`) } : { preset },
            }] });
          }}>
          <option value="none">None (blank and unlinked)</option>
          {Object.keys(templates).map((p) => <option key={p} value={p}>{presetLabels[p] ?? label(p)}</option>)}
          <option value="custom">Custom template</option>
          {selected === "linked" && <option value="linked" disabled>Linked to previous section</option>}
          {selected === "multiple" && <option value="multiple" disabled>Multiple paragraphs (edit below)</option>}
        </select>
      </label>;
    }
    const fields = Object.entries(value).filter(([key]) =>
      (key !== "trim_mm" || name === "page") && !openingHidden.has(key)
      && (name !== "page" || key !== "section_start")
      && (name !== "navigation" || !["include_toc", "toc_depth", "toc_before_chapter_id", "toc_style_id",
        "toc_heading", "toc_heading_style_id", "toc_start"].includes(key)));
    const renderField = ([key, v]: [string, JsonValue]) => definition === "opening_settings" && key === "number_format"
      ? <NumberFormatChoices key={key} format={String(value.number_format)} letterCase={String(value.number_case)}
        numberTemplate={String(value.number_template)} kind={name === "chapter_openings" ? "Chapter" : "Part"}
        onTemplateChange={(number_template) => onChange({ ...value, number_template })}
        onChange={(next) => onChange({ ...value, ...next })} />
      : <SchemaFields key={key} name={key} value={v}
      schema={definition === "opening_settings" && (key === "ornament_position" && layout !== "separated"
        || key === "start" && name === "heading")
        ? { ...schema.properties?.[key], enum: schema.properties?.[key]?.enum?.filter((option) =>
          option !== (key === "start" ? "continuous" : "between")) }
        : schema.properties?.[key] ?? {}}
      styleEditors={designSystem && key === "chapter_openings" ? renderStyles("chapter")
        : designSystem && key === "part_openings" ? renderStyles("part")
        : designSystem && key === "navigation" ? renderStyles("navigation")
        : name === "part_openings" && key === "heading" ? styleEditors : undefined}
      root={root} geometry={mm} {...context} onChange={(next) => onChange({ ...value, [key]: next,
        ...(designSystem && key === "navigation" && (next as Record<string, JsonValue>).toc_start === "recto"
          ? { page: { ...value.page as Record<string, JsonValue>, blank_policy: "allow-declared-recto-blanks" } } : {}),
        ...(key === "layout" && next !== "separated" && value.ornament_position === "between"
          ? { ornament_position: "below" } : {}),
        ...(key === "layout" && next === "preserve-source" ? { number_format: "source" } : {}),
      })} />;
    field = <details open={name === "Design system" || name === "Edition brief" || name === "page"
      || name === "chapter_openings" || name === "part_openings" || definition === "opening_settings"}>
      <summary>{name === "chapter_openings" ? "Chapter openings" : name === "part_openings" ? "Part openings" : label(name)}</summary>
      {presetControl}
      {definition === "opening_settings" && <p className="muted">
        Combined uses one shared number/title paragraph style; separated uses independent styles.
        Title-only requires a source title. Unnumbered openings stay unnumbered.
        Recto starts require the permitted-blank policy under Page.
        Spacing/alignment live in the named styles; the offset adds space before the opening block.
        Shared-page parts own the block start/offset and use chapter-page furniture.
      </p>}
      {fields.filter(([key]) => definition !== "opening_settings" || !key.endsWith("_style_id")).map((entry) =>
        designSystem && entry[0] === "styles" ? <details key="styles">
          <summary>Text styles ({styleEntries.filter(({ style }) => styleGroup(style) === "text").length})</summary>
          {renderStyles("text")}
        </details> : renderField(entry))}
      {definition === "opening_settings" && <details>
        <summary>{name === "chapter_openings" ? "Chapter styles" : "Part styles"}</summary>
        {fields.filter(([key]) => key.endsWith("_style_id")).map(renderField)}
        <p className="muted">Edit the named styles below. Shared styles have one editor, under their owning opening section
          or Text styles; selecting a style here does not create a copy.</p>
        {styleEditors}
      </details>}
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
