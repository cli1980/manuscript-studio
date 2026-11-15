# Semantic roles: preparation and downstream hand-off

**Status:** owner-confirmed scope, proposed technical contract; not implemented.
**Requirements:** IDP-R10 through IDP-R12 in the
[interior design](interior-design-and-production.md) register.

## 1. Ownership

Semantic roles are manuscript data, not formatting instructions.

- Preparation owns source structure, role definitions, and bound occurrences.
- Editing/translation own the mappings to their changed output text.
- Interior design consumes those roles and proposes named visual styles.
- The producer implements approved styles; it cannot invent, drop, or repair
  semantic annotations silently.

For example, `letter` or `alternate-narrator` describes narrative function.
Italic, indentation, font family, and print color belong to a separate style map.
A temporary blue marker is source evidence, not the semantic identifier or final
print color. Ordinary italics alone do not establish a letter or alternate voice.

## 2. Proposed preparation artifact

Add a revision-scoped `semantic-roles.json` sidecar, referenced by path/hash from
the preparation manifest. This requires coordinated changes to the current closed
preparation schemas and validators, not an undeclared extra JSON file.

Proposed information:

- A role registry: stable `role_id`, display name, kind, narrative function,
  evidence, classification provenance, and review state.
- Occurrences: stable `annotation_id`, role ID, chapter ID/hash, exact UTF-8 byte
  range/hash, optional parent annotation, and source evidence.
- Inventory/coverage state and unresolved classifications. Distinguish an
  explicitly checked empty inventory from an inventory never performed.

Role identity survives transfer; a changed target occurrence gets its own
annotation ID and source-lineage references. Scope identities with the manuscript
lineage so independently created roles do not accidentally collide.

The sidecar binds unit bytes, not its parent manifest hash: the manifest already
hashes the sidecar. Keep receipts outside that hash cycle.

Source preparation remains immutable. Annotation changes create a new revision,
reusing unchanged content bytes where appropriate; they do not silently mutate a
verified package or grant editorial authority.

### Annotation/modification tools

Provide a preparation-owned helper, usable by both skill and workflow, with
operations equivalent to:

- `inspect`: show roles, occurrences, provenance, and unresolved mappings.
- `propose`: add/change a role or bind/rebind an occurrence against an expected
  revision and unit hash; record the actor and evidence.
- `validate`: check schema, IDs, role references, bounds, UTF-8 boundaries,
  hashes, scope/coverage, and declared nesting policy.
- `apply`: atomically create the next annotated preparation revision using an
  expected-current-revision/hash guard; record authorized dispositions.

These are proposed operations, not installed CLI commands. A metadata edit tool
alone is insufficient: occurrence locations and role classification need
revision-bound modification. Agents may propose classifications, but cannot
manufacture human review receipts or claim uncertain classifications confirmed.

## 3. Preparation workflow changes

Extraction must inventory semantic distinctions and capture existing structural
evidence. When an author supplies a color legend, capture the complete relevant
passages before Markdown conversion loses the marker; do not infer a legend
from color alone. Missing/ambiguous information remains explicit.

The workflow presents consequential ambiguities with their source excerpts,
routes corrections through the shared annotation helper, pins the resulting
sidecar in checkout/snapshots, and exposes it to downstream requests.

Extraction readiness, annotation coverage, and human confirmation are distinct.
Do not add an unconditional new approval gate or redefine preparation readiness
without reviewing IDP-D08. Missing role support must not masquerade as a verified
empty role inventory or silently permit a semantically flattened final edition.

## 4. Translation transfer

Source byte offsets cannot be copied to translated Markdown. Stable role meaning
can transfer, but target spans must be bound to actual final target bytes.

For each source annotation, the translation operation returns a mapping:

```text
source_annotation_id
  -> target annotation(s): same role_id, target unit/hash/range/hash
  -> or an explicit unresolved mapping with reason
```

Allow one-to-many and many-to-one correspondence where translation changes
paragraph boundaries. A missing mapping is not permission to omit source text.
Proposed omissions require the existing literary decision authority, not merely
a role-transfer disposition.

The workflow must:

1. Include the pinned role registry/source occurrences in chapter and passage
   requests. Passage splitting must preserve role context and identify spans
   crossing passage boundaries.
2. Collect target occurrences and transfer provenance alongside translated text.
3. Validate IDs, exact source/target identities, target bounds/hashes, declared
   nesting, and coverage of all source annotations.
4. Present unresolved/uncertain transfers beside chapter review. Hash validation
   cannot prove that the translated passage has the right semantic role.
5. Rebind or reopen affected target annotations after revisions, alternate
   variants, whole-book consistency patches, or chapter restart.
6. Publish accepted text together with a pinned annotation/transfer artifact;
   carry both when preparing the translated output for formatting.

Temporary in-band role markers, if used during drafting, are transport details:
they must never leak into final literary text or replace the canonical sidecar.
Do not add/remove Markdown wrappers simply to carry metadata.

## 5. Editing and zero-pass behavior

With zero editing passes, reuse the matching preparation annotation revision.
No editorial agent is needed to pretend roles were transferred.

With edits, rebase untouched ranges only when an exact edit map makes that safe.
Edits intersecting annotated passages, changing boundaries or splitting/merging
units require revalidation and potentially renewed review. Never guess locations
with a text search that could match repeated passages.

Retained, transformed, newly introduced, and explicitly removed annotations need
accounting. Removing an annotation is not authority to remove its text, and
removing text does not justify silently losing its annotation history.

## 6. Interior-design consumption

Interior proposals reference canonical role/annotation identities and the
annotation-artifact hash, then map roles to proposed style IDs. New classifications
suggested by the designer return to preparation's proposal/review mechanism;
the designer does not become a second source of canonical manuscript semantics.

The current proposal-v1 schema only has proposal-local role IDs and byte ranges.
It does **not** yet implement canonical annotation references or translation
transfer. Its schema, example, helper and tests must change together with the
preparation/downstream contracts; do not imply that today's span checks implement
this hand-off.

## 7. Required implementation surfaces and evidence

- Preparation skill instructions, central work/revision schema definitions,
  annotation helper/validator, and extraction/verification tests.
- Shared PreparedManuscriptEngine checkout, snapshots, source verification,
  protected-input checks, publication and output-preparation materialization.
- Editing/translation skills, domain records, runtime result contracts, passage/
  chapter gates, consistency-patch application and restart/recovery.
- Proposal schema/helper and native intake/producer role-to-style consumption.

Tests must include an ordinary manuscript with verified no-special-role coverage,
color-coded and nested passages, repeated text, Unicode ranges, annotations
crossing passage boundaries, translation expansion/reordering/splits, changed
target variants, consistency patches, stale revisions, zero-pass reuse, and
publish/export/reprepare round trips without role loss or text mutation.

These checks are required evidence, not completed verification. No new
preparation manifest field, modification command, or transfer implementation
ships from this design document alone.
