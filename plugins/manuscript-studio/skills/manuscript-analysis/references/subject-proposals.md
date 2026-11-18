# Subject And Keyword Proposals

Analysis proposes bibliographic discovery terms after reading the whole
manuscript. These are interpretation-backed suggestions, not confirmed metadata,
publisher-approved positioning, or permission to change the shared work record.
Retain existing author-supplied keywords and classifications as separate input.

## Required Groups

Include these four headings in `reading-profile.md` and mirror the proposals
in the host's `subject_proposals` envelope:

- **BISAC Subjects** (`bisac_subjects`): ranked BISAC subject candidates.
  Usually propose one to three, most relevant first, using the work's substance
  and intended readership rather than isolated tropes or incidental mentions.
- **Thema Subjects** (`thema_subjects`): independently assessed Thema subject
  candidates, most relevant first. Do not assume a one-to-one BISAC crosswalk.
  Geographic, language, age and other Thema qualifiers are not subject codes.
- **Keywords** (`keywords`): typically five to twelve specific, useful words or
  short phrases in the manuscript language. Avoid duplicates, keyword stuffing,
  unsupported comparisons, marketing superlatives and spoiler-heavy phrases.
- **Place Subjects** (`place_subjects`): meaningful geographic settings or
  geographic topics, not every place mentioned or the author's residence.
  Mark each as `real`, `historical`, `fictional` or `unspecified`. Preserve the
  source's level of precision; do not map fictional or unnamed places onto
  guessed real locations or infer modern borders for historical settings.

Every group has `status`, `reason` and `items` under the
[JSON schema](subject-proposals.schema.json). Use `proposed` with at least one
item, or `not_applicable`/`undetermined` with an empty list and a substantive
reason. A pending/unassessed group is not a completed analysis. An unavailable
taxonomy does not block the whole reading: propose supported subject wording
with unresolved codes instead.

Each item has a `label`, `confidence` (`low`, `medium`, `high`), `rationale`
and at least one evidence record: `chapter_id`, `locator`, exact `quote`.
Evidence must come from the bound prepared manuscript, not model memory,
metadata alone or a catalogue. Explain the whole-work relevance in the
rationale; an exact quote establishes traceability, not semantic correctness.
Place items also require `kind`. Subject arrays are ordered by relevance;
neither their order nor any analysis approval confers metadata approval.

## Controlled Vocabularies

BISAC and Thema items additionally require `code`, `scheme_version` and
`reference`, each nullable. Give an official code/label pair only after checking
a designated catalogue or an accessible official BISG/EDItEUR reference. Record
the actual vocabulary edition/version and the specific reference URL or local
catalogue locator used. Preserve the official label even when analysis prose
is in another language. Never invent a code, edition, citation or crosswalk.
If lookup is unavailable or uncertain, set all three fields to `null`, propose
the subject wording, and explain the unresolved mapping in the rationale.

Studio checks shape, code syntax, source quotes and frozen bindings. It does
not independently validate code/label membership, reference contents or literary
judgment. References are agent-supplied evidence of lookup, not certification.
Do not fetch unrelated sources, upload manuscript text, or access external
accounts to obtain classifications.

## Review And Reuse

Expose all four groups for human inspection, including reasons for no proposal.
Do not introduce an extra analysis approval gate, overwrite confirmed keywords,
apply subjects to metadata, or publish catalogue records. A later explicit
metadata-edit decision remains separate. Querying's story-ledger approval does
not approve these classifications.

Freeze proposals with the analysis revision and source hashes. Changes to the
manuscript may make them historical; refresh through a new authorized analysis
revision rather than editing the old result or silently migrating old runs.
