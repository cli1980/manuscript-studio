# Manuscript Analysis to Querying

Read the sibling [manuscript-analysis skill](../../manuscript-analysis/SKILL.md)
and its [analysis contract](../../manuscript-analysis/references/analysis-contract.md).
It owns full-manuscript reading, chapter summaries, reading profile, story
ledger, evidence audit, corrections and item-level story review. Querying owns
market positioning, author/rights intake, comps, agent research, pitches,
submission-specific synopsis drafting, samples and complete agent packages.

## Required shared input

Use an explicitly designated analysis revision outside editorial-process and
query-output folders. Record in `query-package/static/package-manifest.md`:

- analysis manifest locator/checksum, contract and revision;
- ledger locator/revision/checksum and its exact manuscript/preparation binding;
- whole-work coverage and passing evidence audit;
- human-review artifact identities/checksums/revision, counts and gate status;
- explicit final closure and all qualifications that survive compression.

Require ledger `approved`, synopsis readiness `ready` or applicable
`ready-with-open-items`, gate `passed`, no required pending/correction/invalidated
items, matching review/ledger bindings, unchanged source and verified artifacts.
Recheck before generating story-dependent prose or building an on-demand ZIP.
A source identity, analysis hash or approval mismatch makes querying `not-ready`.

Do not create `static/story-ledger.md` or local review copies. The static manifest
pins the external analysis rather than becoming another mutable story authority.
Old query-local ledgers need explicit adoption/refresh through manuscript
analysis; do not silently accept or relocate their approvals.

If analysis is absent, delegate to manuscript analysis using the authorized
prepared manuscript and destination. If the source is unavailable, record
author-supplied intake and clearly unverified research/positioning only; do not
invent a source-grounded ledger or mark story-dependent prose/package ready.
Source and output permissions still apply: an analysis derived from forbidden
editorial material is not an exception to querying's evidence restrictions.

## Approval and correction ownership

Analysis builds the ledger and uses its
[human-review protocol](../../manuscript-analysis/references/story-ledger-human-review.md).
Every synopsis-eligible atomic `HG` proposition needs an explicitly enumerated
disposition, corrected/dependent claims need re-review, and final closure is a
separate submission. Querying cannot set these states or replace them with
approval of positioning, a package, synopsis or blanket ledger approval.

If query drafting exposes a missing/overstated claim, stop the affected output.
Return claim IDs, evidence conflict and requested refresh to manuscript analysis;
obtain authorization for targeted source rereading where needed. Analysis owns
repair, dependent invalidation and renewed closure. Then repin the new revision
and invalidate affected static drafts and products derived from the old one.
Never fix a consumer-local ledger fork or silently broaden source access.

## Positioning and story-side prose

Use the analysis reading profile as evidence for genre, prose essence, tone,
themes and narrative engine. Querying still chooses market-facing category,
reader promise, hook, emphasis, comps and rhetorical strategy, with the author's
confirmation. It must not change story facts to fit an agent.

For each query/synopsis sentence, split material assertions into atomic clauses
and map each to approved ledger IDs and source locators. Preserve character
belief versus fact, uncertainty, identity boundaries, causality, motives, object
authority and knowledge timing. An unchanged approved analysis eliminates
unnecessary raw-source rereading, not the consumer's claim audit.

## Agent-specific synopsis

The analysis package may contain a neutral full synopsis. It is not a query
artifact, submission authority or authorized on-demand product; never copy it
into a package or use it instead of the approved linked ledger.

Only when an explicit named-agent complete-package build is authorized and
current official guidelines request a synopsis:

1. Verify the pinned approved ledger and passed gate above.
2. Start an empty staged synopsis file outside the terminal on-demand tree.
   Select ledger compression records for the required length/format/emphasis.
3. Draft fresh from linked events, threads, arcs, revelations and resolutions.
   Include the actual ending, causal movement and protagonist's emotional spine.
4. Audit every material clause against ledger IDs and qualifications. Do not
   invent transitions, conflate entities, imply unsupported motives/knowledge,
   or manufacture resolution of deliberately open threads.
5. If a ledger gap emerges, stop and route it to analysis; otherwise no separate
   synopsis approval or raw-source reread is required.
6. Run the final prose gate and repeat the claim audit after the last wording
   change. Record counts, ledger/analysis revision and fresh-reproduction
   declarations in the on-demand manifest.
7. Deliver only inside the complete validated agent ZIP, never loose. Never
   read or reuse a prior on-demand product. Keep query pitches compact; a missing
   synopsis requirement does not authorize a synopsis disguised as a query.

Official research, named-agent authorization, sample boundaries, final prose
checks, complete ZIP validation and permission to actually send remain governed
by [the query package specification](package-spec.md).
