import { api, type ChapterDetail, type RunDetail, type Overview as OverviewData } from "../api";
import { workflowUI } from "../workflows";
import { Documents, reviewName, when } from "./common";
import { MetadataDifferences, MetadataTable } from "./Metadata";
import { SubjectProposals } from "./SubjectProposals";

export function Overview({ data, run, onSaved }: { data: OverviewData; run: RunDetail; onSaved: () => Promise<void> }) {
  const reviews = data.source?.reviews ?? [];
  const metadataReview = reviews.find((review) => review.kind === "metadata_review");
  const groups = workflowUI(run.workflow).overviewReviewGroups;
  const claimed = new Set(groups.flatMap((group) => group.kinds));
  const other = reviews.filter((review) => review.kind !== "metadata_review" && !claimed.has(review.kind));
  return (
    <div className="overview-section">
      <section className="panel" aria-label="Work metadata">
        <h2>Metadata</h2>
        <p className="muted">Review preparation's draft metadata here, correct it, and fill in anything else you know.
          Optional fields may stay unknown. Changes are versioned, separate from manuscript text.</p>
        {metadataReview && <p className="tag ready">metadata confirmed (revision {metadataReview.record_revision})</p>}
        {data.metadata && run.gate?.kind !== "metadata_review"
          && <MetadataDifferences view={data.metadata} fields={data.metadata_fields} />}
        {run.gate?.kind === "metadata_review"
          ? <p>Review and confirm the metadata in the decision panel below.</p>
          : data.metadata
            ? <MetadataTable metadata={data.metadata.metadata} fields={data.metadata_fields}
                provenance={data.metadata.provenance} locked={data.metadata.locked}
                onSave={data.metadata_edit?.target ? async (field, value, rationale) => {
                  if (data.metadata_edit.target === "run") await api.editMetadata(run.id, { field, value, rationale });
                  else await api.editWorkMetadata(data.work_id, { field, value, rationale });
                  await onSaved();
                } : undefined} />
            : <p className="muted">Metadata becomes available after preparation.</p>}
        {data.metadata_edit?.run_id && data.metadata_edit.run_id !== run.id && <p>
          <a href={`#/runs/${data.metadata_edit.run_id}/overview`}>Open the current metadata editor</a>
        </p>}
        <a href={`#/works/${encodeURIComponent(data.work_id)}`}>Open shared work record</a>
        {run.input_version && <p className="muted">Metadata is pinned to the selected Work version.
          Review metadata on the Work to create another version without repeating the reading.</p>}
      </section>
      <section className="panel" aria-label="Manuscript analysis">
        <h2>Manuscript Analysis</h2>
        {data.analysis ? <>
          <p className="muted">Shared source reading for downstream skills. Provisional, not author-approved.</p>
          <p className="muted">{data.analysis.coverage_verification}</p>
          {!data.analysis.current_text_matches_source && <div className="banner warn">
            The manuscript has changed since this source analysis. Refer to current text and editorial records for later changes.
          </div>}
          {data.analysis.current_metadata_matches_analysis === false && <div className="banner">
            This reading used an earlier metadata snapshot. Its text binding is unchanged; use current confirmed
            metadata rather than older profile or catalogue assumptions.
          </div>}
          {data.analysis.qualifications.length > 0 && <ul>
            {data.analysis.qualifications.map((note, i) => <li key={i}>{note}</li>)}
          </ul>}
          {data.analysis.subject_proposals
            ? <SubjectProposals proposals={data.analysis.subject_proposals} />
            : <p className="muted">Subject proposals were not generated for this analysis revision.</p>}
          <Documents documents={data.analysis.documents} />
        </> : <p className="muted">{run.stage === "analysis"
          ? "Analysis is not complete. Results pass directly to the workflow; no extra approval is required."
          : "Shared analysis has not been generated for this run."}</p>}
      </section>
      {groups.map((group) => (
        <section className="panel reviews" key={group.title} aria-label={group.title}>
          <h2>{group.title}</h2>
          {reviews.some((review) => group.kinds.includes(review.kind))
            ? reviews.filter((review) => group.kinds.includes(review.kind)).map((review) =>
              <Review key={review.kind} review={review} finalized={run.finalized} />)
            : <p className="muted">No approved {group.title.toLowerCase()} yet. Its review appears here when requested.</p>}
        </section>
      ))}
      {other.length > 0 && <section className="panel reviews" aria-label="Other work reviews">
        <h2>Other work reviews</h2>
        {other.map((review) => <Review key={review.kind} review={review} finalized={run.finalized} />)}
      </section>}
    </div>
  );
}

function Review({ review, finalized }: { review: ChapterDetail["reviews"][number]; finalized: boolean }) {
  return (
    <div>
      {!!review.current_documents?.length && <div className="current-documents">
        <h3>{finalized ? "Final" : "Current"} {reviewName(review.kind)}</h3>
        <p className="muted">{finalized ? "Documents saved with the accepted output."
          : "Latest saved documents, including corrections and additions during this workflow."}</p>
        <Documents documents={review.current_documents} />
      </div>}
      <details>
        <summary><span className="tag ready">Approved {reviewName(review.kind)} — snapshot</span>{" "}
          <span className="muted">{review.decision_source !== "human" ? review.decision_source : ""} {when(review.created_at)}</span>
        </summary>
        <Documents documents={review.documents} />
      </details>
    </div>
  );
}
