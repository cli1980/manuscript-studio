import { useState } from "react";
import { api, type RunDetail } from "../api";

export function DocxDelivery({ run, perform }: {
  run: RunDetail; perform: (operation: () => Promise<RunDetail>) => void;
}) {
  const job = run.production;
  const [confirmed, setConfirmed] = useState(false);
  if (!job) return null;
  const canAuthorize = job.status === "plan-review" && run.gate?.kind === "docx_generation_review"
    && run.engine_current && !run.worker.active;
  return <div className="panel docx-delivery">
    <h2>{job.docx ? "Editable DOCX" : "DOCX generation plan"}</h2>
    <p className="banner warn">{job.notice}</p>
    <p>{job.summary.units} manuscript units, {job.summary.paragraphs} paragraphs, {job.summary.styles.length} named styles</p>
    <p className="mono muted">Plan: {job.plan_sha256}</p>
    <details><summary>Effective generation policies</summary>
      <dl>{Object.entries(job.summary.policy).map(([key, value]) =>
        <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{JSON.stringify(value)}</dd></div>)}</dl>
      <p>Styles: {job.summary.styles.join(", ")}</p>
      {job.summary.vendor_warnings.length > 0 && <pre>{JSON.stringify(job.summary.vendor_warnings, null, 2)}</pre>}
    </details>
    {canAuthorize && <>
      <label><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />{" "}
        I authorize this exact editable-DOCX generation plan.</label>
      <p><button disabled={!confirmed} onClick={() => perform(() =>
        api.authorizeDocx(run.id, run.gate!.id, job.plan_sha256))}>Generate editable DOCX</button></p>
    </>}
    {job.docx && run.status !== "CANCELLED" && <>
      <p><a className="button" href={api.docxUrl(run.id, job.id)} download>
        Download {job.accepted ? "accepted DOCX" : "DOCX candidate"}</a></p>
      <p className="mono muted">SHA-256: {job.docx.sha256}</p>
      <p>Open the document in Word for inspection and post-generation editing. Generated styles are Quick Styles.
        Changes made in Word are not synchronized back into this workflow.</p>
    </>}
    {job.status === "building" && <p>Building and checking the DOCX without an agent or renderer.</p>}
  </div>;
}
