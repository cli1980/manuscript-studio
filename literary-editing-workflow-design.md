# Literary Editing Workflow Design

Status: Draft for review
Scope: A reusable literary-editing skill suite for completed or substantially drafted book manuscripts

## 1. Design Goals

The workflow must:

1. Obtain and normalize the manuscript before evaluating it.
2. Infer the requested editorial service from the user's prompt when the intent is clear.
3. Route directly to the requested service instead of forcing the manuscript through every editorial stage.
4. Distinguish services that require the complete novel from services that can operate chapter by chapter.
5. Analyze first and modify nothing while producing the editorial verdict.
6. Represent proposed textual changes as a stable, reviewable diff.
7. Apply only changes the user explicitly approves.
8. Separate the author-controlled source location from the editorial workspace and preserve provenance across both.
9. Use the same workspace structure whether it is a local Git repository or an environment-provided artifact workspace.
10. When Git is available, manage workspace and source as two separate local repositories; otherwise never modify the source and deliver a verified updated-source export for manual application.
11. Attach a scoped 1-5 editorial-acceptance score to every verdict, with revision history when author clarification changes the editorial evaluation.

The workflow should follow professional editorial sequencing without requiring every project to use the full sequence.

## 2. Governing Principles

### 2.1 Authorial control

The author or authorized user owns creative decisions. The editor diagnoses, explains, recommends, queries, and proposes. It does not silently rewrite the manuscript.

### 2.2 Verdict before intervention

Every editorial service has two separate operations:

1. **Review:** inspect the manuscript and produce a verdict.
2. **Intervention:** apply only user-approved proposals to a working draft.

Completing a review never authorizes intervention.

### 2.3 Direct routing, not a mandatory pipeline

The professional sequence is useful for identifying dependencies:

`assessment → developmental edit → author revision → line edit → copyedit → layout → proofreading`

It is not a mandatory execution path. A user may request any applicable service directly. The skill must:

- honor a clear request;
- identify missing prerequisites or likely rework;
- label limitations in the verdict;
- avoid silently expanding the requested scope.

### 2.4 Larger decisions precede smaller decisions

When several editorial levels are requested together, perform higher-level diagnosis first. Do not spend time polishing sentences that a proposed structural revision would remove or substantially rewrite.

### 2.5 Separate source and workspace

The source location is the author-controlled draft. The workspace is the editorial working environment. Never use the source location itself as the workspace. Preserve the source baseline and record how each workspace revision derives from it.

Use one invariant workspace layout in both modes. In `dual-repository-git` mode, manage the workspace and source draft as two separate, non-nested local repositories. In `artifact-workspace` mode, use task/output artifacts as the workspace, identify inputs with fingerprints, and never modify the source location. After approval, create a verified updated-source export for the user to apply manually.
### 2.6 Evidence over prescription

Ground verdicts in manuscript evidence, authorial intent, intended audience, genre expectations, and the editorial brief. Treat story models and craft frameworks as optional diagnostic lenses, not universal rules.

### 2.7 Acceptance score and clarification

Every verdict includes a 1–5 editorial-acceptance score scoped to the selected service and reviewed material. The score measures acceptance at that editorial level, not publication probability, sales potential, or the author's worth.

Editorial conversation may clarify intent, audience, context, facts, or a defensible choice. Preserve the prior score and explain any revised score. A manuscript change is not required, and clarification may improve, reduce, or leave the score unchanged.

## 3. Manuscript Intake and Normalization

### 3.1 Locate or request the manuscript

Search the project, provided attachments, and connected sources for the requested manuscript. Confirm:

- work identity and title;
- author or responsible user;
- manuscript version;
- file type;
- whether the artifact is complete;
- whether it is an original manuscript, a translation, or a later revision;
- whether the user has supplied the scope they want reviewed.

If no manuscript can be located, ask the user to provide it. Do not produce a manuscript-level verdict from a synopsis or sample.

An isolated chapter may be reviewed only for services that allow chapter-level work. Any conclusion dependent on the complete novel must be labeled provisional or unavailable.

### 3.2 Inspect the source artifact

Determine:

- whether chapter divisions already exist;
- chapter order, numbering, titles, and section breaks;
- whether extraction preserves paragraphs, punctuation, italics, scene breaks, notes, and dialogue;
- whether OCR, encoding, missing-page, or duplicated-text problems exist;
- whether front matter, back matter, footnotes, images, or tables belong to the editorial scope.

### 3.3 Normalize without editing

If the manuscript is not chapter-separated:

1. extract the text with an appropriate document or PDF workflow;
2. identify real chapter boundaries from headings and manuscript structure;
3. save one UTF-8 Markdown file per chapter;
4. preserve wording, order, punctuation, paragraphing, and intentional irregularities;
5. preserve scene and section breaks;
6. compare the normalized files with the supplied artifact;
7. report extraction uncertainties before editorial review.

Normalization may correct extraction errors only when the source artifact makes the intended text objectively clear. It must not correct the author's prose.

### 3.4 Create the source record and manuscript manifest

Create `source/source-record.md` inside the workspace containing:

- source location or attachment identity;
- source draft path and format;
- source repository root and commit in Git mode;
- size, modification time, and checksum when feasible;
- import date, method, and update constraints.

Create `source/manuscript-manifest.md` containing:

- work title and manuscript identifier;
- ordered normalized chapter list and word counts;
- completeness and extraction limitations;
- operating mode and workspace identity;
- source identity from which the workspace was imported;
- source and workspace baselines in Git mode;
- source and workspace fingerprints in artifact mode.

### 3.5 Select the operating mode and establish baselines

Run preflight before creating durable state. Resolve a source location and a distinct workspace destination. Confirm whether Git can safely manage two separate local repositories, whether author identity is available in both, whether either location already belongs to a repository, and whether unrelated changes would prevent safe setup.

Use `dual-repository-git` only when both repositories can be managed safely. Initialize or reuse one repository for the source draft and another for the invariant workspace. Never nest them. Establish a source baseline commit, import and verify the normalized manuscript, then establish a workspace baseline commit. Because a commit cannot contain its own SHA, record both baseline SHAs in a later workspace metadata commit rather than amending either baseline.

Otherwise use `artifact-workspace`. Resolve the environment-provided task artifact or Outputs destination without inventing a path, create the same workspace layout there, and fingerprint the source plus normalized chapters. Artifact mode supports the complete review, proposal, approval, workspace-application, and verification lifecycle. It never authorizes writes to the source location. After approval, preserve a new workspace revision and generate a complete verified updated-source export for manual application.
## 4. Intent and Service Routing

### 4.1 Build the editorial request

Derive the following from the user's prompt and available project context:

- requested service;
- requested scope;
- intended audience and genre;
- author's stated goals and concerns;
- desired English variety and governing style references, if applicable;
- whether the user wants diagnosis only or expects approved changes to be applied later;
- target medium, such as submission manuscript, print book, ebook, or formatted proof.

Infer missing details when they do not materially change the service. Ask only when ambiguity would change the editorial level, scope, authority, or deliverable.

### 4.2 Routing examples

| User intent | Route |
|---|---|
| “What kind of editing does this novel need?” | Manuscript assessment |
| “Does the plot or character arc work?” | Developmental/structural review |
| “Review the pacing of the whole book” | Developmental review, whole novel |
| “Line edit chapter 4” | Line-edit review, chapter scope |
| “Make the prose flow better” | Line/stylistic review |
| “Check grammar and consistency” | Copyedit review |
| “Check the typeset PDF before publication” | Proofreading review |
| “Check representation of this community” | Sensitivity/authenticity review |
| “Edit my novel” | Determine the likely level from context; if still ambiguous, begin with an assessment verdict |

### 4.3 Readiness classification

Before the requested review, classify the task:

- **Ready:** the artifact and context support a professional verdict at the requested level.
- **Ready with limitations:** the review can proceed, but missing context or unsettled upstream work limits reliability.
- **Provisional:** the supplied scope is too small for a conclusive manuscript-level verdict.
- **Blocked:** the necessary artifact is absent, unreadable, incomplete for the requested service, or not in the required production state.

Readiness is part of the verdict. It must not silently reroute a clear user request into a different service.

Examples:

- A line edit can proceed on a chapter while structural revision remains possible, but the verdict must warn that later structural changes may invalidate the proposals.
- A professional proofread requires formatted proofs. An unformatted Word manuscript can receive a copyedit or surface-error review, but it must not be represented as a production proofread.
- A whole-novel continuity verdict cannot be completed from one chapter.

## 5. Editorial Services and Scope

### 5.1 Scope classification

| Service | Professional unit of judgment | Allowed execution unit | Completion requirement |
|---|---|---|---|
| Manuscript assessment/appraisal | Whole novel | Whole novel | Complete manuscript |
| Developmental/structural review | Whole novel | Whole novel; analysis may be accumulated by chapter | Complete novel read and whole-book synthesis |
| Character, plot, theme, pacing, or continuity review | Whole novel or complete narrative arc | Chapters may be analyzed incrementally | Whole-book verdict requires complete manuscript |
| Line/stylistic review | Chapter, scene, paragraph, sentence in novel context | Chapter or coherent passage | Requested unit reviewed; whole-book style claims require a final global pass |
| Copyedit review | Chapter plus manuscript-wide conventions | Chapter or batch of chapters | Whole-book completion requires consistency and completeness pass across all chapters |
| Sensitivity/authenticity review | Depends on represented subject and narrative function | Scene, chapter, or whole novel | Limit conclusions to supplied scope; recurring representation usually requires the complete novel |
| Fact-check, permissions, and legal-risk flagging | Individual claim plus manuscript-wide inventory | Chapter or batch | Whole-book completion requires full inventory |
| Proofreading | Final formatted publication | Page range or proof batch | Complete formatted proof and final global check |
| Final publication QA | Whole publication | Whole publication | All final components and approved proofs |

### 5.2 Whole-novel services

#### Manuscript assessment

Read the complete manuscript and determine:

- its apparent aims, audience, genre, and current state;
- strengths that should be preserved;
- highest-impact problems;
- the editorial level or revision work most likely needed next;
- whether the manuscript is ready for line editing, copyediting, submission, or production.

Deliver a verdict and prioritized recommendation. Do not mark up or rewrite the manuscript unless the user later requests a separate editorial service.

#### Developmental/structural review

Read the complete manuscript before issuing the final verdict. Evaluate, as applicable:

- premise and intended reader experience;
- narrative architecture and causality;
- plot, subplots, conflict, stakes, tension, and resolution;
- character motivations, relationships, development, and arcs;
- scene and chapter function;
- pacing and distribution of narrative modes;
- point of view, focalization, and information control;
- theme, motif, foreshadowing, and payoff;
- setting, chronology, and world consistency;
- genre promises and deliberate departures.

The verdict should include a prioritized revision strategy. Recommendations may describe structural operations such as move, cut, expand, combine, split, foreshadow, clarify, or reconsider. Do not rewrite the affected prose by default.

Chapter-by-chapter observations may support this review, but they are evidence for a whole-novel verdict rather than independent final verdicts.

### 5.3 Chapter-capable services

#### Line/stylistic review

Review one complete chapter or coherent passage in sufficient narrative context. Evaluate:

- voice, tone, register, and narrative distance;
- clarity, flow, cadence, and emphasis;
- diction, imagery, repetition, and figurative language;
- dialogue, subtext, and differentiated voices;
- sentence structure and a dedicated paragraph-boundary pass;
- point-of-view control;
- exposition, interiority, action, and scene rhythm;
- preservation of intentional ambiguity and stylistic irregularity.

The paragraph-boundary pass inspects every existing break and plausible missing break for paragraph unity, speaker change, shifts in time/place/viewpoint/mode, action-reaction sequence, emphasis, pacing, overlong blocks, and overfragmentation. It presumes the existing paragraphing is intentional and requires both reader-effect evidence and manuscript-pattern evidence before proposing a change; paragraph length or visual density alone is insufficient. It classifies findings as `clarity`, `attribution`, `narrative-shift`, `pacing`, `emphasis`, `unity`, `consistency`, or `intentional-exception`, with `intentional-exception` retained rather than proposed as a change. It distinguishes paragraph boundaries from scene/section breaks and production line/page wraps. The verdict includes a paragraph-break assessment even when no changes are proposed.

Produce:

1. a chapter-level verdict;
2. a prioritized issue summary;
3. a paragraph-break assessment;
4. a proposed line-edit diff;
5. queries for decisions that cannot be responsibly proposed as a single edit.

Every paragraph-boundary proposal names category `paragraph-break`, an allowed change classification, an `insert-break`, `remove-break`, or `move-break` operation, exact text anchors on both sides, current and proposed boundary states, whether wording remains unchanged, reader-effect evidence, and manuscript-pattern evidence. Do not represent the operation only through invisible whitespace.

Do not modify the working draft before approval.

#### Copyedit review

Review one chapter or a batch while carrying the project style sheet and continuity record. Evaluate:

- grammar, spelling, punctuation, usage, and syntax;
- internal consistency;
- names, capitalization, numbers, dates, hyphenation, and typography;
- timeline, physical continuity, character facts, and recurring terminology;
- cross-references and completeness;
- obvious factual questions within scope;
- consistency with the agreed language variety and style references;
- intentional fictional usage that should be preserved.

Produce:

1. a copyedit verdict;
2. a proposed copyedit diff;
3. author queries;
4. proposed style-sheet and concordance additions.

A chapter may be completed independently, but the novel is not fully copyedited until a whole-manuscript consistency and completeness review is complete.

### 5.4 Production-stage services

#### Proofreading

Use the final formatted artifact whenever possible. Review textual and visual elements, including:

- typographical and punctuation errors;
- missing, duplicated, or transposed text;
- incorrect implementation of approved edits;
- headers, footers, folios, running heads, and chapter openings;
- paragraph indents, scene breaks, widows, orphans, and bad line breaks;
- contents, cross-references, captions, and other navigation;
- consistency with the style sheet;
- layout changes caused by corrections.

Produce a proof verdict and correction log. Do not silently perform line editing, copyediting, or developmental editing during proofreading. Flag serious surviving problems separately and explain the production cost or risk of addressing them.

## 6. The Review-to-Edit Lifecycle

Every requested service follows the same control cycle.

### Phase A: Freeze the review input

Record:

- job identifier;
- service and scope;
- operating mode;
- workspace review identity;
- source import identity;
- chapter or page range;
- editorial brief;
- style and continuity resources used;
- known limitations.

Do not change the source or reviewed workspace manuscript paths while review is in progress. Preserve the original workspace and source review identities even when durable editorial artifacts create later revisions.

### Phase B: Analyze without editing

Read the required scope and build an internal evidence ledger. Separate:

- objective defects;
- probable problems supported by evidence;
- defensible creative choices;
- unresolved questions of intent;
- out-of-scope observations;
- downstream risks.

Do not write changes into the manuscript during analysis.

### Phase C: Produce the verdict

Every verdict must contain:

1. **Service and scope**
2. **Workspace review identity and source import identity**
3. **Readiness and limitations**
4. **Overall verdict**
5. **Editorial-acceptance score from 1 to 5 and rationale**
6. **Score revision and basis when clarification changed the evaluation**
7. **Strengths to preserve**
8. **Prioritized findings with manuscript locations**
9. **Recommended next actions**
10. **Proposal status**

Use one of these overall verdicts when applicable:

- `ready`
- `ready-with-reservations`
- `revision-needed`
- `not-ready-for-requested-stage`
- `provisional`
- `blocked`

These labels summarize the evidence. The separate acceptance score means: 1 not accepted, 2 major revision, 3 conditional acceptance, 4 accepted with limited reservations, and 5 accepted at the requested editorial level. Do not average finding counts or imply marketability.

### Phase D: Produce proposals when the service supports them

Use stable proposal identifiers, source locations, both review identities, and exact identity-bound text in either operating mode.

Each textual proposal records:

- proposal ID;
- service;
- severity or priority;
- location;
- exact current text;
- exact proposed replacement, insertion, deletion, or movement;
- rationale;
- reader or consistency effect;
- dependencies and cascade risk;
- status.

Allowed statuses:

- `pending`
- `accepted`
- `accepted-with-modification`
- `rejected`
- `deferred`
- `withdrawn`
- `stale`
- `applied`
- `verified`

Line editing, copyediting, and proofreading normally include exact proposals. Developmental editing normally includes recommendation records rather than prose diffs. If a structural recommendation includes sample wording, label it as an illustration, not an approved replacement.

### Phase E: Present the human approval gate

Show the verdict before requesting approval to edit. Present proposals in a manageable, source-ordered set or batch.

The user may:

- accept all proposals in the presented set;
- accept selected proposal IDs;
- reject selected proposals;
- modify a proposal;
- defer a proposal;
- ask a question;
- request a regenerated proposal;
- approve the verdict while declining all edits.

Questions, discussion, “continue,” or approval of the general direction do not authorize textual changes.

Partial approval is valid. Apply only proposal IDs explicitly accepted or accepted with user-specified modifications. Pending and deferred proposals remain unapplied.

When a writable project supports it, create an authoritative compact `decision-table.md` linked to the proposal ledger and a synchronized revision-bound `decision-table.json` for the shared interactive approval-sheet interface. Let the user submit any explicitly decided subset as `accept`, `accept-with-modification`, `reject`, `defer`, or `revise proposal`, with required exact wording for modifications and revisions. Keep long wording in keyed modification blocks rather than crowding Markdown cells. Validate and render the interactive sheet by default; direct ID responses or Markdown editing remain fallbacks.

Parse interactive responses against the saved JSON revision, update and synchronize the review records, then on a “quick check” validate IDs, allowed values, exact modified wording, dependencies, overlaps, and stale text. Annotate the records when writable and return a concise status summary. A submission, quick check, table edit, or request to review does not authorize manuscript changes. Require a separate explicit apply instruction, then translate the selected valid rows into durable approval records.

If permissions, sandboxing, missing shared-interface support, or format restrictions prevent either interface, prefer the remaining durable interface, then fall back to chat or copyable `ID | decision= | comment=` lines and run the same validation. Do not skip the approval gate. If durable approval provenance cannot be written, remain validation-only and do not edit the manuscript.

### Phase F: Revalidate approval

Before applying a proposal:

1. verify both recorded review identities;
2. verify that workspace manuscript paths have not changed since review;
3. verify that the exact current text still exists;
4. check overlaps and dependencies;
5. mark conflicting or invalidated proposals `stale`;
6. return stale proposals for review instead of guessing.

### Phase G: Apply and verify the workspace revision

Apply only explicitly accepted proposals, accepted user modifications, and mechanical consequences that create no new creative choice. If implementation exposes a new meaningful choice, stop and create a new proposal.

Create a new workspace revision in either mode. In Git mode, commit the approved batch. In artifact mode, preserve the prior revision and assign the new revision a durable identity. Verify that every workspace change maps to approval and that no text or paragraph boundary was lost, duplicated, reordered, or altered without authorization.

### Phase H: Deliver the source result

In `dual-repository-git` mode, revalidate the source repository, translate only the approved workspace changes into the source format, verify equivalence, and create a separate source commit. If safe synchronization fails, preserve the workspace commit, mark `source-sync-pending`, and create a manual-update export.

In `artifact-workspace` mode, never modify the source location. Generate a complete verified updated source under `exports/<job-id>/`, preserve prior revisions, ask the user to apply it manually, and mark `awaiting-manual-source-update`.

The application report records both review identities, the resulting workspace identity, the source commit or export identity, manual-update status when applicable, approved-only verification, and cascade tasks. It is not a new editorial pass.
## 7. Proposal Types by Editorial Service

| Service | Verdict | Exact text diff | Other proposal form |
|---|---|---|---|
| Manuscript assessment | Required | No | Recommended editorial path |
| Developmental edit | Required | Normally no | Prioritized revision plan and structural operations |
| Character/plot/pacing review | Required | Only for narrow examples | Arc, scene, or continuity recommendations |
| Line edit | Required | Yes | Author queries and optional alternatives |
| Copyedit | Required | Yes | Style-sheet decisions and factual queries |
| Sensitivity/authenticity review | Required | When a responsible alternative can be proposed | Consultation or research recommendations |
| Fact/permissions/legal-risk review | Required | When correction is straightforward | Verification, permission, or specialist-review actions |
| Proofreading | Required | Yes, as proof corrections | Layout and production queries |
| Final QA | Required | Only for identified final corrections | Publication hold or sign-off recommendation |

## 8. Shared Editorial State

### 8.1 Durable workspace artifacts

Use the same workspace layout in both operating modes:

```text
workspace/
|-- source/
|   |-- source-record.md
|   `-- manuscript-manifest.md
|-- manuscript/
|   `-- chapters/
|-- editorial/
|   |-- editorial-brief.md
|   |-- style-sheet.md
|   |-- continuity-concordance.md
|   |-- project-state.md
|   `-- reports/
|       `-- <job-id>/
|           |-- verdict.md
|           |-- proposals.md
|           |-- decision-table.md
|           |-- decision-table.json
|           |-- approvals.md
|           `-- application-report.md
`-- exports/
    `-- <job-id>/
```

The workspace `source/` directory contains provenance records, not the live source draft. In Git mode this tree is a local workspace repository separate from the source repository. In artifact mode it lives under the environment-provided task/output artifact destination.
### 8.2 Editorial brief

Record:

- work and version identity;
- authorial intent;
- audience and genre;
- requested service and scope;
- language variety and style references;
- desired intervention level;
- protected or intentional stylistic features;
- delivery format;
- known constraints and exclusions.

### 8.3 Style sheet

Track approved conventions, not every observed variation:

- spelling and language variety;
- punctuation and typography;
- capitalization and hyphenation;
- numbers, dates, and time;
- names and special terms;
- intentional nonstandard usages;
- dialogue and thought conventions;
- chapter and scene-break treatment;
- source and permissions notes when relevant.

### 8.4 Continuity concordance

Track facts whose consistency matters:

- characters, aliases, descriptions, ages, relationships, and possessions;
- chronology, dates, durations, and travel;
- locations and spatial relationships;
- world rules, institutions, titles, and terminology;
- injuries, objects, knowledge states, promises, secrets, and unresolved plot threads;
- motifs, echoes, and deliberate repeated wording.

Distinguish manuscript facts, editor inferences, proposed changes, and user-approved canon.

### 8.5 Job state

For each review job, record:

- operating mode, service, and scope;
- workspace review identity and source import identity;
- phase, verdict, proposal, and approval state;
- decision-table Markdown/JSON paths, interface revision, synchronization state, and quick-check status;
- resulting workspace identity;
- source commit, `source-sync-pending`, or manual-update export status;
- verification result and next action.

Suggested phases:

- `intake`
- `normalizing`
- `ready`
- `reviewing`
- `verdict-presented`
- `awaiting-approval`
- `applying-workspace`
- `verifying-workspace`
- `syncing-source`
- `awaiting-manual-source-update`
- `completed`
- `paused`
- `blocked`
## 9. Cross-Stage Dependency Rules

### 9.1 Upstream changes

An approved developmental revision may invalidate:

- previous line-edit proposals;
- previous copyedit proposals;
- chapter-level continuity findings;
- pagination and proof corrections.

Create cascade tasks and mark affected downstream proposals or verdicts stale. Do not silently reapply them to rewritten text.

### 9.2 Chapter-by-chapter accumulation

Line editing and copyediting may proceed chapter by chapter when:

- the current workspace manuscript identity is recorded;
- relevant preceding chapters and continuity records are available;
- each chapter receives its own verdict and proposal set;
- shared decisions are added to the style sheet;
- a final whole-manuscript consistency pass remains required before claiming whole-book completion.

### 9.3 Overlapping services

If a review uncovers an issue from another editorial level:

- record it separately;
- correct its classification;
- explain whether it blocks the requested service;
- do not silently expand the edit.

For example, a copyeditor may flag a plot contradiction but should not conduct an unrequested developmental rewrite.

### 9.4 User changes during review

If the user revises the manuscript while a verdict or proposal set is pending:

- preserve the prior report;
- identify the new manuscript commit SHA;
- compare the affected scope;
- revalidate unaffected proposals;
- mark invalid proposals stale;
- review only what changed unless broader dependencies require more.

## 10. Completion Criteria

### 10.1 Review completion

A review job is complete when:

- the required scope has been read;
- both review identities are recorded;
- the verdict, score, evidence, and applicable proposals are saved;
- neither workspace manuscript nor source changed during review;
- the user received the verdict and proposal status.

Approval is not required to complete a review.

### 10.2 Intervention and source-delivery completion

Workspace intervention is complete when every workspace change has approval, the correct review base was used, a new commit or preserved artifact revision exists, the approved-only diff is verified, and shared state is updated.

Source delivery is complete when either:

- Git mode: the approved source update is verified and committed separately; or
- artifact mode: a verified updated-source export is delivered with a clear instruction that the user must apply it manually.

Keep `source-sync-pending` and `awaiting-manual-source-update` distinct from workspace intervention completion.
### 10.3 Whole-novel completion

Do not claim that the novel has completed a service merely because every chapter was processed separately. Also verify:

- all chapters and book components are present exactly once and in order;
- shared style and continuity decisions are consistent;
- cross-chapter references, chronology, arcs, and transitions have been reviewed at the level relevant to the service;
- no chapter-level proposal or approval remains unresolved in a way that blocks completion;
- the final verdict refers to the assembled manuscript at its exact workspace and source identities.

## 11. Skill Packaging Implications

Keep `plugins/manuscript-studio/skills/literary-editing/SKILL.md` focused on:

- manuscript initialization;
- intent routing;
- scope classification;
- the verdict-first rule;
- the approval and application lifecycle;
- shared state;
- references to service-specific workflows.

Move detailed procedures into:

- `references/workspace-and-source.md`
- `references/manuscript-intake.md`
- `references/manuscript-assessment.md`
- `references/developmental-edit.md`
- `references/line-edit.md`
- `references/copyedit.md`
- `references/proofreading.md`
- `references/editorial-state.md`
- `references/git-versioning.md`
- `references/style-and-continuity.md`

Templates may be stored as assets only when they are meant to be copied into user projects. Internal schemas and instructions belong in references.

## 12. Initial Evaluation Scenarios

Before implementation, use at least these cases to test the workflow design:

1. A single DOCX containing a complete novel with no extracted chapters; the user asks for a manuscript assessment.
2. A chapter-separated novel; the user asks for a line edit of chapter 6 only.
3. A complete novel that has not received developmental editing; the user explicitly asks for copyediting.
4. A user asks to “edit my novel” without identifying the editorial level.
5. A user approves only 7 of 20 proposed copyedits.
6. The manuscript changes after a line-edit proposal set is produced but before approval.
7. A typeset PDF is supplied for proofreading, with a serious plot inconsistency discovered during the proof.
8. All chapters have been copyedited separately, and the user asks whether the whole novel is complete.
9. The source draft and proposed workspace are separate local locations, but one contains unrelated uncommitted changes; setup must preserve those changes and avoid nested repositories.
10. Git is unavailable in a web interface; the complete workspace is created as task artifacts, approved changes create a preserved workspace revision and updated-source export, and the source location remains untouched.
11. The author clarifies intent after the verdict; the score is reconsidered without requiring a manuscript change.
12. A line-edit unit contains both an overlong paragraph that may need splitting and short adjacent paragraphs that may need merging; the paragraph-boundary pass must assess every boundary and produce explicit approval-controlled operations.

Success requires correct routing, separate source and workspace identities, mode-invariant workspace structure, no pre-approval edits, exact approval provenance, safe dual-repository commits or manual source delivery, and appropriate whole-novel completion gates.
