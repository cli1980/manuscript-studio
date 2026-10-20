# Literary editing: design rationale

This contributor note explains the reasons behind the editing skill's boundaries.
It is not an execution specification. The current
[literary-editing skill](../plugins/manuscript-studio/skills/literary-editing/SKILL.md)
and its linked references define the procedures, schemas, and completion rules.
Change those sources when changing behavior; avoid copying their instructions here.

## Review and intervention are separate

A useful editorial diagnosis can end without changing the manuscript. Keeping the
verdict and proposals separate from application lets the author weigh alternatives
and accept only the changes that serve the work. Recording dispositions separately
from apply authorization also supports review and discussion without accidentally
granting permission to rewrite.

See [decision tables](../plugins/manuscript-studio/skills/literary-editing/references/decision-tables.md)
and [editorial state](../plugins/manuscript-studio/skills/literary-editing/references/editorial-state.md)
for the actual authority and persistence contracts.

## Editorial sequence informs readiness, not compulsory routing

Developmental decisions can invalidate sentence-level work, but a user may still
have a valid reason to request copyediting or another service directly. Separating
service selection from readiness allows the skill to explain limitations without
silently replacing the requested service. Whole-book judgments require different
evidence from a chapter-level intervention; processing every chapter does not
itself establish consistency across the assembled book.

The skill's routing table and service references own these scope decisions.

## Preparation and editing have different responsibilities

A neutral verified source package can serve several skills without making an
editor's working copy authoritative for all of them. Separating preparation from
editorial intervention preserves extraction provenance and makes upstream changes
visible to dependent work.

The [preparation contract](../plugins/manuscript-studio/skills/prepare-manuscript/references/preparation-contract.md)
owns source discovery, extraction, and shared metadata. The
[editorial intake reference](../plugins/manuscript-studio/skills/literary-editing/references/manuscript-intake.md)
owns consumption of that package and binding it to an editorial job.

## Workspace completion and source synchronization are different outcomes

An approved working revision can be complete even when the author's source has
not yet been updated. Keeping those outcomes distinct makes artifact-only
environments useful without pretending they provide direct source synchronization.
The same separation preserves a valid workspace result when a Git source update
cannot proceed safely.

See [workspace and source strategy](../plugins/manuscript-studio/skills/literary-editing/references/workspace-and-source.md)
and [Git versioning](../plugins/manuscript-studio/skills/literary-editing/references/git-versioning.md).

## Prose improvement depends on the task's governing standard

Editorial choices should follow the work's intent and reader effect rather than
a universal preference for smoother or more conventional prose. This distinction
is especially consequential in translation: an English-only improvement may
change information, voice, or revelation relative to the source. General editing
is therefore not a mandatory stage of the translation workflow; its
source-grounded review remains with the translation skill.

See the [translation skill](../plugins/manuscript-studio/skills/literary-translation/SKILL.md)
and the application's [workflow architecture](../workflow/docs/architecture.md).

## Evaluation and history

The [editing evaluation scenarios](../evals/cases/literary-editing/README.md)
preserve the useful test ideas from the former root design document and align
them with the current contracts. They are planned skill-execution scenarios, not
completed evaluations or application E2E tests.

The former `literary-editing-workflow-design.md` is retained in Git history.
Its detailed instructions were retired because the maintained skill references
already define the behavior and the duplicate document had drifted.
