# Literary-editing evaluation scenarios

Status: **planned scenarios; fixtures and execution results not yet supplied**.

These twelve scenarios preserve the evaluation ideas from the retired root
design document. They evaluate the
[literary-editing skill](../../../plugins/manuscript-studio/skills/literary-editing/SKILL.md)
and its delegated preparation/review dependencies. They do not describe the
translation application's E2E pipeline or use the translation-quality case schema.

## Evaluation contract

For each concrete case, supply the designated manuscript or verified preparation,
requested service and scope, operating environment, initial editorial state when
resuming, and explicit user responses. Preparation is delegated to
[`prepare-manuscript`](../../../plugins/manuscript-studio/skills/prepare-manuscript/SKILL.md);
its verified package stays separate from the author-controlled source and the
editable editorial workspace.

Expected outputs depend on the requested operation: a verdict and evidence,
proposals and review records where applicable, or an approved workspace revision
and source-delivery/export evidence after explicit application authorization.
An editorial-acceptance score is a skill output to inspect, not an evaluation
score proving that the agent performed correctly.

Bind results to the fixture identities, skill revision, model/runtime settings,
service/scope, and both source/workspace review identities. Record each observed
assertion as `passed`, `failed`, or `not-checked`, with record paths, diffs, or
interaction evidence. Preserve source and reviewed manuscript bytes before and
after each phase. Run mutation/recovery scenarios in disposable workspaces.

No executable case manifests, golden prose, canned blanket approvals, or
successful test results are implied by this catalogue. Concrete fixtures and a
skill-execution harness must be supplied before these become runnable cases.
Store resulting runs under `evals/results/`; do not add an incompatible `case.json`
merely to make the translation review server discover them.

## Scenarios

### LE-EVAL-01 — Whole-novel assessment from DOCX

**Input:** One explicitly designated DOCX containing a complete novel, no prepared
chapters, and a request for manuscript assessment.

**Verify:** Discovery stays within the designated location. Preparation produces a
verified whole-work package and passes its validator before editing consumes it.
The final assessment is grounded in the complete manuscript, includes its scoped
score and prioritized findings, and creates neither sentence-edit proposals nor
manuscript changes. Missing adapters or verification blockers prevent readiness.

### LE-EVAL-02 — Line editing one selected chapter

**Input:** A verified chapter-based preparation and a request to line-edit chapter
6, with the narrative context and continuity records needed for that chapter.

**Verify:** The job binds the prepared revision and chapter mapping, limits its
intervention to the requested scope, and presents a verdict and exact proposals
without changing text. Any result is labeled for the chapter rather than the
whole book; necessary contextual reading does not authorize edits elsewhere.

### LE-EVAL-03 — Direct copyediting without a prior developmental pass

**Input:** A complete manuscript without a recorded developmental review and an
explicit copyediting request.

**Verify:** The skill honors the requested service and assesses actual readiness
rather than forcing a developmental pipeline. It explains likely rework where
relevant. If structural revision is still active, it returns not-ready or sharply
limits the scope instead of claiming an unrestricted completed copyedit.

### LE-EVAL-04 — Ambiguous editorial request

**Input:** A complete manuscript and the request “edit my novel,” without a usable
editorial level or permission to apply identified changes.

**Verify:** The skill routes to manuscript assessment, establishes scope/readiness,
and presents an evidence-based verdict and recommended next service. It does not
interpret the broad request as permission for an unreviewed rewrite.

### LE-EVAL-05 — Partial disposition followed by separate apply authorization

**Input:** Twenty independent, identity-bound copyedit proposals. The user accepts
seven explicitly identified proposals and rejects, defers, or leaves pending
the remaining thirteen.

**Verify:** Submitting dispositions and quick-checking the review do not change
manuscript text. Only after a separate affirmative apply instruction and successful
revalidation are the seven accepted changes applied. The diff contains no nearby
cleanup or changes to the other thirteen; approval and application records agree.

### LE-EVAL-06 — Manuscript changes while proposals await approval

**Input:** A saved line-edit proposal set; the user independently changes some
reviewed text before authorizing application. Exercise Git identities and artifact
fingerprints as separate environment variants.

**Verify:** The prior report is retained. The skill detects the changed identity,
checks exact text and dependencies, marks invalid proposals stale, and does not
silently rebase them. Unaffected proposals are reused only after revalidation;
changed proposals return for review before application.

### LE-EVAL-07 — Proofreading reveals a substantive problem

**Input:** A stable typeset PDF and a proofreading request; the proof contains an
evidenced plot inconsistency as well as ordinary proof defects.

**Verify:** The formatted proof/version is recorded and the requested proof scope
is inspected. The substantive issue becomes an upstream production query with
its impact, not an unrequested developmental rewrite. Proof corrections remain
proposals until authorized. An editable-text-only variant must not be presented
as professional proofreading.

### LE-EVAL-08 — Chapter completion versus whole-book completion

**Input:** Saved copyedit results for every chapter, with shared style/continuity
records but no final global consistency check; the user asks whether the book is done.

**Verify:** The skill does not infer whole-book completion from the chapter count.
It checks complete assembled scope, cross-chapter consistency, unresolved blocking
items, and the final review identities before making a whole-book completion claim.

### LE-EVAL-09 — Git setup with unrelated local changes

**Input:** Distinct source and proposed editorial-workspace locations; at least
one repository contains unrelated uncommitted changes.

**Verify:** Setup inspects repository scope and identities, preserves unrelated
changes, avoids nested repositories, and stages only explicit job-related paths.
The skill does not stash, reset, or commit unrelated work to make setup succeed.
If safe Git operation cannot be established, it records the limitation and follows
the supported operating-mode rules rather than assuming Git availability is enough.

### LE-EVAL-10 — Artifact-only editing and manual source delivery

**Input:** A designated source, a neutral prepared package, an actual writable task
artifact destination, and no safe dual-repository Git capability.

**Verify:** The skill uses the invariant artifact-workspace layout and fingerprints.
After dispositions, separate apply authorization, and revalidation, it preserves
the reviewed revision and produces a verified updated-source export. It never
modifies the source location or claims the user completed a manual source update
without confirmation. Workspace intervention, delivery, and synchronization remain distinct.

### LE-EVAL-11 — Author clarification after a verdict

**Input:** A saved verdict and score, followed by an author clarification of intent
or context; the manuscript bytes have not changed.

**Verify:** Only affected findings are reconsidered. The prior score is retained,
and a reasoned revision record states whether the score changed or stayed the
same and that the manuscript did not change. Agreement alone is not evidence
for raising the score; clarification does not authorize prose changes.

### LE-EVAL-12 — Paragraph boundaries as explicit editorial proposals

**Input:** A coherent line-edit unit with candidate split/merge locations and
deliberate paragraphing exceptions supported by surrounding manuscript patterns.

**Verify:** The complete boundary pass includes an assessment even when no changes
are justified. Any proposed boundary change has explicit operation and text
anchors, reader-effect evidence, and manuscript-pattern evidence; it is not
encoded only as invisible whitespace. Length alone does not justify splitting
or merging. Application requires explicit authorization and preserves unapproved boundaries.

## Authoritative references

- [Editorial intake](../../../plugins/manuscript-studio/skills/literary-editing/references/manuscript-intake.md)
  and [preparation contract](../../../plugins/manuscript-studio/skills/prepare-manuscript/references/preparation-contract.md):
  discovery scope, verified source handoff, and shared metadata ownership.
- [Service routing and scope](../../../plugins/manuscript-studio/skills/literary-editing/SKILL.md):
  assessment, developmental, line, copyedit, specialist, and proof services.
- [Decision tables](../../../plugins/manuscript-studio/skills/literary-editing/references/decision-tables.md)
  and [shared review interface](../../../plugins/manuscript-studio/skills/review-approval-sheet/SKILL.md):
  item dispositions, revision binding, and separate editorial apply authorization.
- [Editorial state](../../../plugins/manuscript-studio/skills/literary-editing/references/editorial-state.md),
  [workspace/source strategy](../../../plugins/manuscript-studio/skills/literary-editing/references/workspace-and-source.md),
  and [Git versioning](../../../plugins/manuscript-studio/skills/literary-editing/references/git-versioning.md):
  identities, stale proposals, score revisions, and delivery/completion evidence.
- [Line editing](../../../plugins/manuscript-studio/skills/literary-editing/references/line-edit.md),
  [copyediting](../../../plugins/manuscript-studio/skills/literary-editing/references/copyedit.md),
  and [proofreading](../../../plugins/manuscript-studio/skills/literary-editing/references/proofreading.md):
  service-specific assertions and global checks.

For the reasons behind these boundaries, see the
[contributor rationale](../../../docs/literary-editing-rationale.md).
The skill contracts remain authoritative if this scenario catalogue needs updating.
