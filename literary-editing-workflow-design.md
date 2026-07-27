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
8. Preserve the original manuscript, approved decisions, workflow state, and provenance of every applied change through a project-local Git history.
9. Attach a scoped 1–5 editorial-acceptance score to every verdict, with revision history when author clarification changes the editorial understanding.

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

### 2.5 Original preservation and Git binding

Never edit the received source artifact. After normalization, use one canonical chapter set under Git rather than duplicating complete draft folders. Every verdict and proposal must identify the exact reviewed commit. If the manuscript changes before approval or application, revalidate or regenerate affected proposals against the new commit. If Git is unavailable or setup fails, redirect all generated outputs away from the project and into the current task artifact area, switch to verdict-and-score-only work, and do not create proposals or apply edits.

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

### 3.4 Create the manuscript manifest

Create a manuscript manifest containing:

- work title and manuscript identifier;
- source artifact path;
- source artifact checksum when feasible;
- normalized chapter list in order;
- word counts;
- completeness status;
- extraction or formatting limitations;
- intended Git repository root;
- baseline commit and tag, once created.

### 3.5 Initialize or reuse local Git

Begin Git setup only after the received manuscript has been normalized, split into verified chapter files, and recorded in the manifest.

1. Resolve whether the manuscript project is already inside a Git repository.
2. If an appropriate project repository already exists, reuse it. Do not create a nested repository.
3. If a parent repository exists but its intended scope is unclear, ask before adding the manuscript project to it or creating a separate repository.
4. If no repository exists, initialize one at the manuscript project root.
5. Keep the repository local by default. Do not add a remote or push manuscript content unless the user explicitly requests it.
6. Create a project `.gitignore` before the baseline commit. Ignore temporary extraction files, editor or office lock files, generated caches, and disposable exports. Keep normalized chapters and durable editorial records tracked.
7. Verify that Git author identity is available. If a commit cannot be created because identity is missing, ask the user for the local repository identity rather than inventing one.
8. Inspect the working tree. Never stage unrelated pre-existing files or changes, and never use a broad staging command that could capture them.
9. Stage only the verified normalized chapters, manuscript manifest, agreed source artifact or its checksum record, and initial durable editorial files.
10. Create the baseline commit with a clear message such as `chore(manuscript): establish normalized baseline`.
11. Tag that commit `manuscript-baseline`.
12. Record the full baseline commit SHA and tag in the manuscript manifest and project state.
13. Confirm that the tracked manuscript tree is clean before beginning editorial review.

The baseline commit is the immutable reference point. The checked-out manuscript files remain the single current draft. Later approved edits create new commits rather than new copies of the full chapter tree.

If the supplied source is a large binary DOCX or PDF, retain it as the received source of record but do not rely on Git to provide meaningful textual diffs. Use its checksum and the normalized Markdown chapters to verify provenance. Track the binary only when project policy and repository size make that appropriate.

If Git is unavailable, initialization fails, or no safe baseline commit can be created, stop writing generated files into the manuscript project. Resolve the environment-provided task artifact or Outputs destination without inventing a path and redirect every generated setup and review output there. Continue only in `verdict-score-only` mode. Permitted task artifacts are limited to the diagnostic, artifact manifest, any normalized review copy needed for assessment, the scoped verdict, acceptance score, and score revisions. Do not produce project-local editorial state, proposal diffs, decision tables, approval records, application reports, revised manuscripts, alternate project draft folders, or Git-bound completion claims. If no task-artifact facility exists, write no generated editorial files into the project and return the permitted result in chat with the persistence limitation stated. If Git later works, establish a clean baseline and start a new commit-bound review before proposing edits; treat fallback artifacts as reference evidence only.

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
- sentence and paragraph structure;
- point-of-view control;
- exposition, interiority, action, and scene rhythm;
- preservation of intentional ambiguity and stylistic irregularity.

Produce:

1. a chapter-level verdict;
2. a prioritized issue summary;
3. a proposed line-edit diff;
4. queries for decisions that cannot be responsibly proposed as a single edit.

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
- reviewed Git commit SHA;
- chapter or page range;
- editorial brief;
- style and continuity resources used;
- known limitations.

Do not change the reviewed manuscript paths while the review is in progress. If durable review artifacts are committed during the review, preserve the original reviewed commit SHA as the manuscript base.

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
2. **Git commit reviewed, or fallback artifact identity**
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

Skip Phase D and every intervention phase in `verdict-score-only` mode.

Use stable proposal identifiers, source locations, the reviewed Git commit SHA, and exact commit-bound text.

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

When a writable project supports it, create a compact `decision-table.md` linked to the authoritative proposal ledger. Let the user mark each row `accept`, `accept-with-modification`, `reject`, `defer`, or leave it blank, with a comment or modification reference. Keep long exact wording in keyed modification blocks below the table rather than crowding cells.

On a “quick check,” validate IDs, allowed values, exact modified wording, dependencies, overlaps, and stale text; annotate the table when writable and return a concise status summary. A quick check, table edit, or request to review the table does not authorize manuscript changes. Require a separate explicit apply instruction, then translate the selected valid rows into durable approval records.

If permissions, sandboxing, or format restrictions prevent table creation or update, present the same rows in chat or as copyable `ID | decision= | comment=` lines and run the same validation. Do not skip the approval gate. If durable approval provenance cannot be written, remain validation-only and do not edit the manuscript.

### Phase F: Revalidate approval

Before applying a proposal:

1. verify that the proposal identifies the reviewed commit SHA;
2. verify that manuscript paths have not changed since that commit, even if editorial reports have been committed separately;
3. verify that the exact current text still exists at the recorded location;
4. confirm that the tracked manuscript working tree is clean before application;
5. check whether another approved proposal changes the same span;
6. resolve proposal dependencies in a safe order;
7. mark conflicting or invalidated proposals `stale`;
8. return stale proposals for review instead of guessing.

### Phase G: Apply approved changes

Apply approved changes to the single checked-out manuscript tree. Never alter the received source artifact or rewrite the baseline commit.

Apply only:

- explicitly accepted proposals;
- user-specified modifications to accepted proposals;
- mechanical consequences strictly required to implement an approved proposal, when those consequences do not create a new creative choice.

If implementation exposes a new meaningful choice, stop and create a new proposal. Stage only the approved manuscript changes and their approval/application records. Create one commit for the approved batch with a message that identifies the service, scope, and proposal IDs. Do not amend or rewrite earlier commits.

### Phase H: Verify and report

After application:

1. compare the new manuscript commit with the reviewed commit;
2. verify that every applied change maps to an approval record;
3. verify that rejected, deferred, and pending proposals were not applied;
4. check for missing, duplicated, reordered, or corrupted text;
5. update the style sheet and continuity record only for approved decisions;
6. identify cascade tasks created by the applied changes;
7. record the resulting commit SHA in the application report;
8. tag only meaningful editorial milestones, not every small batch;
9. present the application report and resulting commit to the user.

The application report is not a new editorial pass. Any newly discovered optional improvement becomes a new review job.

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

### 8.1 Durable project artifacts

Recommended project layout:

```text
project/
|-- .git/
|-- .gitignore
|-- source/
|   |-- received-manuscript.docx
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
|           |-- approvals.md
|           `-- application-report.md
`-- exports/
```

Adapt names to an established project convention rather than creating duplicates. This layout becomes valid only after safe Git preflight succeeds. When Git setup cannot support a baseline, keep the manuscript project untouched by generated outputs and route the complete permitted fallback bundle to the current task artifact area.

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

- service and scope;
- reviewed Git commit SHA;
- phase;
- verdict status;
- proposal set and statuses;
- decision-table path, quick-check status, or fallback mode when used;
- approval records;
- applied output commit SHA;
- verification result;
- next action.

Suggested phases:

- `intake`
- `normalizing`
- `ready`
- `reviewing`
- `verdict-presented`
- `awaiting-approval`
- `applying`
- `verifying`
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

- the current manuscript commit SHA is recorded;
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
- the verdict, editorial-acceptance score, and evidence are saved;
- all expected proposal artifacts are saved, except in `verdict-score-only` mode, where every permitted generated output is stored in the task artifact area and no project-local editorial output is created;
- no manuscript text has been changed;
- the user has received the verdict and proposal status.

Approval is not required to complete a review.

### 10.2 Intervention completion

An intervention job is complete when:

- every applied change has an explicit approval record;
- the application targets the correct reviewed commit;
- a new approved-change commit has been created;
- the approved-only diff has been verified;
- shared editorial state has been updated;
- cascade tasks have been recorded;
- the user has received the application report and revised artifact.

### 10.3 Whole-novel completion

Do not claim that the novel has completed a service merely because every chapter was processed separately. Also verify:

- all chapters and book components are present exactly once and in order;
- shared style and continuity decisions are consistent;
- cross-chapter references, chronology, arcs, and transitions have been reviewed at the level relevant to the service;
- no chapter-level proposal or approval remains unresolved in a way that blocks completion;
- the final verdict refers to the assembled manuscript at its exact commit SHA.

## 11. Skill Packaging Implications

Keep the future `literary-editing/SKILL.md` focused on:

- manuscript initialization;
- intent routing;
- scope classification;
- the verdict-first rule;
- the approval and application lifecycle;
- shared state;
- references to service-specific workflows.

Move detailed procedures into:

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
9. A normalized manuscript project is already inside a Git repository that contains unrelated uncommitted user changes.
10. Git is unavailable or baseline creation fails; every generated setup and review output is redirected to the task artifact area, and the editorial output stops at verdict and score.
11. The author clarifies intent after the verdict; the score is reconsidered without requiring a manuscript change.

Success requires correct routing, honest scope labels, no pre-approval edits, exact approval provenance, preservation of the baseline, and appropriate whole-novel completion gates.
