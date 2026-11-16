import type { TokenUsage as Usage } from "../api";

const tokens = (value: number | null) => value == null ? "Not reported" : value.toLocaleString("en-US");

export function TokenUsage({ usage }: { usage?: Usage }) {
  return (
    <details className="panel token-usage" open>
      <summary><h2>Token usage</h2></summary>
      <div className="facts">
        <div><span>Total tokens</span>{tokens(usage?.total_tokens ?? null)}
          {usage?.partial && usage.total_tokens != null && <small className="muted"> (partial)</small>}</div>
        <div><span>Input tokens</span>{tokens(usage?.input_tokens ?? null)}</div>
        <div><span>Output tokens</span>{tokens(usage?.output_tokens ?? null)}</div>
        <div><span>Cached input</span>{tokens(usage?.cached_input_tokens ?? null)}</div>
        {usage && <div><span>Usage reported</span>{usage.reported_attempts} of {usage.attempts} agent turns</div>}
      </div>
      <p className="muted">Includes reported usage from failed and retried turns. Cached input is part of input, not
        added again to the total. Harness-reported counts are not a billing statement. Updates at saved turn boundaries.</p>
      {usage?.warnings.map((warning) => <p className="muted" key={warning}>{warning}</p>)}
    </details>
  );
}
