# Studio interface structure: design and decision record

**Origin:** roadmap's "UX enhancement - studio interface structure", recorded
2026-10-28; subsequent owner decisions through 2026-11-10.

**Status:** partially implemented design, not a new approval or implementation.

**Current baseline:** consult the [flow inventory](../README.md#flow-inventory).

This migration preserves design scope and historical decisions. Statements about
planned phases remain targets; "implemented" below reflects the original record,
not fresh end-to-end validation. Delivery priorities/status remain in the roadmap.
The engine and gate model do not change merely to restructure the interface.

## Original review findings (2026-10-28)

| Perspective | Fit then | Recorded gap |
| --- | --- | --- |
| Evolving page viewer | Partial | Whole chapter blocks, no paragraph alignment or accepted-version reader |
| Separate run inspector | Partial | Metadata/final acceptance forms still on run page; raw event timeline |
| Works explorer | Mostly | Mixed browsing/actions; flat files rather than workflow/version hierarchy |
| Unified approval GUI | Not at UI level | Six forms for one engine gate model |

Some gaps have since narrowed; this is a dated review, not today's defect list.

## Target interfaces and acceptance boundaries

### Unified decision panel

The engine already represents kind, optional bound text, optional sheet, commands,
closure, and receipt. Replace fragmented item/list/free-reply/chapter/metadata/
acceptance presentation with a shared frame:

- Header: what is being decided and why.
- Conversation: reviewer feedback and the agent's answer.
- Body by shape: item review for sheets, command buttons, feedback box,
  document review, sample poll, metadata fields, choices, or final acceptance.
- Consistent closure and irreversible-action treatment, without changing each
  gate's required semantics. Metadata and acceptance keep specialized bodies.

Current mapping: [SC-06](../screens/decision-panel.md). Shared components exist;
this does not mean every gate already has identical layout or closure.

### Separate run inspector

The intended inspector is status/control only: stage/chapter progress, errors,
controls, and readable decision history from receipts (already summarized in
accepted `run.json` records), not raw events alone. Decisions move to the reader.
Current [SC-04](../screens/run-management.md) still hosts formatting gates.

### Works explorer

Browse workflow -> version -> files, reusing the format panel's `run.json` and
`manifest.json` preview. Organize work details into overview/metadata, versions
(including formatting/downloads), runs, and library/publication log. Add
accepted-version downloads, original-document preview, and metadata-version
comparison. Intake remains on the Works list.

Current [SC-02](../screens/work-details.md) is a flat library/publication list
with a formatting version preview, not the full target explorer.

### Evolving page viewer

Use a document model of prepared paragraphs and per-stage versions, numbered
as in the passage map. Select content from a run in progress or accepted
`<workflow>/vNNN` version. Keep reading layout independent of decision logic:
aligned source/target, editing diffs, single-language reading, and sheet-item
location highlighting should not require rewriting gates.

Target acceptance: the same panel presents every human decision; the inspector
has no decision forms; accepted versions are browsable/previewable/formattable/
downloadable; the viewer aligns source/output by paragraph for run and accepted
version content and highlights each reviewed item. Current side-by-side panes
and chapter links do not already satisfy all of this.

## Recorded owner decisions

### Front matter and shared metadata (2026-10-28; `d9896c5`)

Every prepared work begins with exactly one front-matter unit split verbatim
from the source: pre-chapter material and at least its title heading. The skill,
validator, workflow/studio fixtures, and evaluations enforce that contract.
The metadata gate attaches to this unit while the record stays shared/work-level.
Both editing and translation use ordinary chapter routing; the original change
required restarting unfinished runs and landed after the referenced live run.

On 2026-11-10 the owner replaced "missing title stops and asks" with title
precedence: metadata title, source document title property, then filename.
Preparation supplies the opening heading and records `supplied_title` with
text, basis, and evidence; the validator checks the match. The viewer and
metadata review disclose it. A corrected title takes effect after preparation
restart, not a direct chapter edit.

### Front-matter document reviews and translation brief (2026-11-03)

Workflow templates may declare `"front_matter": true` stages with workspace
documents and an exact approval command. Translation's brief follows metadata:
the agent derives `glossary.md` and `voice.md` from the whole prepared manuscript;
the reviewer sends corrections or `approve brief`. Approved files seed every
chapter. The owner selected feedback-only, not direct editing of those files.
The original brief implementation was committed locally and exercised by a
live run with delegated approval only; that is not human literary review.

On 2026-11-04 the owner added tryout samples: three randomly selected passages,
each translated three ways into `brief-samples.md`. The front-matter poll shows
originals beside variants; choose one per sample with optional reasons before
approving the brief. Samples guide voice, not mandatory future wording. They
carry forward with glossary/voice. Brief documents render as formatted Markdown
using the studio's shared Markdown renderer. These template/engine/skill/UI
changes required unfinished translation runs to restart.

### Per-run maximum passage size (2026-11-03)

The translation template defaults to 1,500 characters for Chinese/Japanese/Korean,
800 words otherwise. Work-details Advanced, the service, and CLI
`--passage-size` can set another value at launch. It is fixed for the run and
retained on workflow restart. Oversize exact ranges need map-exception approval;
the engine rejects a longer passage without it. The original record notes one
live story divided into three passages within the default, not broader sizing
or usability evidence. See [UF-05](../flows/UF-05-start-workflow.md).

### Frontend responsibilities and workflow behavior (2026-11-04/05)

Four interfaces were chosen: work explorer; cross-work workflow explorer with
workflow/status/needs-me filters; run management; chapter viewer. Shared widgets:
decision panel, Markdown/document viewing, metadata editor, status/progress tags.
Launch is available from both explorers.

Each workflow defines page behavior in
[workflows.ts](../../../studio/frontend/src/workflows.ts). Translation lands and
decides in the viewer. Editing follows it through `ChapterViewerWorkflowUI`,
with pass/whole-book decisions at the end of the content column. Formatting
has no chapter link and keeps decisions on the run page until preview exists.
The 2026-11-05 editing/viewer decisions were described as uncommitted at that
time; current source mapping is separate from that historical label.

The shared viewer/panel/feedback widget should not own workflow-specific text
or gate kinds. WorkflowUI supplies `panes()`, `decisionCopy()`, `awaitingLabel()`,
`stageVerb()`, `afterReply()`, and agent name. Translation has original/translation
panes and draft comments; editing has the current text pane. The shared decision
slot replaced translation-only chapter approval.

### Placement and shared feedback (2026-11-05/08)

The 2026-11-08 owner request places every decision after its reading area:
chapter gates below that chapter, whole-book jobs/pass choices/final acceptance
at the content column's end, scrolled into view once. Before chapters exist,
the decision can be the only content. This replaces top placement and the
translation-consistency exception.

The 2026-11-05 shared `AgentFeedback` choice covers sheets, chapter approval,
editorial reviews, apply authorization, and questions: conversation, item review
for sheets, otherwise commands and feedback/inline comments. Separate list-sheet
and free-reply forms were removed. Brief document review, sample poll, metadata,
pass choices, and final acceptance retain specialized bodies.

Inline comments (2026-11-04, recorded committed locally) use Recogito on the
translation, not the original, and on brief documents. Drafts remain in the
browser until sent and retain quote/range/paragraph context for possible future
alignment. They are ordinary feedback to the unchanged engine.

### Formatted output becomes a work (2026-11-05)

Formatting is an optional step after accepted output; completion automatically
creates a DOCX-source work linked to origin/run. Derive rather than blindly copy
metadata: translated front-matter title, language-neutral type/form/audience/
series facts and relationships, contributors for review, and original language.
Original-language free text starts empty for new preparation to infer.
The original record called hand-off committed locally and derived metadata
uncommitted. The mechanism covers linkage of a formatted translation that is
subsequently edited; it does not settle all arbitrary source-work linking.

## Recorded implementation phases and remaining targets

| Phase | Recorded design / status | Current qualification |
| --- | --- | --- |
| 1 | Implemented/committed 2026-11-04: viewer landing, status/problem links, pre-chapter questions, final acceptance, run-page links rather than chapter gate forms | Present for chapter-based workflows; formatting is an exception |
| 2 | Planned: selectable Whole book after last chapter; chapter API serves `_whole` material/status; WorkflowUI `wholeBookPanes()` | Not a selectable current route; needed to give developmental/consistency material its own reading page |
| 2b | Planned: move remaining workflow IDs/gate checks from Chapters.tsx to neutral WorkflowUI hooks such as `wholeBookLabel()`, `statusNotice(run)`, `extraPanels(chapter)` | Current viewer still has translation-specific labels/banner/applied-fixes presentation |
| 3 | Planned: keep formatting gates on run page until preview, then a Formatted document reader entry sharing the decision panel | No current formatted-page reader/gallery |

Phase 2b acceptance: no workflow IDs or gate kinds in the generic viewer, with
unchanged translation/editing rendering. Phase 2 requires a small web-API addition
because the chapter endpoint does not provide a whole-book reading document.

The original suggested order was unified panel, inspector, version explorer,
then paragraph-aligned viewer (largest), with frontend/web-API changes intended
not to invalidate running workflows. This is preserved rationale, not a new
priority commitment. Editing now has a shared viewer, but the whole-book/diff
targets and M4's verification gaps remain.
