import { api, type RunDetail } from "../api";

export function DocxDelivery({ run, perform }: {
  run: RunDetail; perform: (operation: () => Promise<RunDetail>) => void;
}) {
  const job = run.production;
  if (!job) return null;
  return <div className="panel docx-delivery">
    <h2>{job.docx ? "Editable DOCX" : "Generating draft DOCX"}</h2>
    <p className="banner warn">{job.notice}</p>
    <p>{job.summary.units} document sections, {job.summary.paragraphs} mapped paragraphs, {job.summary.styles.length} named styles</p>
    {job.summary.toc && <div className="banner warn">
      <strong>TOC field: update in Word</strong>
      {job.summary.toc.heading && <p>Heading: {job.summary.toc.heading} ({job.summary.toc.heading_style_id}).</p>}
      {job.summary.toc.start && <p>TOC section starts {job.summary.toc.start === "recto" ? "recto (right-hand page)" : "on a new page"}.</p>}
      <p>Inserted before {job.summary.toc.before_chapter_id}, depth {job.summary.toc.depth},
        using {job.summary.toc.entry_styles.join(", ")} based on {job.summary.toc.style_id}.
        There are {job.summary.toc.eligible_headings} eligible body headings.</p>
      <p>The TOC is intentionally unpopulated. In Word, right-click it and choose Update Field / Update entire table,
        or select all and press F9. Word may also prompt to update fields on opening.
        Entries, page numbers and pagination are not calculated or verified by Studio.</p>
      {job.summary.toc.prompt && <p>Its field result initially displays: {job.summary.toc.prompt}</p>}
    </div>}
    <p className="mono muted">Plan: {job.plan_sha256}</p>
    <details><summary>Effective generation policies</summary>
      <dl>{Object.entries(job.summary.policy).map(([key, value]) =>
        <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{JSON.stringify(value)}</dd></div>)}</dl>
      <p>Styles: {job.summary.styles.join(", ")}</p>
      {job.summary.vendor_warnings.length > 0 && <pre>{JSON.stringify(job.summary.vendor_warnings, null, 2)}</pre>}
    </details>
    {job.docx && run.status !== "CANCELLED" && <>
      <p><a className="button" href={api.docxUrl(run.id, job.id)} download>
        Download {job.accepted ? "accepted DOCX" : "DOCX candidate"}</a></p>
      <p className="mono muted">SHA-256: {job.docx.sha256}</p>
      <p>Open the document in Word for inspection and post-generation editing. Generated styles are Quick Styles.
        Changes made in Word are not synchronized back into this workflow.</p>
      {!job.accepted && run.status === "WAITING_FOR_ACCEPTANCE" && run.acceptance
        && run.engine_current && !run.worker.active && <p>
        <button onClick={() => perform(() => api.reopenInteriorDesign(
          run.id, run.acceptance!.acceptance_id, job.docx!.sha256))}>Revise design</button>
        <span className="muted">Return to the saved settings or request an agent revision, then generate a new draft.
          This candidate stays in history but can no longer be approved.</span>
      </p>}
    </>}
    {job.status === "building" && <p>Building and checking the DOCX without an agent or renderer.</p>}
  </div>;
}
