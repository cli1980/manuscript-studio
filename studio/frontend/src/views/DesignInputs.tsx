import { useState } from "react";
import type { JsonSchema, JsonValue } from "../api";

type Scalar = string | number | null;
type Option = { value: Scalar; label: string };
export type Trim = { width: number; height: number };
export type PaperRanges = Record<string, { width: number[]; height: number[] }>;

export function withTocHeadingDefaults(design: JsonValue): JsonValue {
  const system = design as Record<string, JsonValue>;
  const navigation = system.navigation as Record<string, JsonValue>;
  if (!navigation.include_toc) return design;
  const styles = system.styles as Record<string, JsonValue>[];
  let headingId = navigation.toc_heading_style_id;
  let nextStyles = styles;
  if (headingId == null) {
    const existing = styles.find((style) => style.id === "toc-heading" && style.role === "toc");
    if (existing) headingId = existing.id;
    else {
      headingId = "toc-heading";
      for (let suffix = 2; styles.some((style) => style.id === headingId); suffix++) headingId = `toc-heading-${suffix}`;
      const body = structuredClone(styles.find((style) => style.role === "body")!);
      nextStyles = [...styles, { ...body, id: headingId, role: "toc", heading_level: null,
        font: { ...body.font as Record<string, JsonValue>, size_pt: 18, weight: "bold", italic: false,
          line_spacing: { mode: "multiple", value: 1.2 } },
        paragraph: { ...body.paragraph as Record<string, JsonValue>, model: "block", first_line_indent_mm: 0,
          space_before_pt: 0, space_after_pt: 12, alignment: "center", indent_opening_paragraph: false,
          keep_with_next: true },
      }];
    }
  }
  return { ...system, styles: nextStyles, navigation: { ...navigation,
    toc_heading: navigation.toc_heading ?? "Contents", toc_heading_style_id: headingId } };
}

export const fontChoices = [
  "Garamond", "Georgia", "Baskerville", "Book Antiqua", "Palatino Linotype",
  "Times New Roman", "Noto Serif", "Noto Serif CJK SC", "SimSun", "Noto Sans", "Microsoft YaHei",
].map((value) => ({ value, label: value }));

const numberFormats = [
  { format: "source", letterCase: null, label: "Preserve source label", example: "" },
  { format: "arabic", letterCase: "title", label: "Arabic", example: "4" },
  { format: "roman-upper", letterCase: "title", label: "Roman uppercase", example: "IV" },
  { format: "roman-lower", letterCase: "title", label: "Roman lowercase", example: "iv" },
  { format: "words", letterCase: "lower", label: "Words lowercase", example: "four" },
  { format: "words", letterCase: "title", label: "Words title case", example: "Four" },
  { format: "words", letterCase: "upper", label: "Words uppercase", example: "FOUR" },
  { format: "ordinal-words", letterCase: "lower", label: "Ordinal lowercase", example: "fourth" },
  { format: "ordinal-words", letterCase: "title", label: "Ordinal title case", example: "Fourth" },
  { format: "ordinal-words", letterCase: "upper", label: "Ordinal uppercase", example: "FOURTH" },
];

export function NumberFormatChoices({ format, letterCase, numberTemplate, kind, onChange, onTemplateChange }: {
  format: string; letterCase: string; numberTemplate: string; kind: "Chapter" | "Part";
  onChange: (next: { number_format: string; number_case: string }) => void;
  onTemplateChange: (template: string) => void;
}) {
  const [labelTemplate, setLabelTemplate] = useState(numberTemplate === "{number}" ? `${kind} {number}` : numberTemplate);
  const numberOnly = numberTemplate === "{number}";
  const key = (format: string, letterCase: string | null) => format === "source" ? "source" : `${format}:${letterCase}`;
  const current = key(format, letterCase);
  const known = numberFormats.some((option) => key(option.format, option.letterCase) === current);
  function example(option: typeof numberFormats[number], casing: string | null) {
    let text = numberTemplate.replace("{number}", option.example);
    if (casing === "upper") text = text.toUpperCase();
    else if (casing === "lower") text = text.toLowerCase();
    return text;
  }
  const savedFormat = numberFormats.find((option) => option.format === format);
  return <div className="design-field">
    <label>Number format
      <select aria-label="Number format" value={current} onChange={(event) => {
        const option = numberFormats.find((item) => key(item.format, item.letterCase) === event.target.value);
        if (option) onChange({ number_format: option.format, number_case: option.letterCase ?? letterCase });
      }}>
        {!known && <option value={current}>
          Saved setting: {savedFormat ? example(savedFormat, letterCase) : format} ({savedFormat?.label ?? format} / {letterCase} label)
        </option>}
        {numberFormats.map((option) => <option key={key(option.format, option.letterCase)}
          value={key(option.format, option.letterCase)}>
          {option.example ? `${example(option, option.letterCase)} (${option.label})` : option.label}
        </option>)}
      </select>
    </label>
    <label><input type="checkbox" aria-label="Number only" checked={numberOnly} disabled={format === "source"}
      onChange={(event) => {
        if (event.target.checked) {
          setLabelTemplate(numberTemplate);
          onTemplateChange("{number}");
        } else onTemplateChange(labelTemplate);
      }} /> Number only (omit {kind}/label wording)</label>
    <p className="muted">Examples use number 4 and your label wording. Number only does not hide the opening title.
      Capitalization is included in the choice. Source keeps the original label. Generated words are English.</p>
  </div>;
}

export function ValueChoices({ name, value, options, onChange, schema = {}, numeric = false, hint }: {
  name: string; value: Scalar; options: Option[]; onChange: (value: Scalar) => void;
  schema?: JsonSchema; numeric?: boolean; hint?: string;
}) {
  const nullable = value === null || (Array.isArray(schema.type) && schema.type.includes("null"));
  const known = options.some((option) => option.value === value);
  const [custom, setCustom] = useState(!known && value !== null);
  return <div className="design-field">
    <label>{name}
      <select aria-label={`${name} preset`} value={custom || (!known && value !== null) ? "custom" : JSON.stringify(value)}
        onChange={(event) => {
          const next = event.target.value;
          setCustom(next === "custom");
          if (next !== "custom") onChange(JSON.parse(next) as Scalar);
        }}>
        {nullable && !options.some((option) => option.value === null) && <option value="null">Not selected</option>}
        {options.map((option) => <option key={JSON.stringify(option.value)} value={JSON.stringify(option.value)}>
          {option.label}
        </option>)}
        <option value="custom">Custom value...</option>
      </select>
    </label>
    {(custom || (!known && value !== null)) && <label>Exact {name}
      <input aria-label={`Custom ${name}`} type={numeric ? "number" : name === "color" ? "color" : "text"}
        value={value ?? ""} step={schema.type === "integer" || (Array.isArray(schema.type) && schema.type.includes("integer")) ? 1 : "any"}
        min={schema.minimum} max={schema.maximum} pattern={schema.pattern}
        onChange={(event) => onChange(numeric ? Number(event.target.value) : event.target.value)} />
    </label>}
    {hint && <p className="muted">{hint}</p>}
  </div>;
}

const trims = [
  [5, 8], [5.25, 8], [5.5, 8.5], [6, 9], [6.14, 9.21], [7, 10], [8.5, 11],
].map(([width, height]) => ({
  id: `${width}x${height}`, label: `${width} x ${height} in`,
  width: Number((width * 25.4).toFixed(3)), height: Number((height * 25.4).toFixed(3)),
}));
const inches = (mm: number) => new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 }).format(mm / 25.4);

export function TrimChoices({ value, ranges, paper, onChange }: {
  value: Trim | null; ranges?: PaperRanges; paper: string | null; onChange: (value: Trim) => void;
}) {
  const match = trims.find((trim) => value && Math.abs(trim.width - value.width) < 0.001
    && Math.abs(trim.height - value.height) < 0.001);
  const [custom, setCustom] = useState(!match);
  const envelopes = ranges ? (paper && ranges[paper] ? [ranges[paper]] : Object.values(ranges)) : [];
  const outside = (trim: Trim) => envelopes.length > 0 && !envelopes.some((range) =>
    trim.width / 25.4 >= range.width[0] - 0.0001 && trim.width / 25.4 <= range.width[1] + 0.0001
    && trim.height / 25.4 >= range.height[0] - 0.0001 && trim.height / 25.4 <= range.height[1] + 0.0001);
  return <div className="design-field">
    <label>Trim size (width x height)
      <select aria-label="Trim size preset" value={custom || !match ? "custom" : match.id}
        onChange={(event) => {
          const chosen = trims.find((trim) => trim.id === event.target.value);
          setCustom(!chosen);
          if (chosen) onChange({ width: chosen.width, height: chosen.height });
        }}>
        {trims.map((trim) => <option key={trim.id} value={trim.id} disabled={outside(trim)}>
          {trim.label}{outside(trim) ? " - outside profile range" : ""}
        </option>)}
        <option value="custom">Custom dimensions...</option>
      </select>
    </label>
    {value && <p className="muted">Current trim: {inches(value.width)} x {inches(value.height)} in
      {" "}(width x height); {value.width} x {value.height} mm.</p>}
    {(custom || !match) && <div className="row">
      {(["width", "height"] as const).map((dimension) => <label key={dimension}>Custom {dimension} (mm)
        <input aria-label={`Custom trim ${dimension} mm`} type="number" min="0.001" step="any"
          value={value?.[dimension] ?? ""} onChange={(event) => onChange({
            width: value?.width ?? 152.4, height: value?.height ?? 228.6,
            [dimension]: Number(event.target.value),
          })} />
      </label>)}
    </div>}
    <p className="muted">Presets are starting points, not a vendor product catalog.
      {ranges && " Profile ranges inform these choices; confirm the exact paper/ink/binding product before printing."}
      {" "}Changing trim updates both the page and output specification.</p>
  </div>;
}

export function numericChoices(name: string, mm: boolean, schema: JsonSchema): Option[] {
  const sets: Record<string, number[]> = {
    size_pt: [9, 10, 10.5, 11, 11.5, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48],
    first_line_indent_mm: [0, 3, 4, 5, 6.35, 7.62],
    space_before_pt: [0, 3, 6, 9, 12, 18, 24, 36],
    space_after_pt: [0, 3, 6, 9, 12, 18, 24, 36],
    gutter_mm: [0, 3, 4, 5, 6.35, 8, 10],
    bleed_mm: [0],
    heading_level: [1, 2, 3, 4, 5, 6],
    widow_lines: [0, 1, 2, 3], orphan_lines: [0, 1, 2, 3],
    body_numbering_start: [1],
  };
  const values = sets[name] ?? (mm ? [0, 10, 12.7, 15, 18, 20, 22, 25.4] : []);
  return values.filter((value) => (schema.minimum === undefined || value >= schema.minimum)
    && (schema.maximum === undefined || value <= schema.maximum)).map((value) => ({
      value, label: `${value}${mm ? " mm" : name.endsWith("_pt") ? " pt" : ""}`,
    }));
}

export function LineSpacingChoices({ value, onChange }: {
  value: { mode: string; value: number }; onChange: (value: JsonValue) => void;
}) {
  const options = [
    ...[1, 1.15, 1.2, 1.3, 1.5, 2].map((number) => ({ mode: "multiple", value: number, label: `${number} x lines` })),
    ...[12, 14, 16, 18, 20, 24].map((number) => ({ mode: "exact-pt", value: number, label: `Exactly ${number} pt` })),
  ];
  const current = options.findIndex((option) => option.mode === value.mode && option.value === value.value);
  const [custom, setCustom] = useState(current < 0);
  return <div className="design-field">
    <label>Line spacing
      <select aria-label="Line spacing preset" value={custom || current < 0 ? "custom" : String(current)}
        onChange={(event) => {
          setCustom(event.target.value === "custom");
          if (event.target.value !== "custom") {
            const { mode, value } = options[Number(event.target.value)];
            onChange({ mode, value });
          }
        }}>
        {options.map((option, index) => <option key={index} value={index}>{option.label}</option>)}
        <option value="custom">Custom spacing...</option>
      </select>
    </label>
    {(custom || current < 0) && <>
      <label>Custom spacing mode
        <select value={value.mode} onChange={(event) => onChange({ ...value, mode: event.target.value })}>
          <option value="multiple">Line multiple</option><option value="exact-pt">Exact points</option>
        </select>
      </label>
      <label>Custom spacing value
        <input type="number" min="0.001" step="any" value={value.value}
          onChange={(event) => onChange({ ...value, value: Number(event.target.value) })} />
      </label>
    </>}
  </div>;
}

export function FontFallbackChoices({ value, onChange }: { value: string[]; onChange: (value: string[]) => void }) {
  return <details><summary>fallback families ({value.length})</summary>
    {value.map((font, index) => <div key={index}>
      <ValueChoices name={`fallback font ${index + 1}`} value={font} options={fontChoices}
        onChange={(next) => onChange(value.map((previous, i) => i === index ? String(next) : previous))} />
      <button type="button" onClick={() => onChange(value.filter((_, i) => i !== index))}>Remove fallback font</button>
    </div>)}
    <button type="button" onClick={() => onChange([...value, "Noto Serif"])}>Add fallback font</button>
    <p className="muted">Fonts are suggestions, not proof of installation, licensing or glyph coverage.</p>
  </details>;
}
