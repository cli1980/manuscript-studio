import { useState } from "react";
import { api } from "../api";
import { useLoad } from "./common";

export function useModelSelection(workflow: string | undefined) {
  const execution = useLoad(api.execution, []);
  const [selected, setSelected] = useState<{ workflow: string | undefined; key: string }>({ workflow, key: "" });
  const configured = !!execution.data?.models.length;
  const models = execution.data?.models.filter((m) =>
    workflow && (!m.workflows.length || m.workflows.includes(workflow))) ?? [];
  const key = selected.workflow === workflow ? selected.key : "";
  const model = models.find((m) => m.model_key === key)?.model_key
    || models.find((m) => m.model_key === execution.data?.default_model)?.model_key || "";
  return {
    catalog: execution.data, error: execution.error, configured, models, model,
    ready: !!execution.data && (!configured || !!model),
    select: (key: string) => setSelected({ workflow, key }),
  };
}

type Selection = ReturnType<typeof useModelSelection>;

export function ModelPicker({ selection }: { selection: Selection }) {
  if (!selection.configured) return null;
  return <label>Model{" "}
    <select value={selection.model} onChange={(e) => selection.select(e.target.value)}>
      <option value="">Select a compatible model...</option>
      {selection.models.map((m) => <option key={m.model_key} value={m.model_key}>
        {m.model} / {m.endpoint ?? m.harness}
      </option>)}
    </select>
  </label>;
}

export function ExecutionProfileNotice({ selection }: { selection: Selection }) {
  if (!selection.configured) return null;
  return <p className="muted">Execution profile: {selection.catalog?.name} ({selection.catalog?.harness}).
    {selection.catalog?.harness === "pi" && " Pi POC runs trusted local tools without an OS sandbox."}</p>;
}
