# Workflow Handoff

Studio's literary editing and translation flows compose:

`Preparation -> Metadata confirmation -> Manuscript analysis -> Workflow-specific work`

Metadata confirmation remains intake's existing human gate. Analysis introduces
no new approval gate: a complete, evidence-audited reading passes directly to
translation briefing or editing-pass selection. It remains provisional and does
not satisfy querying's separate atomic author-review and final-closure policy.
Real questions or incomplete reading may still block progress.

## Bound document package

The host supplies a revision-specific destination, five `output_paths`, and a
`manifest_template`. Write the document package defined in
[analysis-contract.md](analysis-contract.md), preserving the complete migrated
ledger and its evidence/uncertainty conventions.

Also write `analysis-manifest.json` at the supplied `manifest_path`. This is a
thin machine-checkable binding/coverage envelope, not a competing story model.
The Markdown ledger remains the narrative authority. Its required fields are:

- `contract`: `manuscript-analysis/1`; `analysis_id`: the host-provided identity.
- `basis`: copy the exact work/source identity, preparation revision/manifest
  path/hash, language, and ordered unit IDs, roles, paths and hashes.
- `metadata_record_revision`: the consumed shared metadata revision.
- `analysis_language`: the manuscript language for these workflows.
- `approval_status`: `provisional`. Never claim human approval.
- `coverage`: exactly one record per unit, in source order, with `chapter_id`,
  `sha256`, `status: read`, and nonempty `evidence` records containing an exact
  source `quote` and its nonempty `locator`.
- `evidence_audit`: `passed` only after the skill's full evidence audit.
- `qualifications`: a list of unresolved interpretations and limitations, empty
  only when there are none. Qualified ambiguity need not become an invented fact.
- `artifacts`: the five host-provided keys/paths, each with the SHA-256 of the
  actual saved Markdown bytes. Do not substitute source or consumer files.

Return `completed` with `state_path=manifest_path` and other output/gate paths
null. The host checks coverage identities/order, source quotes, artifact
presence/hashes and source freshness, then freezes snapshots. These deterministic
checks do not prove full reading, semantic correctness or literary quality.

## Direct downstream context

`manuscript_analysis` contains the immutable manifest/document references,
source basis, qualifications, provisional status and producer provenance.
Consumers read these existing files rather than constructing competing ledgers.
They retain source verification and their own translation/editorial decisions.
The files are included in accepted publication/export alongside the run record.

For editing, `current_text_matches_source` becomes false if the editable
manuscript differs from the prepared source. Then the package is historical
source context only: read the current text and later editorial/continuity
records. Do not use old analysis as evidence that an edited manuscript still
contains a fact. Target-text analysis needs its own source binding.

Changing a frozen analysis file is refused. An allowed stage restart creates
a fresh analysis revision and invalidates dependent work; preparation restarts
also clear analysis. Accepted passes/finalization retain their existing restart
restrictions. Existing runs are not silently migrated or granted approvals.
