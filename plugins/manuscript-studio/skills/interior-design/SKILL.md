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
   fiction should not acquire a TOC by default.
5. Map semantic text roles to named styles using exact prepared ranges/hashes
   under the proposal contract. Consume verified preparation annotations when
   available; keep additional classifications as local proposals for review.
   Preserve special forms even when the requested production tool cannot render
   them.
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
python scripts/validate_proposal.py PROPOSAL.json
python scripts/validate_proposal.py PROPOSAL.json --work /path/to/work.json
```

The first checks shape and internal references. --work additionally verifies local
preparation/source hashes and bound occurrences. Neither verifies external
references, fonts, vendor readiness or approval.

Return the JSON artifact, concise rationale, unresolved questions and exactly
which validation ran. If execution is unavailable, label the artifact unvalidated.
Optional Markdown is derived, not authoritative. Increment revision for a new
proposal and preserve saved human choices.
