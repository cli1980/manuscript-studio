import type { SubjectProposalGroups } from "../api";

const groups = [
  ["bisac_subjects", "BISAC Subjects"], ["thema_subjects", "Thema Subjects"],
  ["keywords", "Keywords"], ["place_subjects", "Place Subjects"],
] as const;

export function SubjectProposals({ proposals }: { proposals: SubjectProposalGroups }) {
  return <section aria-label="Subject proposals">
    <h3>Subject And Keyword Proposals</h3>
    <p className="muted">Suggestions from this source analysis, not applied to shared metadata.
      Existing keywords stay unchanged. Catalogue references are agent-supplied;
      codes and classifications need review before publication.</p>
    {groups.map(([key, title]) => {
      const group = proposals[key];
      return <details key={key}>
        <summary>{title} ({group.items.length}){group.status !== "proposed"
          ? ` - ${group.status.replaceAll("_", " ")}` : ""}</summary>
        {group.reason && <p>{group.reason}</p>}
        <ol>{group.items.map((item, index) => <li key={index}>
          <strong>{item.label}</strong>{" "}
          {item.code && <code>{item.code}</code>}
          {"code" in item && !item.code && <span className="muted">Code unresolved</span>}{" "}
          <span className="tag">{item.confidence} confidence</span>
          {item.kind && <> <span className="tag">{item.kind} place</span></>}
          <p>{item.rationale}</p>
          {item.reference && <p className="muted">
            Vocabulary: {item.scheme_version}; reference: {item.reference}
          </p>}
          <details>
            <summary>Source evidence ({item.evidence.length})</summary>
            {item.evidence.map((evidence, i) => <div key={i}>
              <p>{evidence.chapter_id}: {evidence.locator}</p>
              <blockquote>{evidence.quote}</blockquote>
            </div>)}
          </details>
        </li>)}</ol>
      </details>;
    })}
  </section>;
}
