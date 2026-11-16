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
| Host with verified preparation and accessible manuscript text | Standalone or reusable interior-design proposal, with JSON validation when Python/jsonschema are available | No workflow run, orchestration UI, Documents skill, office renderer or inline surface is needed. The skill does not construct documents or record design/page approval. Native intake/production integration is separate work. |

Preparation uses `jsonschema` and format-specific extraction dependencies listed
in its `requirements.txt`. Query research additionally needs browsing/search;
without it, draft reusable materials but label agent guidelines unverified and
do not claim a verified agent-specific package. Git is optional: without it,
return reviewable files/proposals rather than claiming a commit.

## Interior-design boundary demonstration

**Request:** "Format this manuscript as a Word edition."

**Capabilities:** verified preparation is readable; document-generation tools
may or may not be present.

**Required behavior:**

```text
Available result: interior-design-proposal.json, status=proposed.
Validation: report shape-only or local-preparation validation accurately.
No DOCX/PDF is generated or visually verified by this skill.
Native design approval, production, and human page review are separate operations.
The new embedded GUI/production integration is not implemented by this plugin.
```

If preparation is missing, request it first. If Python is unavailable, label the
proposal unvalidated. Do not invoke a Documents skill or silently substitute an
ad hoc builder; having Word/LibreOffice does not expand this skill's authority.

## Inline review and text fallback demonstration

This applies to the other literary review skills, not to the proposal-only
interior-design skill.

Interactive sheets require Python to validate/render the saved JSON and a host
that can present `::codex-inline-vis{file="<basename>.html"}` from the active
thread visualization directory. A local HTML path or Markdown link is not that
surface. Do not assume ChatGPT web or every Codex client implements it.

When inline presentation is unavailable or fails, state that fact and show the
same stable IDs, choices, required notes, binding, and saved revision in text:

```text
Approval sheet: review-demo
Revision: rev-1
Binding: manuscript fingerprint recorded in the saved sheet
RV001 | Punctuation change | approve / modify (exact replacement note required)
RV002 | Sentence clarity | approve / modify (exact replacement note required)

Example user dispositions:
RV001: approve
RV002: modify - Retain the original wording.
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

See the [interior-design skill](skills/interior-design/SKILL.md) for its proposal
contract and [approval skill](skills/review-approval-sheet/SKILL.md) for literary
review gates.
