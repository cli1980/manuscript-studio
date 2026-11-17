import { api } from "../api";
import { ErrorBox, useLoad, when } from "./common";

export function ApprovedSheets({ runId, changed }: { runId: string; changed: string | null }) {
  const history = useLoad(() => api.approvedSheets(runId), [runId], changed);
  return (
    <section className="approved-sheets" aria-label="Approved sheets">
      <h2>Approved Sheets</h2>
      <p className="muted">Download past approved sheets as Markdown.</p>
      <ErrorBox error={history.error} />
      {!history.data && !history.error && <p className="muted">Loading approved sheets...</p>}
      {history.data?.length === 0 && <p className="muted">No approved sheets yet.</p>}
      <ul className="list sheet-history">
        {history.data?.map((entry) => (
          <li key={entry.receipt_id}>
            <a href={api.approvedSheetDownload(runId, entry.receipt_id)} download>
              {entry.title}{" \u00b7 revision "}{entry.revision}
            </a>
            <div className="muted">
              {entry.pass_number != null ? `Pass ${entry.pass_number}: ` : ""}
              {entry.stage_title}{" \u00b7 "}{entry.scope}
            </div>
            <small>{when(entry.created_at)}</small>
            {entry.superseded && <div><span className="tag">superseded</span></div>}
          </li>
        ))}
      </ul>
    </section>
  );
}
