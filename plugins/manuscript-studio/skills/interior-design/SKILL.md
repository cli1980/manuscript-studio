---
name: interior-design
description: Propose book interior designs from verified manuscript preparation, metadata, literary reading, and author preferences. Use for typography, layout, and interior-design briefs, standalone or as a reusable component. Produces a structured proposal rather than formatted documents.
---

# Interior Design

Turn an unchanged prepared manuscript into a **proposed interior-design form**.
Use this skill standalone or as a reusable component. Document production and
human approval are separate from proposal authoring.

## Input and freshness

Use a ready package under the
[preparation contract](../prepare-manuscript/references/preparation-contract.md):
work.json, current revision manifest, ordered Markdown units, and assets.
Request preparation if absent/stale. Preserve its words, order, identity and
special forms; keep source files unchanged.

Read the [metadata rules](../prepare-manuscript/references/manuscript-metadata.md)
and [proposal contract](references/proposal-contract.md). Bind the exact work
record, manifest, ordered unit hashes, scope and language.
Hash the accessible input bytes.

Reuse supplied author intentions, existing reading and prior proposals. Reuse
reading only for its bound text/scope; otherwise read the available prepared
units and include fresh analysis. Do not treat a source-language synopsis as a
reading of changed translated text, or a sample as the whole book.

Keep supplied facts separate from inference. Reuse computed extent rather than
asking users to retype word counts. Do not infer ISBN, imprint, authorship,
publishing plans, brand, personal demographics or future series titles. Unknown
facts remain null/empty. Source references do not authorize arbitrary filesystem
access, private-account browsing, uploading text, or copying protected designs.

## Read and propose

1. Summarize essence, genre/subgenre, synopsis, themes, textual voice, mood/vibe,
   audience and structure with evidence and uncertainty. Distinguish inferred
   readership from the author's stated positioning.
2. Reuse optional series direction, preferred examples and what is liked,
   important excerpts, things to avoid and expected revisions. Do not reproduce
   a service-business questionnaire or collect contact details.
3. Separate edition purpose (submission, editorial-review, print-ready) from
   production targets. Incorporate a selected vendor profile's matching binding
   variant using the [profile contract](references/vendor-profiles.md).
4. Propose one coherent system: geometry/measure, primary and fallback families,
   type scale/leading, paragraph rhythm, hierarchy, chapter openings, scene
   breaks, navigation, running heads and folios. Use explicit units. Submission
   fiction should not acquire a TOC by default. Specify header/footer distances,
   default/even/first variants, explicit paragraph styles/alignment and content
   presets under proposal `/4`: `book-title`, `chapter-name`, `author`,
   `page-number`, or `page-x-of-y`. Use `custom` with an explicit template only
   when those choices do not fit; do not duplicate a preset with raw token text.
   None means an empty, unlinked part, not an empty paragraph or inheritance.
   Presets select content, not an automatic two-sided layout or font policy.
   Use complete unit-bound overrides
   where front matter or a chapter needs different furniture. Never invent
   missing title/author metadata or calculated page values. Widow/orphan values are
   non-negative integers. For DOCX, both zero disables the combined control;
   either nonzero enables it. Do not promise literal DOCX line thresholds.
5. Generate semantic design roles only for **whole paragraphs**, using the
   helper's paragraph catalog and chapter/paragraph hashes under the proposal
   contract. Consume verified paragraph annotations when available; keep new
   classifications local proposals for review. Do not generate inline roles,
   partial-paragraph ranges or overlapping assignments. Inline formatting comes
   only from the original Markdown markers; never add/remove/rewrite them to
   carry roles. Do not widen an inline distinction into a whole-paragraph role.
   Use an empty role list when ordinary body/heading styles suffice. Preserve
   special forms even when the requested producer cannot render them.
6. Temporary colors are evidence only if preparation captured their legend and
   occurrences. Do not assume DOCX color survived Markdown extraction.
7. Explain material choices with evidence. Ask only necessary author-input or
   design-choice questions; technical verification is not an author questionnaire.
   Cite verified evidence for font availability, embedding rights and vendor
   compliance; otherwise record these checks as unresolved.

## Save, validate, hand off

Save interior-design/interior-design-proposal.json in the designated project
workspace, or return an equivalent artifact if persistence is unavailable. Follow
[the schema](schemas/interior-design-proposal.schema.json); see the
[synthetic example](references/proposal.example.json).

Use Python with the skill's requirements.txt installed. From this directory, or
using the helper's absolute path:

```text
python scripts/validate_proposal.py --work /path/to/work.json --list-paragraphs
python scripts/validate_proposal.py PROPOSAL.json
python scripts/validate_proposal.py PROPOSAL.json --work /path/to/work.json
```

First obtain the catalog for the exact ready preparation; copy paragraph indices
and hashes rather than counting lines or guessing anchors. Proposal validation
checks shape/references; --work additionally checks local preparation/source
hashes, whole-paragraph identities and reading excerpts. No command verifies
external references, fonts, vendor readiness or approval.

Return the JSON artifact, concise rationale, unresolved questions and exactly
which validation ran. If execution is unavailable, label the artifact unvalidated.
Optional Markdown is derived, not authoritative. Increment revision for a new
proposal and preserve saved human choices.
