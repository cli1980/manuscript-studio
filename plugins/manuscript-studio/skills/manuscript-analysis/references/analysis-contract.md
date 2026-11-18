# Manuscript Analysis Handoff Contract

Contract: `manuscript-analysis/2`.

This remains a document-based story contract, not an executable JSON story-graph
schema. The migrated ledger Markdown owns story records; the review Markdown
owns the domain approval audit; review JSON is only interface state. Do not
create an independent `understanding.json` authority until that future contract
is specified and implemented.

Workflow hosts may also require the thin `analysis-manifest.json`
[binding/coverage envelope](workflow-handoff.md). It does not duplicate story
records or confer author approval. Studio uses this to pass the frozen document
package directly from preparation/intake to translation and editorial consumers.

## Intake routing

- A designated `prepare-manuscript` `work.json` is direct input. Resolve and
  validate its current revision, source binding, requested scope and ordered
  unit files before reading; no second extraction is needed for fresh input.
- A designated raw manuscript automatically delegates to the sibling
  [prepare-manuscript skill](../../prepare-manuscript/SKILL.md). Invoke it where
  supported, or follow its full instructions as an instruction-based subtask.
  Pass the source locator/scope and a neutral output destination, then consume
  the returned work-record locator only after successful readiness validation.
- No extra user invocation is required merely because the input is raw.
  Missing permissions, ambiguous authority/scope, unavailable extraction tools
  and unresolved source problems remain real blockers, not reasons to fabricate
  a ready package. Preserve source files and propagate preparation failures.

This is skill-level delegation, not a new host dispatcher or automatic workflow
transition. It does not bypass existing metadata or human-review gates.

## Output package

```text
manuscript-analysis/
  revisions/<analysis-id>/
    analysis-manifest.md
    story-ledger.md
    chapter-summaries.md
    synopsis.md
    reading-profile.md
    story-ledger-review.md      # When review is requested/required
    story-ledger-review.json    # Synchronized shared-interface state
```

All files belong to the same analysis revision. Draft analysis may be resumed;
published revisions are immutable. New source or material corrections create a
new revision with a supersedes link. Never overwrite the original, preparation
or a consumer's records. Do not inspect Git or commit artifacts unless asked.

### Analysis manifest

Record:

- contract, analysis ID/revision, creation/update dates, prior/superseded identity;
- work ID, exact designated source locator/identity/checksum, preparation
  revision/manifest hash, scope, manuscript language and ordered unit hashes;
- consumed shared metadata fields/values and record revision; do not use a
  mutable metadata-record checksum as a substitute for manuscript identity;
- analysis language, requested depth/policy and credential-free producer details;
- every unit's read/partial/unread/blocked status and source-bound coverage;
- artifact locators/hashes, ledger revision, evidence-audit counts/failures;
- ledger status, synopsis readiness, review identity/revision, human-gate state,
  item counts, closure receipt and surviving qualifications when applicable;
- unresolved claims, unsupported source forms and consumer-specific limitations.

A missing file, hash mismatch, partial read or stale source cannot be hidden by
an overall success label. Byte/schema checks cannot prove semantic reading
accuracy; distinguish deterministic checks, agent assertions and human review.

### Chapter summaries

Use one record per prepared unit, retaining its ID, order, role and hash. Include
summary, viewpoint/source, time/place where supported, participants, major
events/choices/consequences, arc/thread developments, uncertainties and links
to ledger IDs and exact source spans. Cover front/back matter without inventing
plot. Do not split the original into artificial chapters for processing.

### Synopsis and reading profile

The neutral synopsis includes the actual ending and material resolutions; label
unapproved claims and unresolved interpretations. It is neither query prose nor
a submission-ready synopsis. The profile records manuscript-derived genre,
voice, themes, structure and readership hypotheses, not external market claims.
Neither file overrides source evidence, the ledger or shared metadata.

The profile also proposes **BISAC Subjects, Thema Subjects, Keywords and Place
Subjects** under the [subject-proposals contract](subject-proposals.md).
All four groups need an explicit assessment, including a reason when no
supported proposal is possible. Preserve source evidence, confidence and
rationale, vocabulary edition/reference for codes, and real/historical/
fictional/unspecified place distinctions. These are discovery suggestions,
not metadata edits or author approval. The host mirrors them in the frozen
JSON envelope for display and handoff; this is not a second story model.

## Readiness and human review

Keep analysis coverage separate from approval. An analyzed, evidence-audited
whole manuscript may be useful as provisional context while ledger status is
`awaiting-confirmation`, human gate is `open` or `not-built`, and synopsis
readiness is `not-ready`. Do not call that author-approved.

For consumers requiring confirmed story claims, apply the complete
[ledger review protocol](story-ledger-human-review.md). Only an audit-passing,
unchanged ledger with every required proposition resolved and separate final
closure may be `approved`, gate `passed`, and synopsis-ready. Optional open
items cannot include a claim required by the selected consumer/profile.

## Consumer handoff

Consumers record the manifest locator and checksum, ledger identity/checksum,
analysis revision, source/preparation binding, required coverage, review identity
and state, and limitations. Check hashes and source freshness before reuse.
Equivalent filenames or revision labels are not proof of identical text.

| Consumer | Use and retained authority |
| --- | --- |
| Querying | Requires whole-work coverage, passed evidence audit and the complete item-level human gate. Uses the approved ledger as its sole story authority. Owns its adapter, positioning, comps, agent research, pitch, agent-specific synopsis and submission packaging. |
| Translation | Can use the source reading as context for glossary/voice/samples. Still checks source passages and obtains its own translation approvals. Target-text analysis needs its own exact binding. |
| Developmental editing | Can use the map as a starting point, but must read the complete manuscript and independently assess it. Analysis is not a verdict or approved recommendation. |
| Line/copy editing | Uses continuity context without applying changes or treating interpretations as facts. Accepted changes may invalidate analysis. |
| Interior design | Can adapt bound reading with provenance. Must revalidate changed edited/translated text and keep design approval distinct. |

These are skill-level handoffs, not claims that Studio/CLI stages have been wired
for those consumers. The host, not this skill, owns workflow transitions.

If a consumer identifies a gap, return claim IDs, conflicting evidence and
requested refresh scope to manuscript analysis. It owns ledger repair and
review invalidation; a consumer must not silently repair its own fork or alter
the approved ledger while drafting.

## Reuse and source permissions

Only explicitly designated analysis and source locations are authorized.
Analysis cannot launder forbidden inputs: a querying job must reject analysis
derived from editorial-process outputs even if the analysis folder is elsewhere.
Prior pitches, model summaries and terminal query packages are not evidence.
Adopt older query-local ledgers only through an explicitly authorized analysis
refresh/adoption with checked source identity, audit and review bindings; do not
silently promote them or assume approval survives changed content.
