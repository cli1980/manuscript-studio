import { useEffect, useMemo, useState } from "react";
import type { Sheet, SheetItem } from "../api";
import { TextBlock } from "./common";

// Translation brief sample poll: each sample's original beside its tryout variants. The reviewer picks one
// variant per sample (or none of them) and may give reasons; one submission covers every open sample.

type Choice = { decision: string; note: string };

export function SamplePoll({ sheet, onSubmit, busy = false }: { sheet: Sheet; onSubmit: (text: string) => void; busy?: boolean }) {
  const key = `sample-poll:${sheet.sheet_id}:${sheet.revision}`;
  const [choices, setChoices] = useState<Record<string, Choice>>(() => {
    try { return JSON.parse(localStorage.getItem(key) ?? "{}"); } catch { return {}; }
  });
  useEffect(() => { localStorage.setItem(key, JSON.stringify(choices)); }, [key, choices]);
  const decisions = useMemo(() => Object.fromEntries(sheet.decisions.map((d) => [d.id, d])), [sheet]);
  const open = sheet.items.filter((item) => item.status !== "resolved");
  const ready = (item: SheetItem) => {
    const choice = choices[item.id];
    return !!choice?.decision && !(decisions[choice.decision].requires_note && !choice.note.trim());
  };

  function update(itemId: string, change: Partial<Choice>) {
    setChoices((old) => ({ ...old, [itemId]: { ...(old[itemId] ?? { decision: "", note: "" }), ...change } }));
  }

  function submit() {
    const lines = open.map((item) => {
      const choice = choices[item.id];
      const command = decisions[choice.decision].command;
      const note = choice.note.trim().replace(/\s*\n\s*/g, " ");
      return note ? `${item.id} ${command}: ${note}` : `${item.id} ${command}`;
    });
    onSubmit(lines.join("\n"));
    localStorage.removeItem(key);
  }

  return (
    <div className="sample-poll">
      <p className="muted">{sheet.submission.instruction}</p>
      {sheet.items.map((item) => {
        const row = (label: string) => item.details.find((d) => d.label === label)?.value;
        const allowed = item.allowed_decisions.map((id) => decisions[id]);
        const variants = allowed.filter((d) => d.effect === "resolve" && row(d.label) != null);
        const others = allowed.filter((d) => !variants.includes(d));
        const shown = new Set(["Original", ...variants.flatMap((d) => [d.label, `About ${d.label}`])]);
        const choice = choices[item.id];
        return (
          <div key={item.id} className="panel sample">
            <h3>{item.id} <span className="muted">{item.summary}</span> <span className="tag">{item.status_label ?? item.status}</span></h3>
            {item.details.filter((d) => !shown.has(d.label)).map((d) => <p key={d.label} className="muted">{d.label}: {d.value}</p>)}
            <div className="label">Original</div>
            <TextBlock text={row("Original") ?? ""} />
            <div className="columns">
              {variants.map((d) => (
                <label key={d.id} className={`variant ${choice?.decision === d.id ? "chosen" : ""}`}>
                  <div><input type="radio" name={`${key}-${item.id}`} disabled={item.status === "resolved"}
                    checked={choice?.decision === d.id} onChange={() => update(item.id, { decision: d.id })} /> <strong>{d.label}</strong></div>
                  <TextBlock text={row(d.label) ?? ""} />
                  {row(`About ${d.label}`) && <p className="muted">{row(`About ${d.label}`)}</p>}
                </label>
              ))}
            </div>
            {item.status !== "resolved" && (
              <>
                <div className="row">
                  {others.map((d) => (
                    <label key={d.id}><input type="radio" name={`${key}-${item.id}`} checked={choice?.decision === d.id}
                      onChange={() => update(item.id, { decision: d.id })} /> {d.label}{d.requires_note ? " (reason required)" : ""}</label>
                  ))}
                </div>
                <textarea rows={2} value={choice?.note ?? ""} placeholder="Why you prefer this variant, or what is wrong with the others (optional)"
                  onChange={(e) => update(item.id, { note: e.target.value })} />
              </>
            )}
          </div>
        );
      })}
      <button className="primary" disabled={busy || !open.length || !open.every(ready)} onClick={submit}>
        Submit choices for {open.length} sample{open.length === 1 ? "" : "s"}
      </button>
      <span className="muted"> {open.filter(ready).length} of {open.length} decided.</span>
    </div>
  );
}
