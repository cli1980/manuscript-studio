# Interior-design skill: author-brief refinement

**Status:** selected refinements are implemented in the proposal-only
interior-design skill/schema. Broader intake/production behavior remains proposed,
not implemented or approved in full.

**Design:** [interior design and production](interior-design-and-production.md),
especially component 1 and requirements IDP-R01 through IDP-R05.

## Source and authority

The owner supplied `INTERIOR-DESIGN-brief-for-AUTHOR-2026 (1).docx` on 2026-11-13
as a reference for refining the converted skill. Its document heading is
"INTERIOR LAYOUT DESIGN & TYPESETTING BRIEF".

Source SHA-256:
`491dd8959362733c79ec7534dddefc11c3bd995dbbf843a451648e70ab5728fa`.

The reference remains outside the repository in the owner's Downloads folder.
This document records its design implications, not a redistributed copy. The
mapping below does not turn every questionnaire field into an approved product
requirement. This is an author/designer brief, not a vendor compliance standard.

## 1. Adapt the brief, do not reproduce a questionnaire

The reference is designed for an external studio that does not read the whole
manuscript. Our skill has verified prepared text and agent reading. It should
prefill supported literary and structural observations, disclose uncertainty,
and ask the author only for missing intentions and consequential choices.

Keep three information layers distinct:

1. **Author brief:** supplied intentions, production goals, references, and
   constraints. Agents cannot fabricate author/business facts.
2. **Manuscript reading:** text-bound analysis with evidence and uncertainty.
3. **Interior-design proposal:** a proposed typographic/layout response, with
   rationale linking choices to the first two layers.

The GUI reconciles these with vendor/capability constraints and records approval.
The skill neither generates production files nor approves its own recommendations.

## 2. Field mapping and ownership

| Reference area | Proposed treatment | Authority / handling |
| --- | --- | --- |
| Project contact, collaboration invitation, quotation and extra fees | Exclude from the interior-design contract | Service-business administration, not document layout; no ActiveCollab integration or email collection is implied. |
| Publisher/imprint and ISBN | Optional supplied publication facts | Do not infer, assign, or insert into prose. Adding a copyright/credits page requires explicit content authority. |
| Word count | Reuse preparation extent | Preserve revision, language, scope, and counting method; do not ask the user to retype a computed value. |
| Target page count | Optional author preference | A soft design target unless explicitly controlling; actual count comes from rendering. No omission, forced compression, or promise of an exact count. |
| Publishing format, platform, binding, trim | Capture requested production targets | Resolve through versioned vendor/product profiles. IngramSpark remains first; references to KDP, hardcover, ebook, or audio do not add implementation scope. |
| One-sentence essence, genre/subgenre, themes, synopsis, message | Prefill from metadata and reading, with provenance | Separate author intention from inferred interpretation. A synopsis is analysis, never manuscript content. |
| Tone/voice and mood/vibe | One normalized reading section | The source repeats tone questions; avoid duplicate conflicting fields. Distinguish textual voice from desired visual mood. |
| Symbols, characters, important excerpts | Optional prioritized design evidence | Use prepared unit IDs and text hashes/ranges. Do not invent symbols, illustrations, or a need to insert them into the book. |
| Series/collection direction | Optional author brief | Consistency versus controlled variation, supplied prior design, planned titles, and recurring motifs. Do not invent future-title facts. |
| Manuscript readiness and expected revisions | Capture author expectations separately from preparation readiness | Verified preparation does not mean editorial finality. Production still pins exact text; any later correction can invalidate pagination and page approval. |
| Parts, chapters, prologue/epilogue, appendices/back matter | Derive structural inventory from preparation | Preserve source order, roles, and identities; never create missing components merely to complete the brief. |
| Distinct narrative/text types | Explicit semantic role inventory and proposed style mapping | See section 3; do not rely on transient colors as canonical content semantics. |
| Broad changes in time, pace, voice, or atmosphere | Optional author notes plus reading evidence | Propose restrained supporting treatments; do not infer that every tonal change needs a new style. |
| Brand, goals, selling points, audience, comparable titles | Optional supplied positioning plus separately labeled analysis | Do not infer personal demographics, commercial intentions, endorsements, or contents of inaccessible external books. |
| Preferred samples, typography/layout feel, things to avoid | First-class author preferences and constraints | Record references and what is liked/disliked; do not copy a reference design or assume rights to assets/fonts. |
| Cover design and launch/branding support | Keep outside production scope | May be noted as external context; no cover, marketing, ordering, or commercial service workflow is added. |

## 3. Important refinement: semantic text roles

The reference's strongest structural contribution is a distinction between
ordinary body text and passages such as letters, journals, messages, poems,
transcripts, quotations, documents, alternate narrators, sidebars, and inserts.

Introduce a proposed `text_roles` collection:

- Stable role ID and human-readable name.
- Narrative function and heading/body classification.
- Prepared-text occurrences with exact scope/bindings.
- Evidence/source: author supplied, preparation captured, or agent proposed.
- Proposed semantic style and capability/verification status.

Keep source inventory, inferred classification, and approved presentation separate.
A repeated role should map consistently to a named style; isolated one-off
formatting must not replace the role system.

### Color markers are optional source evidence, not final styling

The brief asks authors to color-code complete passages and states that these
markers are temporary. Do not make coloring or re-uploading a requirement.

The current Markdown preparation contract does not establish a general
color-to-semantic-role mapping. If a source uses such markers, preparation must
capture an explicit legend and bound occurrences in a compatible annotation
contract, or surface the unresolved mapping for review. Never assume colors
survive DOCX-to-Markdown extraction or let the design skill recover lost ranges
by guessing.

Any preparation extension needs its own schema/validator review; do not silently
add unsupported fields to existing manifests. Record temporary marker semantics
separately from meaningful source emphasis/color. Only known temporary markers
are removed from presentation, never the passage itself.

The producer must reject unsupported roles/treatments rather than flatten poetry,
discard inserts, or claim that a role inventory means the builder can render it.
The broad inventory does not expand the first renderer's supported-content scope.

## 4. Refined proposal-form groups

Recommended output groups for `interior-design-proposal.json`:

1. **Identity and evidence:** prepared revision, consumed metadata/reading hashes,
   author-brief revision, source references, uncertainty, and proposal revision.
2. **Edition brief:** purpose, requested production target, supplied imprint/ISBN,
   desired trim/page-count direction, and manuscript-change expectations.
3. **Reading and visual direction:** essence, genre, synopsis, themes, voice/vibe,
   audience, important excerpts, and a concise interior-design rationale.
4. **Design system:** geometry, type families/fallbacks, sizes, leading, paragraph
   model, hierarchy, chapter openings, scene breaks, navigation, and page furniture.
5. **Semantic role/style map:** body and special text roles with occurrence
   references, proposed treatments, and unsupported/unresolved cases.
6. **Series and preferences:** inherited design rules, allowed variation,
   references/likes, and things to avoid.
7. **Decisions and gaps:** consequential alternatives, missing author information,
   capability conflicts, and exactly which choices need confirmation.

Each material recommendation should state its basis and effect, not merely a
numeric value. For example, a leading choice can cite sustained-reading density
and preferred visual rhythm; it must not assert a guaranteed page count.

The proposal form can reference the brief/reading rather than copying every
marketing or literary-analysis field into the production specification.
Only approved presentation values and necessary content/profile bindings belong
in the effective specification consumed by the deterministic producer.

## 5. Intake behavior and safeguards

- Reuse author-supplied data and existing confirmations; never overwrite them
  with model inference. Surface disagreements instead.
- Distinguish optional author context from required production values. An absent
  brand, ISBN, comparable title, or series plan must not trigger a generic intake
  questionnaire or block an otherwise supported editable-document build.
- Treat a stated publishing format as intent, not proof that its vendor profile
  or renderer is implemented. Unsupported targets remain visibly unsupported.
- Ask focused questions about unresolved author intent or semantic-role ambiguity,
  not facts already available in verified preparation.
- Do not require sensitive demographic/contact data for interior design.
  External links are references, not authorization to upload the manuscript.
- Selecting examples or entering an ISBN does not authorize inserting new pages,
  illustrations, ornaments, copyright language, or other literary content.
- Keep inferred choices proposed until the native GUI's explicit approval.

## 6. Review and verification implications

Proposed checks include:

- Complete reading-derived fields without fabricating author/business details.
- Computed extent retains its preparation scope and method.
- Repeated tone questions resolve to one consistent field group.
- Role occurrences bind actual prepared text and stale spans are refused.
- Temporary color markers are never assumed to survive preparation.
- Unsupported special forms and production formats are reported, not dropped.
- Page-count targets remain preferences until actual production checks run.
- A prior series design can seed a proposal without silently overriding new
  author choices or current vendor/capability limits.

The converted skill/schema/helper now implement structured reading, supplied
preferences, semantic roles and bound excerpts, with validation tests for shape,
provenance references and local preparation freshness. These checks do not prove
semantic reading quality or implement native intake, production, color-marker
extraction, vendor readiness, or every field in the source questionnaire.
No preparation schema is changed and no broader product scope is inferred.
