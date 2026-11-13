# Runtime support and fallbacks

The plugin supplies instructions and helper scripts, not an execution engine,
Documents skill, office suite, browser, or inline-rendering capability. Product
names alone do not guarantee those capabilities. Check the active workspace
before promising an output or showing an approval interface.

| Environment | Supported path | Limits and fallback |
| --- | --- | --- |
| Codex CLI or desktop with accessible project files and Python 3.10+ | Script-backed preparation, review parsing, and literary workflows | Install skill dependencies as needed; inline review only if the active surface supports `::codex-inline-vis`. Otherwise use revision-bound text. |
| ChatGPT desktop/workspace with plugin support | Skills available through the enabled plugin and host tools | Local/Git marketplace availability, file writes, Python, and inline rendering vary by product and workspace. Probe capabilities, do not assume desktop means filesystem or inline support. |
| Browser chat with attachments but no execution tools | Analysis, drafts, and manually reviewable proposals | Reading GitHub is not installation. No claim of validated extraction, saved receipts, source modification, or rendered DOCX without the actual tools. Return proposals/specifications and explain missing validation. |
| Any host with an available Documents skill and its required construction/rendering/inspection tools | Approved Word/DOCX production and page-by-page visual verification | These are external prerequisites, not bundled dependencies. Missing Documents skill or render/page-inspection capability blocks generation. |

Preparation uses `jsonschema` and format-specific extraction dependencies listed
in its `requirements.txt`. Query research additionally needs browsing/search;
without it, draft reusable materials but label agent guidelines unverified and
do not claim a verified agent-specific package. Git is optional: without it,
return reviewable files/proposals rather than claiming a commit.

## Formatting fallback demonstration

**Request:** "Format this manuscript as a Word edition."

**Capabilities:** manuscript is readable; the Documents skill or its required
rendering workflow is absent.

**Required behavior:**

```text
Generation status: blocked-adapter
Missing capability: Documents skill and/or its required rendering and page inspection.
Available result: a proposed format-spec.md for your review.
No generated DOCX is claimed to be complete or visually verified.
Resume construction only in an environment with the required adapter and tools,
after the specification's explicit approval gate.
```

Keep the manuscript unchanged. Do not silently substitute an ad hoc DOCX builder,
skip visual QA, deliver an empty TOC, or interpret "continue" as approval.
Having Word or LibreOffice alone does not install the required Documents skill.

## Inline review and text fallback demonstration

Interactive sheets require Python to validate/render the saved JSON and a host
that can present `::codex-inline-vis{file="<basename>.html"}` from the active
thread visualization directory. A local HTML path or Markdown link is not that
surface. Do not assume ChatGPT web or every Codex client implements it.

When inline presentation is unavailable or fails, state that fact and show the
same stable IDs, choices, required notes, binding, and saved revision in text:

```text
Approval sheet: format-demo
Revision: rev-1
Binding: manuscript fingerprint recorded in the saved sheet
FM001 | Body typography | approve / modify (exact replacement note required)
FM002 | Chapter openings | approve / modify (exact replacement note required)

Example user dispositions:
FM001: approve
FM002: modify - Use chapter headings without a page break.
```

This is an illustrative dialogue, not an approval receipt for a real manuscript.
For an actual saved sheet, use only its declared commands and IDs. Bind
disposition-only text explicitly to that active revision and run the same parser:

```text
python plugins/manuscript-studio/skills/review-approval-sheet/scripts/approval_review.py validate SHEET.json
python plugins/manuscript-studio/skills/review-approval-sheet/scripts/approval_review.py parse SHEET.json RESPONSE.txt --output RECEIPT.json
```

Reject stale identity/revision, unknown or duplicate IDs, missing required notes,
and blanket approval. A modification reopens or propagates work according to
the originating skill; it is not approval of its replacement. After the domain
saves all items resolved, obtain the separate final closure on the new revision.
If Python/parser access is also missing, present a non-authoritative proposal
and mark machine validation/persistence blocked; do not invent a validated receipt
or apply source changes.

See the [formatting skill](skills/format-manuscript/SKILL.md) and
[approval skill](skills/review-approval-sheet/SKILL.md) for authoritative gates.
