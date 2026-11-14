# UXD-001 - Intake, review, versioning, and controls

**Type:** migrated owner-decision record, not a new approval

**Provenance:** roadmap at `87b7737`; dates below retain their original meaning

**Current mapping:** [flows](../README.md#flow-inventory) and [screens](../README.md#screen-contracts)

## Intake and work boundaries

- In the 2026-10-26 M1 design review, every upload creates a distinct work,
  including identical files. Starting another workflow selects an existing
  work; only one unfinished run per work is allowed, including formatting.
- On 2026-10-27 the owner revised the original "workflow first, then upload"
  approach: intake and outcomes belong to Works; preparation is a run's first
  stage. Current direct launch is available on both work details and Workflows.
- Manuscript text is immutable outside workflow stages and gates. Prepared and
  output text are read-only in the GUI. Metadata is separately editable,
  versioned, and attributable. Fields relied on by a run can be locked.
- Preparation is repeated for a new run; published metadata is reused. The
  work library and publication log outlive runs.

## Metadata and front matter

The required metadata gate follows preparation. Edits increment record_revision,
retain snapshots, and record events; the current gate/revision must be confirmed.
Active agent turns reject conflicting edits; later edits do not retroactively
change the confirmed metadata used by a completed operation.

Front-matter placement, supplied-title precedence, brief documents, samples,
and maximum passage size are preserved in the
[studio design record](../designs/studio-interface.md). Those are current
interaction requirements, not a new manual manuscript editor.

## Approval versus discussion, application, and closure

- On 2026-10-28 the owner adopted implied closure for advice-type translation
  sheets and map exceptions, implemented with front-matter work in `d9896c5`.
  A submission resolving every item closes that advice sheet. Discuss/revise
  still creates a new revision.
- Chapter approval retains an explicit approval step: "Approve chapter" without
  proposed edits, or separate closure approving a chapter with its proposed
  edits when no later step displays the final text.
- Whole-book consistency retains separate closure (or explicit clean-review
  confirmation), receipt-backed decisions, and exact approved-fix verification.
  Coverage/proposals bind source/output hashes; candidate changes are checked
  before promotion. Restarting a chapter invalidates affected consistency review.
- On 2026-11-05 the same implied-closure rule was chosen for editorial reviews.
  Explicit apply authorization remains, showing what changes before the text is
  edited. A chapter with proposals needs review plus application, not an extra
  redundant review-closure step. Relevant template/engine changes required
  restarting unfinished editing runs; this is historical migration context.

## Editing pass selection

On 2026-11-05 the owner replaced the fixed developmental-line-copy sequence:
after preparation/metadata the user chooses developmental, line, or copy editing;
accepts each pass separately; and may choose any next pass, including repeating
the same one. Accepted text/editorial files become the next pass's input.
There is no discard: redo the stage before accepting its pass. Irreversible
final acceptance is offered after metadata and after accepted passes, including
zero passes, and is followed by automatic export. After finalization no pass
can run. See [UF-08](../flows/UF-08-edit.md).

## Finalization and versions

The original 2026-10-26 wording required re-upload after final acceptance.
The owner's 2026-10-28 correction permits a new run on the same work to publish
the next immutable version; a completed run never blocks that.
The accepted run's own chapter/stage/workflow remains nonrestartable.
The UI must warn before finalization, require explicit acknowledgement, and
retain a finalized/read-only banner. An engine-code update restricts unfinished
runs to reading and workflow restart; this is not a checkpoint rollback.

## Controls, source retrieval, and deferred downloads

- On 2026-11-10 the owner removed immediate turn interruption from M3.
  Across 121 measured turns, the recorded median was 1.4-1.9 minutes and the
  maximum 7; waiting avoids discarding the current turn. Pause therefore means
  pause after turn; Resume continues saved execution, not approval of a gate.
  Immediate interrupt remains a later possibility in the roadmap.
- Retry attempts the current saved step with a fresh agent thread; chapter,
  consistency, stage, and workflow restart have explicit scope/confirmation.
  Stop cancels permanently while retaining artifacts/history.
- On 2026-11-10 the owner chose original-upload download under its source name
  instead of an embedded original preview: prepared text is already readable,
  and the file itself opens faithfully in its native application.
- A Markdown export-download UI was removed from M3 on the same date.
  Accepted-version downloads and a source preview remain explorer targets.
  Local export paths and original-source download are not those future controls.

## Consequences and open work

No interface may reinterpret feedback as authorization, mutate accepted output,
or remove validation to make a diagram simpler. Proposed screen restructuring
must retain the contracts above. Historical live runs and human-vs-delegated
attribution remain recorded in the roadmap, not reclassified here as UX tests.
