# High-Level Design: Agentic Workflow Orchestration Framework

**Status:** Draft v0.4 — fidelity-governed translation; first CLI iteration implemented\
**Initial use case:** Literary translation\
**Initial target market:** United States\
**Architecture:** Deterministic workflow orchestration with pluggable LLM-agent runtimes

**Implementation:** [Iteration 1](../README.md) provides a Python CLI, SQLite state, pinned skill bundles, a Codex App Server stdio adapter, revision-bound review receipts, and Markdown export. The web application and full deterministic domain-record validation remain planned; this document describes the target architecture unless an implementation limit is stated.

## 1. Overview

### 1.1 Purpose

Design and implement an extensible agentic workflow orchestration framework to automate and streamline literary editing, translation, and publishing workflows.

The framework will coordinate multiple specialized AI agents, each responsible for a well-defined stage of the editorial process. It must support human oversight, manuscript versioning, workflow observability, and controlled execution.

The initial implementation will focus on translation into English, with a US English editorial profile. Agent responsibilities must be supported by their bundled skills; model selection or role instructions alone must not be treated as adding a missing workflow capability.

The architecture should accommodate additional workflows and region-specific publishing practices, including those of China, without major changes to the orchestration core.

### 1.2 Design philosophy

The framework follows five principles:

1. **Deterministic orchestration, agentic execution.** Workflow transitions are initially governed by a static definition, while individual agents use LLMs to perform specialized, potentially nondeterministic tasks.
2. **Separation of concerns.** Workflow management, agent execution, artifact management, and user interaction must remain independently replaceable.
3. **Explicit agent contracts.** Every agent has defined inputs, outputs, responsibilities, and completion criteria.
4. **Human-in-the-loop by design.** Mandatory skill-level review and application gates are preserved inside stages, alongside configurable workflow transition gates.
5. **Reproducibility and observability.** Agent activity, manuscript revisions, configuration, and workflow transitions must be inspectable and traceable.

### 1.3 Scope

**Phase 1 — MVP**

- Implement a static, configuration-driven workflow orchestrator.
- Support sequential execution of specialized agents, including resumable chapter and passage workflows within a stage.
- Integrate Codex App Server as the initial agent runtime.
- Allow model configuration and validated skill bundles independently for each agent.
- Provide a web application for workflow initiation, monitoring, manuscript inspection, and human intervention.
- Support versioned artifacts and agent-specific execution contexts.
- Implement manuscript preparation, translation into English with integrated fidelity and prose review, human artifact acceptance, and Markdown export.

**Future phases**

- Agentic orchestration and dynamic workflow planning.
- Conditional branches, parallel tasks, and dependency-based scheduling.
- Additional editorial and publishing workflows.
- Translation into non-English targets, after extending or adding the required translation skills.
- Standalone bilingual revision and fine-grained alignment contracts.
- Region-specific conventions and regulatory requirements.
- Alternative agent harnesses and model providers.
- Automated evaluation, quality scoring, and optimization.

### 1.4 Non-goals for Phase 1

The MVP will not attempt to:

- Build a fully autonomous publishing platform.
- Automate submission to literary journals, agents, or publishers.
- Replace professional human editorial judgment.
- Support arbitrary dynamically generated workflows.
- Implement a complex distributed execution system.
- Guarantee literary quality or translation accuracy through automated evaluation alone.
- Deliver formatted DOCX, PDF, or EPUB editions without the required output-format skills, rendering tools, and verification.

The initial priority is a reliable, inspectable, and extensible end-to-end workflow.

---

## 2. Functional Requirements

### 2.1 Workflow orchestration

The system must:

- Define workflows declaratively, preferably using YAML or JSON.
- Execute stages in a predefined order.
- Track overall workflow and individual stage status.
- Pass approved artifacts between stages.
- Enforce mandatory gates from the selected skills and support additional configurable stage-transition gates.
- Handle agent errors, timeouts, cancellations, and retries.
- Resume paused workflows without rerunning completed stages unnecessarily.
- Permit rerunning a stage with modified inputs or configuration.
- Preserve workflow and artifact history.

An agent completing a task must not independently determine whether the entire workflow should advance. Stage transition decisions belong to the orchestrator.

A completed runtime turn is not necessarily a completed skill operation. A stage may stop for passage-map approval, an editorial choice, chapter closure, or an instruction to apply accepted proposals, then continue through another turn using its saved domain state.

### 2.2 Agent execution

Each agent is a logical unit consisting of:

- **Runtime / harness:** Manages agent execution, tools, sessions, and interaction with the model.
- **Model configuration:** Specifies the model and relevant inference settings.
- **Skills:** Domain-specific instructions, tools, and operating procedures.
- **Role instructions:** Define the agent's responsibility and constraints.
- **Execution context:** Contains the agent's private conversational state.
- **Input/output contract:** Specifies required input artifacts and expected outputs.

Each agent definition must name its primary skill, selected service, shared skill dependencies, and required tool capabilities. The integration contracts in Section 4.6 constrain the agent's responsibilities and completion criteria.

Agents must have isolated execution contexts.

Agents may access shared manuscript artifacts through an explicitly controlled workspace, but should not automatically inherit another agent's conversational history.

### 2.3 Manuscript and artifact management

The system must provide a shared workspace for storing and exchanging artifacts.

Artifact types may include:

- Original manuscript
- Normalized source manuscript
- Translation drafts
- Revised translation
- Copyedited manuscript
- Editorial reports
- Translation notes
- Terminology glossary
- Scoped voice record (`voice.md`)
- Style guide / style sheet
- Chapter briefs, passage maps, translation checkpoints, and review ledgers
- Editorial verdicts, proposal ledgers, decision tables, and application reports
- Human feedback and decisions
- Export-ready manuscript

Artifacts must be versioned and associated with the workflow stage that produced them.

Agents must not silently overwrite previously approved versions.

### 2.4 Human-in-the-loop capabilities

The frontend must allow users to:

- Start a workflow.
- View workflow and agent status.
- Inspect individual agent activity and execution traces.
- Review manuscript versions and differences.
- Approve or reject proposed outputs.
- Supply feedback and request revisions.
- Pause, resume, cancel, or rerun stages.
- Inspect and resolve failures.
- Modify permitted configuration for subsequent execution.

Approval and revision must be distinct operations.

An artifact acceptance authorizes the workflow to continue using a specific artifact version. Item dispositions, final closure of a review, and authorization to apply editorial changes are distinct decisions governed by the originating skill. A revision request provides additional instructions and resumes the relevant domain phase or creates a new attempt when its inputs change.

### 2.5 Observability

The system must capture:

- Workflow and stage lifecycle events.
- Agent execution start and completion.
- Model and runtime identifiers.
- Agent-generated progress messages.
- Tool invocation and results.
- File operations and artifact changes.
- Errors and warnings.
- Token consumption and estimated execution cost, when available.
- Human approval decisions.
- Stage input and output artifact references.

The frontend should display both a high-level workflow timeline and detailed per-agent traces.

Only information actually exposed by a runtime can be displayed. Internal model reasoning must not be assumed observable.

---

## 3. System Architecture

### 3.1 Major components

The framework consists of five principal layers.

**1. Web frontend**

Provides the user interface for workflow control, manuscript inspection, agent monitoring, and approval handling.

**2. Backend API and event gateway**

Exposes workflow management APIs and streams real-time execution events to connected clients.

**3. Workflow orchestrator**

Owns workflow definitions, lifecycle management, stage scheduling, transition rules, failure handling, and approval gates.

**4. Agent runtime abstraction**

Provides a uniform interface for invoking agents through different harnesses. Codex App Server will be the first supported implementation.

**5. Artifact and metadata storage**

Maintains manuscript versions, structured agent outputs, workflow state, execution metadata, and audit records.

### 3.2 Logical architecture

```text
                   ┌─────────────────────────┐
                   │      Web Frontend       │
                   │                         │
                   │ Workflow Dashboard      │
                   │ Manuscript Diff / Review│
                   │ Agent Trace Viewer      │
                   │ Approval Controls       │
                   └────────────┬────────────┘
                                │
                         HTTP / WebSocket
                                │
                   ┌────────────▼────────────┐
                   │       Backend API       │
                   │   + Event Streaming     │
                   └────────────┬────────────┘
                                │
                   ┌────────────▼────────────┐
                   │  Workflow Orchestrator  │
                   │                         │
                   │ Workflow State Machine  │
                   │ Stage Scheduler         │
                   │ Approval Manager        │
                   │ Failure / Retry Handler │
                   └────────────┬────────────┘
                                │
                   ┌────────────▼────────────┐
                   │ Agent Runtime Interface │
                   └────────────┬────────────┘
                                │
               ┌────────────────┼────────────────┐
               │                │                │
        ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
        │ Preparation │  │ Translation │  │ Editorial   │
        │ Agent       │  │ Agent       │  │ Agent       │
        │             │  │             │  │             │
        │ Own Context │  │ Own Context │  │ Own Context │
        └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
               │                │                │
               └────────────────┼────────────────┘
                                │
                   ┌────────────▼────────────┐
                   │    Shared Workspace     │
                   │                         │
                   │ Manuscript Artifacts    │
                   │ Reports and Glossaries  │
                   │ Versioned Outputs       │
                   └─────────────────────────┘

          Workflow Metadata / Event Store
          (Persistent State and Audit History)
```

### 3.3 Separation of orchestration and execution

The orchestrator must not depend on the internal implementation of a particular agent harness.

Its responsibility is to:

1. Resolve the next eligible stage.
2. Assemble the stage's input artifact references and configuration.
3. Invoke the appropriate runtime adapter.
4. Observe execution.
5. Validate declared output artifacts.
6. Persist the stage result.
7. Apply approval and transition rules.
8. Continue, pause, or terminate the workflow.

The agent runtime is responsible for executing the agent's actual work.

This separation enables eventual migration to an agentic orchestrator without requiring major changes to agent implementations, workspace management, or the frontend.

---

## 4. Agent Runtime Architecture

### 4.1 Agent definition

An agent should be described using a declarative configuration.

Each definition includes:

| Property | Description |
|---|---|
| `id` | Unique logical agent identifier |
| `runtime` | Harness adapter to invoke |
| `model` | Model selection |
| `instructions` | Agent-specific role and constraints |
| `skills` | Skills enabled for the agent |
| `service` | Operation selected within the primary skill, such as line editing or copyediting |
| `skill_contract` | Versioned integration contract, dependency bundle, workspace layout, and completion evidence |
| `required_capabilities` | Tools, validators, import adapters, and review presentation/submission capabilities |
| `input_contract` | Required input artifacts and metadata |
| `output_contract` | Expected artifacts and structured result |
| `permissions` | Workspace and tool access policies |
| `execution` | Timeout, retries, and related settings |

Agent definitions should be reusable across workflows.

### 4.2 Runtime abstraction

Define an interface similar to:

```python
class AgentRuntime(Protocol):
    async def start(
        self,
        request: AgentExecutionRequest
    ) -> AgentExecutionHandle:
        ...

    async def stream_events(
        self,
        handle: AgentExecutionHandle
    ) -> AsyncIterator[AgentEvent]:
        ...

    async def send_input(
        self,
        handle: AgentExecutionHandle,
        message: str
    ) -> None:
        ...

    async def respond_to_approval(
        self,
        handle: AgentExecutionHandle,
        approval_id: str,
        decision: str
    ) -> None:
        ...

    async def cancel(
        self,
        handle: AgentExecutionHandle
    ) -> None:
        ...

    async def recover(
        self,
        execution_id: str
    ) -> AgentExecutionHandle:
        ...
```

This is a conceptual interface, not a representation of the native Codex protocol.

The adapter should normalize runtime-specific events and capabilities while preserving references to their original forms.

Capabilities such as session recovery or interactive input may differ between runtimes. Unsupported operations must be reported explicitly.

The integration layer must classify each turn result as `in_progress`, `needs_human_input`, `blocked`, `completed`, or `failed`, using saved skill state and validation evidence. These are application outcomes, not assumed native Codex statuses. A result references the domain phase, state locator, input identities, output/checkpoint identities, and any pending gate.

`respond_to_approval` above handles runtime/tool authorization only. Domain review responses are validated against their saved review revision and delivered through `send_input` or a subsequent turn in the same logical operation. The domain skill persists the decisions and applies its own rules before the orchestrator evaluates stage advancement.

### 4.3 Codex App Server integration

Codex App Server is the preferred initial harness.

Its thread/turn/item execution model, event streaming, session lifecycle, configurable execution settings, and approval requests are suitable for building a monitored agent execution environment.

The runtime adapter should:

- Create or resume agent-specific Codex threads.
- Start a turn with agent instructions and artifact references.
- Configure the model and execution permissions.
- Subscribe to streamed execution events.
- Normalize and persist relevant events.
- Capture completion status and resulting artifacts.
- Handle native runtime approval requests.
- Resolve complete skill bundles and their relative resources; preflight validators and required adapters.
- Preserve pending domain interactions across turns without confusing them with runtime approval requests.
- Support interruption and recovery where available.

A Codex thread belongs to one logical agent execution context and must not be shared between unrelated agents or workflows.

The implementation should verify the exact supported methods and configuration options against the installed Codex version.

### 4.4 Context isolation and sharing

Two distinct information channels must be maintained.

**Private agent context**

Contains an individual agent's conversation, intermediate observations, tool interactions, and local execution history.

**Shared artifact context**

Contains documents and structured data intentionally made available to other stages.

Downstream agents receive approved or explicitly selected artifacts, not the full history of upstream agents.

This reduces irrelevant context propagation and makes agent behavior easier to reproduce.

For a separately requested editorial workflow, the line-editing agent receives:

- The accepted English translation as its designated editorial source
- A verified preparation of that exact English artifact
- Approved translation decisions and applicable voice constraints
- Terminology glossary and voice record snapshots
- Target-market style profile

It should not need the translation agent's full conversational trace. The original-language package is a separate reference dependency, never the prepared manuscript copied into the English editing workspace. Bilingual fidelity review remains the translation skill's responsibility.

### 4.5 Execution boundaries and security

Each execution should have a designated workspace and explicit read/write permissions.

Recommended policy:

- Original source files remain immutable.
- Agents write to stage-specific output locations.
- Published artifacts are immutable versions.
- Only the orchestrator can promote an artifact to the next stage.
- Skills and tools are explicitly allowlisted.
- Network access and shell execution follow configurable security policies.
- Manuscript content is treated as untrusted input, not executable instructions.
- Secrets are supplied through runtime configuration and never stored in manuscripts or trace logs.

A shared workspace is an information-exchange mechanism, not unrestricted mutual write access.

### 4.6 Skill integration contracts

The canonical skill source is [`plugins/manuscript-studio/skills/`](../../plugins/manuscript-studio/skills/). Bundle complete skill directories, including references, schemas, scripts, assets, and agent metadata. Record the skill source revision and content hashes with each execution. Validate dependency availability before starting an operation.

| Agent / operation | Primary skill | Bundled shared skills | Supported responsibility |
|---|---|---|---|
| `manuscript_preparation` | [prepare-manuscript](../../plugins/manuscript-studio/skills/prepare-manuscript/SKILL.md) | None | Location-scoped discovery, faithful extraction, chapter inventory, verification, and preparation provenance |
| `literary_translator` | [literary-translation](../../plugins/manuscript-studio/skills/literary-translation/SKILL.md) | `prepare-manuscript`, `review-approval-sheet` | English translation, glossary and voice state, passage division, two-path drafting, source-grounded review, and approved chapter delivery |
| `literary_editor` | [literary-editing](../../plugins/manuscript-studio/skills/literary-editing/SKILL.md), line-edit service | `prepare-manuscript`, `review-approval-sheet` | English prose review, verdicts, proposals, approved revisions, and whole-book consistency when requested |
| `literary_copyeditor` | `literary-editing`, copyedit service | `prepare-manuscript`, `review-approval-sheet` | Correctness and consistency review, proposals, approved revisions, and a final global pass |
| Markdown export | No agent required | None | Package the selected reviewed Markdown artifacts and provenance without changing their text |

Only preparation and translation are agent stages in the default literary-translation template. The editing/copyediting rows describe reusable services for separate, explicitly requested workflows; they are not required post-translation passes.

The [review-approval-sheet](../../plugins/manuscript-studio/skills/review-approval-sheet/SKILL.md) skill is a shared interface helper. It validates and renders review state and parses dispositions; it does not authorize or apply domain changes. Document/PDF/OCR adapters are additional environment capabilities, not supplied by `prepare-manuscript`. Missing extraction capabilities leave preparation blocked.

Each integration contract must declare:

- Input roles, scope, source and derived-artifact identities, and permitted locations.
- The skill's required workspace layout and authoritative state locators.
- Supported domain phases, mandatory gates, and permitted resume points.
- Durable outputs, internal checkpoints, and completion/validation evidence.
- Shared metadata ownership, dependency invalidation, and source-sync status.
- Runtime capabilities required to execute scripts and present and receive review decisions.

The orchestrator owns scheduling, immutable artifact registration, and transition enforcement. The originating skill owns domain decisions and their application rules. The integration layer exposes those rules through validated state and events; it must not weaken them through role prompts or configuration.

The existing translation skill already performs bilingual editorial review during translation. The MVP does not introduce a separate bilingual-revision agent or assume that the general editing skill supplies that service. A future independent translation-review operation requires an explicit reusable skill contract.

---

## 5. Initial Workflow: Literary Translation

### 5.1 Workflow objective

Transform a verified original-language manuscript into an English translation whose literary quality and fidelity are reviewed together against the source, then obtain human acceptance and export it.

A general line-editing pass is not required. Changes that improve English in isolation can alter implication, ambiguity, repetition, imagery, voice, or revelation. Approval of an English edit alone does not establish fidelity. Additional reader/editor feedback is advisory and must be resolved through the translation skill's source-grounded review before final acceptance.

The source language is recorded explicitly; the current translation skill targets English. Use `en-US` for the initial editorial profile. Other target languages require a compatible skill extension and must not be enabled solely by changing configuration.

### 5.2 Proposed workflow

```text
Upload and Designate Source / Scope
                 │
                 ▼
     Verified Manuscript Preparation
                 │
                 ▼
 Translation into English, Chapter by Chapter
   Brief and glossary / voice state
   Passage map → item review + final closure
   Two-path drafting → fidelity / prose review
   Chapter sanity review → final approval
                 │
                 ▼
        Workflow Artifact Acceptance
   Accept / return feedback to translation / pause
                 │
                 ▼
             Markdown Export
```

Mandatory domain gates occur within translation. The later workflow acceptance gate does not replace them. Revision requests return to the relevant translation phase; changed upstream artifacts invalidate dependent reviews. There is no default English line-editing or copyediting stage.

### 5.3 Stage 1 — Manuscript preparation agent

**Skill:** `prepare-manuscript`.

**Objective:** Produce a verified, neutral chapter-Markdown package without editorial intervention.

Responsibilities:

- Resolve the designated source, its authority, requested scope, and a separate neutral preparation destination.
- Extract supported formats using available document, PDF, OCR, or text adapters; report unavailable adapters as blockers.
- Identify real chapter/section boundaries and typed front/back matter without splitting by token or page limits.
- Preserve wording, paragraphing, dialogue, meaningful formatting, notes, and declared assets.
- Assign stable chapter IDs and record ordered files, source spans, fingerprints, extraction methods, and verification evidence.
- Compare the extracted scope against the source for missing, duplicated, reordered, or corrupted content.
- Validate the package and publish an immutable prepared revision.

Preparation does not create translation passages, choose English terminology, or generate a translation glossary. Glossary and cultural/voice analysis belong to translation setup. The current contract supplies chapter IDs and source locators, not stable paragraph IDs.

**Inputs**

- Designated original file, directory, attachment, or provider location, with discovery permissions
- Confirmed work and scope: whole work or selected complete chapters
- Source metadata, including language, and any source-selection instructions
- Separate writable preparation destination and available extraction adapters

**Outputs**

- `work.json`, validated against the existing work schema
- `revisions/<revision>/manifest.json`, validated against the existing revision schema
- Ordered UTF-8 chapter files under `revisions/<revision>/chapters/`
- Declared assets when needed, plus verification records, warnings, and blocking issues in the manifests

**Completion criteria**

- Source selection is confirmed and the requested complete scope is represented exactly once.
- The revision is verified against the source and all chapter/asset hashes and locators are valid.
- `validate_preparation.py <work-root>/work.json` succeeds; use `--check-sources` for accessible local sources and provider verification for remote identities.
- Preparation is `ready`, with no blockers. Reporting an error is not a successful handoff; inability to validate keeps preparation blocked.

Use the existing [preparation contract](../../plugins/manuscript-studio/skills/prepare-manuscript/references/preparation-contract.md) and its schemas rather than creating a competing package format.

### 5.4 Stage 2 — Literary translation agent

**Skills:** `literary-translation`, `prepare-manuscript`, and `review-approval-sheet`.

**Objective:** Produce approved English chapters through the skill's complete translation and source-grounded editorial-review workflow.

Responsibilities:

- Consume complete original-language chapters from the verified preparation in manifest order.
- Initialize or load user-editable `glossary.md` and `voice.md`; preserve approved terminology and voice entries scoped by character/narrator, chapter, and place.
- Read each complete chapter and create its translation brief, using prior completed English text and relevant continuity evidence.
- Propose a complete passage map; obtain item-level decisions and separate final closure before extracting source passages.
- For each passage, complete Path A, independent Path B, source-grounded audit, and refined Path B before starting editorial review.
- Save and present the full provisional checkpoint, then review fidelity and English prose under Step 3.2.
- Correct unambiguous objective errors as permitted by the translation skill; resolve meaningful choices through its source-ordered issue ledger and human decisions.
- Finalize passages, assemble the chapter exactly once, and obtain chapter sanity-review approval before durable delivery.

After presenting each finalized passage exactly as saved, preserve the skill's pause for the next passage. Record this as a continuation interaction rather than silently advancing. Chapter continuation follows the user's requested scope and the skill's completed-chapter rules.

Literary translation must not be evaluated solely as literal sentence correspondence.

The agent may restructure phrasing when justified by linguistic or literary differences, while preserving the source's meaning and artistic intent.

**Inputs**

- Ready original-language `work.json`, revision manifest, and complete requested chapters
- Translation brief/instructions and US English profile
- Existing glossary, voice record, binding decisions, prior completed chapters, and any designated benchmark translation

**Outputs**

- Verified completed chapter Markdown under `translated_english/`, retaining stable established filenames
- Updated durable `glossary.md` and `voice.md`
- Internal chapter briefs, passage maps, source passages, provisional/finalized checkpoints, review ledgers, sanity-review records, and assembled chapters
- Pending queries and gate state when paused; these are incomplete operation results, not completed chapters

The current skill does not produce a standardized sentence/paragraph alignment manifest. The MVP uses the existing chapter identities, approved passage maps, and corresponding checkpoints for traceability (Section 7.4).

**Completion criteria**

- Every passage in the approved map has a verified finalized checkpoint, and assembly has no missing, duplicated, or reordered passage.
- Required issue decisions are settled or withdrawn under the skill's rules.
- The chapter sanity review matches the assembled text and is approved. With proposed edits, all items and separate final closure must be resolved; even an empty diff requires explicit approval to complete the chapter.
- The durable chapter is reread and verified against the approved assembly.
- Whole-work completion requires all requested chapters/units; a selected-chapter result is labeled only for its verified scope.

Execute sequentially by complete chapter, with resumable passage phases. Preserve glossary, voice, decisions, and the previous completed chapter across contexts. Do not convert provisional drafts or unresolved chapter gates into successful stage completion.

### 5.5 Stage 3 — Human artifact acceptance

This is a workflow artifact-acceptance gate, additional to the mandatory translation gates already completed. It binds the exact final English chapter versions and their original-language references.

The user should be able to review the completed translation against the source and inspect changes from prior checkpoints.

Supported actions:

- **Accept artifact:** Accept the selected artifact version for export.
- **Request revision:** Return targeted feedback to the source-grounded translation review, preserving settled decisions outside the affected scope.
- **Edit manually:** Create a new proposed artifact version and revalidate it against the source before acceptance.
- **Reject:** Mark the result unacceptable without advancing.
- **Pause:** Preserve state for later review.

When requesting revisions, the system should retain both the original artifact and the proposed revision.

Approval must reference an exact artifact version to prevent ambiguity.

Feedback about awkwardness or readability also returns to translation review: it may reflect a deliberate source effect. A new translation version invalidates prior artifact acceptance. General literary editing remains a separate service rather than an automatic route for polishing the translation.

Iteration 1 supports pending domain feedback and final accept/export. Reopening completed chapters from final acceptance, manual editing with dependency invalidation, and cross-run revision routing remain future iterations.

### 5.6 Stage 4 — Final export and formatting boundary

The MVP exports the selected accepted Markdown chapters and provenance without modifying their content. This is an orchestrator operation, not an assumed formatting-agent capability.

Proofreading, typesetting, and formatted DOCX/PDF/EPUB delivery remain outside the initial scope. A future [format-manuscript](../../plugins/manuscript-studio/skills/format-manuscript/SKILL.md) agent must bundle `prepare-manuscript` and `review-approval-sheet`, obtain approval of the manuscript-bound format specification, and provide the required Documents/output-format skill and rendering tools. Missing construction or visual-verification capabilities produce `blocked-adapter`, not an ad hoc unverified edition.

### 5.7 Optional publication preparation outside the default flow

An explicitly requested copyedit may use `literary-editing` with its proposal, disposition, separate apply-authorization, and verification lifecycle. It is not a blanket exemption from fidelity review: grammar, punctuation, paragraphing, and consistency changes can also alter meaning or voice. Proposed substantive changes must return to translation review before a new final acceptance.

For such a separate editorial job, designate the exact English artifact as the editorial source and prepare it in its own neutral package. Never copy original-language chapters into the English working manuscript or relabel the original preparation as English. Use the existing artifact-workspace layout and retain source fingerprints, prepared revision, chapter mapping, verdicts, proposals, application receipts, and export identity. Track workspace intervention completion separately from any pending manual source update.

---

## 6. Workflow Engine

### 6.1 Static workflow definition

Phase 1 will use a deterministic workflow described by a configuration file.

Example:

```yaml
workflow:
  id: literary_translation_v1
  name: Literary Translation
  market: US

  source_language: zh-CN
  target_language: en-US

  # Bundles, services, and mandatory gates are defined in Section 4.6.
  # They cannot be disabled by stage-transition configuration.

  stages:
    - id: prepare
      agent: manuscript_preparation
      next: translate

    - id: translate
      agent: literary_translator
      depends_on: [prepare]
      input_role: original_language_preparation
      next: accept

    - id: accept
      kind: artifact_acceptance
      depends_on: [translate]
      next: export

    - id: export
      kind: markdown_export
      input: latest_accepted_english_artifact
```

This is an illustrative configuration, not a complete executable schema.

A production schema must define input/output artifact mappings, failure policies, and revision routing explicitly. The first CLI iteration uses the narrower executable JSON definition in [`definitions/translation.json`](../definitions/translation.json), validating the four-stage topology and required skill bundles. Source language and designated input are recorded when creating a run.

Translation executes sequentially by prepared chapter and pauses at its domain gates. The artifact-acceptance stage remains separate from those gates. General editing/copyediting services are excluded from this template.

### 6.2 Workflow state machine

Suggested workflow states:

- `CREATED`
- `RUNNING`
- `WAITING_FOR_HUMAN`
- `BLOCKED`
- `PAUSED`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

Suggested stage states:

- `PENDING`
- `READY`
- `RUNNING`
- `WAITING_FOR_HUMAN`
- `WAITING_FOR_APPROVAL`
- `BLOCKED`
- `PAUSED`
- `COMPLETED`
- `FAILED`
- `SKIPPED`
- `CANCELLED`

A stage reaching `COMPLETED` means its requested skill operation, mandatory domain gates, and artifact validation have finished successfully for the recorded scope. Editorial workspace intervention/export completion and source synchronization are tracked separately.

`WAITING_FOR_HUMAN` covers a question, passage continuation, or unresolved creative choice; `WAITING_FOR_APPROVAL` covers a typed pending gate. Persist the chapter/passage/job, phase, state locator, review revision, and next action alongside the stage state. Resume from the owning skill's verified state, not from the fact that a runtime turn ended.

Where workflow acceptance is required, an explicit acceptance stage prevents downstream execution. Domain gates prevent advancement inside the agent operation itself. The orchestrator must never infer either kind of approval from file existence or a successful model response.

### 6.3 Failure handling

Failures should be classified at least as:

- Runtime execution failure
- Model or service failure
- Artifact validation failure
- Timeout
- Permission or tool failure
- Interrupted execution
- Rejection of a stage artifact requiring revision or an explicit stop

The orchestrator should support configurable retries for recoverable failures.

Waiting for a user is not an execution failure. Suspend runtime execution timeouts and retry counters while awaiting a recorded decision; reconnecting or starting the next turn continues the same logical operation. Missing inputs/adapters and unresolved verification blockers require intervention rather than repeated blind retries. Item rejection, deferral, or reopening follows the domain rules and does not automatically fail the stage.

A retry must not silently reuse partially written outputs as authoritative input.

Retries should create distinct execution attempts, all linked to the same logical stage.

If recovery is not possible, the workflow should enter a recoverable failed or paused state while preserving prior artifacts and logs.

### 6.4 Resume and rerun semantics

A workflow must be resumable from persisted state.

Resume an interrupted or waiting operation by verifying the skill's saved source bindings, checkpoints, approvals, glossary/voice records, and cursor. Do not restart settled work solely because the runtime thread must be recreated. Changed source, proposal text, map, or assembly invalidates affected decisions under the originating skill's rules.

When a stage is rerun:

1. Create a new execution attempt.
2. Bind it to explicit input artifact versions.
3. Record the configuration used.
4. Produce new output artifact versions.
5. Invalidate downstream results that depend on superseded outputs.
6. Require appropriate reapproval before advancing.

A downstream stage must never consume a mixture of incompatible artifact versions.

### 6.5 Agentic orchestration migration

In a later phase, the static scheduler may be replaced or augmented by a planning agent.

The planning agent may:

- Select workflow branches.
- Dynamically determine required editorial stages.
- Schedule independent tasks.
- Request additional specialist reviews.
- Propose retries or targeted revisions.

However, proposed actions must still be validated by the orchestration engine.

State management, artifact provenance, permissions, and approval enforcement must remain deterministic system responsibilities.

---

## 7. Artifact Management and Data Contracts

### 7.1 Artifact model

Every produced document or report should have metadata similar to:

```json
{
  "artifact_id": "artifact-123",
  "workflow_id": "workflow-456",
  "stage_id": "literary_edit",
  "execution_id": "execution-789",
  "artifact_type": "revised_translation",
  "version": 2,
  "parent_artifact_ids": ["artifact-122"],
  "content_hash": "sha256:...",
  "storage_uri": "artifacts/revised/v2.md",
  "created_at": "2026-10-20T12:00:00Z"
}
```

An artifact's identity, content, origin, and dependencies must be independently inspectable.

### 7.2 Canonical manuscript format

For the MVP, use the existing prepared-manuscript contract: chapter-based Markdown in UTF-8 without BOM, LF newlines and a final LF, with metadata stored separately in `work.json` and the revision manifest.

```text
<neutral-preparation-root>/
  work.json
  revisions/
    r0001/
      manifest.json
      chapters/
        0001.md
        0002.md
      assets/
```

Use stable chapter IDs, source-order filenames, declared asset hashes, and source-span locators. Preserve paragraphing, dialogue, italics, scene breaks, poetry lineation, notes, tables, and non-text anchors under the skill's Markdown preservation rules. Missing meaningful content is a blocker. Metadata, glossary entries, and generated headings must not be inserted into literary chapter bodies.

The original-language preparation stays outside its designated source location and translation working/output directories. If a separate English editorial job is requested, its preparation has its own locator and exact English source identity. Record that derived-artifact lineage without changing the existing preparation schemas.

DOCX/PDF/OCR intake requires available adapters and source comparison; the preparation skill does not itself supply converters. Stable paragraph identifiers and fine-grained alignment are future extensions, not prerequisites attributed to the current skill.

### 7.3 Artifact handoff

Agents must exchange artifacts through declared contracts rather than informal assumptions about file names.

Each stage receives a manifest specifying:

- Input artifact identifiers and versions
- Readable workspace paths
- Required output artifact types
- Writable output locations
- Agent instructions
- Relevant market and style configuration
- Prepared package locator, revision, scope, source role, and derived input identities
- Skill state locator and required continuity/approval records for resume

Upon completion, the runtime adapter returns a structured execution result.

The orchestrator validates and registers the outputs before making them available to downstream stages.

Materialize the required skill layouts in supplied task workspaces rather than asking agents to invent new filenames or flatten their records into a generic report. Translation uses `glossary.md`, `voice.md`, `translated_english/`, and its `.literary-translation-work/<work>/<chapter>/` state. Editing uses `source/`, `manuscript/chapters/`, `editorial/`, and `exports/`.

Skill working files may evolve during an active operation, while registered versions remain immutable. Snapshot checkpoints and decision records at durable boundaries before subsequent changes. In editorial artifact mode, apply changes to a new workspace revision and preserve the reviewed revision. Resume resolves logical skill paths to the correct working revision.

Internal translation state is retained for recovery and audit in the framework, but is not listed as a user deliverable by default. Completed chapters, glossary, and voice records remain durable project artifacts. Bind downstream inputs to explicit glossary/voice versions, and ingest direct user edits as new versions requiring affected-state revalidation.

### 7.4 Source alignment and editorial traceability

For literary translation, source-to-target alignment is particularly important.

The MVP retains the existing source chapter ID/hash, approved passage map, numbered source passages, corresponding English checkpoints, and assembly order. These support chapter/passage navigation and the exact paired source/English excerpts required by translation review.

Verify that extracted passage bodies reproduce the source chapter exactly once and that finalized checkpoints assemble exactly once. This establishes structural coverage, not automated proof of semantic fidelity.

The current skills do not define a machine-readable sentence/paragraph alignment schema or stable paragraph IDs. A future extension may support one-to-many and many-to-one relationships. Do not require agents to emit such a manifest until its contract and validation exist.

If a separately requested editorial job changes paragraph boundaries or phrasing, retain the original translation correspondence as historical evidence; do not present it as freshly validated alignment of the edited text. Revalidate the proposed translation changes against the source before final acceptance.

### 7.5 Domain state and shared metadata ownership

The backend database owns execution lifecycle, artifact identities, dependencies, and recorded gate enforcement. Skill records remain authoritative for domain content: passage maps, issue ledgers, proposal text, decisions, approved diffs, and source-sync state. `work.json` is the skill-defined shared preparation/status record, not a replacement for either layer.

Each owning workflow updates only its own `workflows.<skill-name>` summary, using the existing `basis_revision`, scope, operation, and `state_locator` contract. Line editing and copyediting use the same `workflows.literary-editing` slot for the current operation; retain all distinct jobs in their domain records and backend history. A summary marked complete must never imply completion of another service, unprocessed chapters, or pending source synchronization.

Serialize `work.json` updates, reread and merge owned fields, increment `record_revision`, and preserve other workflows' newer state. Where the shared record is read-only, retain the proposed update in the owning workflow's artifacts and record synchronization as pending, as the preparation contract requires.

Persist review submissions/receipts before resuming work. After domain records and outputs are saved and validated, reconcile them into backend state and shared summaries. Recovery must detect a partially completed update, reconcile it idempotently by receipt and artifact identities, and prevent duplicate application or premature promotion. A database status alone cannot clear a domain gate.

A changed original invalidates its preparation and dependent work. A changed English translation or edited export invalidates its own preparation and downstream jobs without falsely marking the unchanged original-language preparation stale. Only the owning workflow revalidates its domain decisions.

---

## 8. Frontend Design

### 8.1 Workflow dashboard

Display:

- Available workflow templates
- Active and historical workflow runs
- Current execution stage
- Overall progress
- Pending approvals
- Errors and warnings
- Recent execution activity

The user should be able to initiate a workflow by selecting a template, designating a manuscript and scope, and configuring its source language and English editorial profile. The MVP must reject unsupported non-English translation targets. Display unavailable import adapters before extraction begins.

### 8.2 Workflow execution view

Present the workflow as a stage-based timeline or directed graph.

Each stage should expose:

- Execution status
- Assigned agent
- Model and runtime
- Start and completion times
- Input and output artifacts
- Validation results
- Execution logs
- Retry and revision history
- Current domain phase, chapter/passage or editorial job, and pending decision
- Workspace intervention/export status separately from manual source-update status

### 8.3 Agent trace viewer

Provide live access to normalized agent events.

Useful event categories include:

- Agent started/completed
- Progress messages
- Tool calls
- File modifications
- Model output events
- Runtime approval requests
- Domain review requests, item dispositions, final closure, and apply authorization
- Warnings and failures

A detailed trace viewer should permit filtering by stage, agent, execution attempt, and event category.

### 8.4 Manuscript review interface

Provide a manuscript-oriented review experience, not merely a generic log viewer.

Preferred capabilities:

- Side-by-side source and translation display.
- Translation draft versus revised translation diff.
- Navigation by chapter or section.
- Review of editorial comments and queries.
- Ability to approve or request changes.
- Manual manuscript corrections.
- Clear identification of the currently approved version.
- Review of glossary and scoped voice records without losing user edits.
- Revision-bound item decisions, separate closure, and separate editorial apply authorization.

The interface should distinguish proposed AI changes, accepted-but-unapplied proposals, and applied manuscript content. Translation review must show the exact original-language excerpt alongside the current saved English text for each decision. Chapter/passage navigation uses existing maps; sentence-level synchronized alignment is not an MVP promise.

### 8.5 Human approval integration

The orchestrator persists and enforces gates; the originating skill determines domain decision semantics. The frontend must distinguish:

| Decision category | Effect |
|---|---|
| Domain item disposition | Accept, reject, qualify, modify, or reopen an identified item under its skill's rules |
| Domain final closure | Confirm the complete current review after its required items are resolved |
| Editorial apply authorization | Separately authorize application of the valid accepted editing proposals after quick-check |
| Workflow artifact acceptance | Permit downstream use of an exact resulting artifact version |
| Runtime/tool approval | Authorize a specific runtime action, not an editorial decision |

Every request references workflow, stage, logical operation/execution, and exact input/artifact identities. Shared review submissions additionally bind `sheet_id`, `revision`, explicit item IDs, allowed commands, and required notes. Use the existing [approval-sheet schema](../../plugins/manuscript-studio/skills/review-approval-sheet/references/approval-sheet-schema.md), validator, renderer, parser, and domain adapters. Reject stale revisions, unknown/duplicate IDs, disallowed commands, and missing required notes. Persist the parsed receipt and domain response before advancing.

Submitting item choices does not implicitly close a review. Where closure is required, render a newly saved revision with all required items resolved before offering final closure. For literary editing, quick-check and summarize valid decisions, then require the separate affirmative apply instruction before persisting application authorization and changing text. For translation, preserve its different rules: settled Step 3.2 choices may update the checkpoint, while passage-map and chapter-sanity gates require their specified closure. An empty chapter sanity diff still needs explicit chapter-completion approval.

**Presentation integration**

The shared renderer produces an HTML fragment intended for `::codex-inline-vis{file="<basename>.html"}`. Its submission controls call `window.openai.sendFollowUpMessage`; Codex App Server event streaming alone does not establish that browser host capability.

The web runtime integration must resolve the directive to the generated fragment, display it inline as-is, and provide a tested host bridge for disposition and closure payloads back to the backend/parser. Bind the bridge to the displayed sheet revision and requesting operation. Do not modify the embedded state, add network behavior to the generated fragment, or assume that a file link satisfies presentation.

Until that surface works, use the skill's permitted readable text/table fallback with the same IDs, revision, commands, required notes, and parser. Interface limitations never remove a gate. Discussion-heavy or dependent translation choices remain individual source/English dialogues; a generic batch UI must not flatten them.

---

## 9. Backend and Persistence

### 9.1 Suggested technology stack

For the MVP:

| Component | Proposed technology |
|---|---|
| Backend API | Python / FastAPI |
| Workflow orchestrator | Python asynchronous service |
| Initial agent runtime | Codex App Server |
| Frontend | React / TypeScript |
| Live event streaming | WebSocket or SSE |
| Workflow metadata | SQLite initially; PostgreSQL later |
| Artifact storage | Versioned local filesystem initially |
| Workflow definition | YAML |
| Document conversion | Preflighted import adapters; unchanged Markdown export in the MVP |
| Domain review | Existing approval-sheet validator/parser and renderer, with host bridge or permitted text fallback |

The implementation should avoid coupling domain logic to the chosen web framework or database.

### 9.2 Core persistence entities

At minimum, persist:

- `WorkflowDefinition`
- `WorkflowRun`
- `StageRun`
- `AgentDefinition`
- `AgentExecution`
- `SkillOperationCheckpoint` (domain phase, scope, state locator, and bindings)
- `Artifact`
- `ArtifactDependency`
- `ApprovalRequest`
- `ApprovalDecision`
- `ReviewSubmission` (sheet revision, payload/parsed receipt, and application status)
- `DomainStateBinding` (domain record revisions, shared metadata revision, and sync status)
- `ExecutionEvent`

The persisted state must be sufficient to reconstruct workflow progress after restarting the backend.

Preserve the referenced skill files and snapshots as well as database rows. Runtime thread recovery cannot substitute for verified domain checkpoints, and domain files alone do not prove that a frontend submission was authorized and recorded.

### 9.3 Event handling

Use a structured event model to decouple agent execution from the frontend.

Example:

```json
{
  "event_id": "evt-001",
  "workflow_id": "workflow-456",
  "stage_id": "translate",
  "execution_id": "execution-789",
  "type": "agent.progress",
  "timestamp": "2026-10-20T12:01:00Z",
  "payload": {
    "message": "Translation draft generated"
  }
}
```

Events should be persisted before or independently of delivery to browser clients.

Reconnecting clients should be able to retrieve historical events and subscribe to subsequent updates without depending on an uninterrupted browser session.

---

## 10. Extensibility and Localization

### 10.1 Regional workflow profiles

Region-specific conventions should be represented as configuration and policy layers, not hardcoded into the core orchestrator.

A regional profile may specify:

- Target language variant
- Preferred editorial standards
- Punctuation and typography rules
- Manuscript formatting conventions
- Required publication metadata
- Copyright or submission requirements, where applicable
- Region-specific workflow stages

For example, the MVP's US English profile may default to an agreed editorial style. A future China-focused profile may require different terminology, formatting, or publication preparation, plus skills capable of the requested output language and services. Configuration must not claim capabilities absent from the selected bundle.

Legal, regulatory, and submission requirements should be maintained as separately validated policies rather than inferred from language alone.

### 10.2 Additional workflows

Future workflow templates may include:

- Original manuscript developmental editing
- Literary line editing and copyediting
- Translation into multiple languages
- Manuscript critique and evaluation
- Proofreading
- Submission package preparation
- Publisher-specific manuscript formatting
- Publication metadata preparation

Agents and skills should be reusable across these workflows wherever responsibilities overlap.

The repository already supplies `literary-agent-querying` and `format-manuscript`; these are optional future workflow integrations, not missing MVP agents. Querying retains its own designated-input restrictions, story-ledger review, named-agent package authorization, and source-evidence rules; it must not automatically consume edited workspace manuscripts or editorial reports. Formatting retains specification approval, output-adapter dependencies, and visual verification. The separate cover-design prototype is not part of the six-skill distributed plugin or this MVP.

### 10.3 Runtime extensibility

The orchestrator must interact with agents exclusively through the runtime abstraction.

Future adapters may use different:

- Harnesses
- Models
- Tool ecosystems
- Execution environments
- Session and memory mechanisms

The core workflow state machine and artifact management system should not need to understand these implementation details.

---

## 11. Implementation Roadmap

### Phase 1A — End-to-end orchestration prototype

Implement:

- Workflow definitions
- Explicit skill bundles, service contracts, and capability preflight
- Sequential stages with resumable chapter/passage and editorial phases
- Codex runtime adapter
- Existing preparation package validation and original-language source handoff
- Stage status tracking
- Mandatory domain gates, using the validated text fallback before a web review surface exists
- Persistent domain checkpoints, review receipts, immutable snapshots, and shared-status reconciliation
- Basic error handling

**Milestone:** Prepare a complete chapter, translate it through the required human gates, and export an explicitly accepted English artifact with traceable source and review records.

Iteration 1 implements the CLI lifecycle, Codex stdio transport, preparation validation, review receipts, artifact snapshots, and final export. Tests use synthetic fixtures and a protocol subprocess. A live installed-Codex smoke run and deterministic parsing of all domain completion records are still required; see the implementation README for precise limits.

### Phase 1B — Web-based interaction

Implement:

- Workflow initiation API
- Browser dashboard
- Live agent event streaming
- Stage execution inspection
- Manuscript artifact viewer
- Inline approval-fragment hosting and submission bridge, retaining the permitted text fallback
- Distinct item review, final closure, apply authorization, and artifact acceptance controls
- Pause and resume controls

**Milestone:** A user can monitor and complete the same skill-compliant workflow in the browser, including pauses within a stage and revision-bound decisions.

### Phase 1C — Editorial reliability

Implement:

- Chapter/passage correspondence and editorial proposal anchors
- Side-by-side comparison and diffs
- Multi-chapter revision cycles with dependency invalidation
- Glossary and scoped voice consistency, including user edits
- Source-grounded chapter/whole-work completion checks and targeted revision routing
- Restart/recovery verification across domain gates and partially synchronized records
- Basic evaluation fixtures and regression tests

**Milestone:** The system can reliably process a multi-chapter manuscript while preserving editorial decisions and artifact provenance.

Reuse the existing preparation validator/evaluation fixtures and approval-sheet tests as contract references. They do not replace new integration checks for stale submissions, repeated receipts, source-role handoff, or paused-operation recovery.

### Phase 2 — Advanced workflow capabilities

Explore:

- Conditional workflow branches
- Parallel chapter translation
- Independent quality review agents
- A reusable standalone bilingual-revision skill, if required
- Paragraph identity and many-to-many alignment contracts
- Dynamic stage selection
- Agentic planning and orchestration
- Multi-market localization
- Non-English target-language skills
- Formatted editions with explicit construction and rendering dependencies
- Publishing and submission integrations
- Automated quality evaluation

---

## 12. MVP Acceptance Criteria

The Phase 1 implementation is successful when:

1. A user can designate a manuscript and scope and initiate translation into English from the web frontend; unsupported targets and unavailable required adapters are reported.
2. The orchestrator executes the configured agents in the correct sequence.
3. Each agent operates with an isolated context, configurable model, and validated complete skill bundle whose capabilities match its assigned service.
4. Preparation passes the existing schemas and validator with no blockers before handoff; stage outputs are versioned with explicit provenance.
5. Translation consumes the original-language preparation and prior approved continuity artifacts without inheriting another agent's private conversation.
6. Users can inspect stage status, agent traces, and manuscript changes in the frontend.
7. Translation cannot draft before passage-map closure or deliver a completed chapter before sanity-review approval, including approval when no edits are proposed.
8. Reader/editor feedback returns to source-grounded translation review; no general line-editing or copyediting stage silently polishes an accepted translation.
9. Pending human input pauses an operation without timeout retries; recovery preserves settled choices and resumes the verified phase.
10. Backend restart reconciles database, domain records, pending review receipts, and shared summaries without duplicate application or lost approvals.
11. The application exports the selected accepted Markdown manuscript without claiming formatted publication delivery or completed manual source synchronization.
12. A second workflow definition or agent runtime can be introduced without major modifications to the orchestration core.
13. Review submissions are revision-bound; stale or duplicate submissions cannot apply changes or clear a gate. The inline bridge or permitted text fallback uses the existing parser.
14. Glossary/voice state and user changes survive context replacement; upstream edits invalidate affected preparations, proposals, and acceptances.
15. A whole-work completion claim requires every requested source unit to complete the translation skill's checks and human gates.

---

## 13. Outstanding Design Decisions

The following require further evaluation during implementation.

**A. Runtime turn granularity**

How should runtime turns map to the skill's chapter, passage, and editorial phases?

The domain granularity is fixed by the current skills: complete-chapter analysis, approved passage division, passage drafting/review, and chapter closure. Start with one logical operation per chapter and multiple turns as needed, carrying glossary, voice, and decisions explicitly. Do not split the mandatory two-path drafting completion gate to solicit intermediate wording decisions.

**B. Workspace materialization**

How should immutable artifact versions be materialized at the paths expected by each skill?

The format is settled for the MVP: prepared chapter Markdown plus the existing JSON metadata and domain layouts. Choose an implementation for revision directories, snapshots, and writable current state that preserves these contracts; do not introduce a competing canonical text format.

**C. Agent context lifecycle**

Should the same runtime thread persist across all chapters of a stage?

Recommended initial approach: one logical context per chapter operation or editorial job, resumed across its turns. New contexts receive verified domain checkpoints and approved continuity artifacts. Avoid unlimited context accumulation or transferring private traces between agents.

**D. Human editing and revision routing**

Should manual edits automatically trigger downstream reprocessing?

Recommended initial approach: make reprocessing an explicit, dependency-aware action. Invalidate affected downstream outputs and require new approval where necessary.

**E. Quality evaluation**

Which translation characteristics can be automatically validated?

Recommended initial approach: deterministic checks for declared scope, hashes, source/passage coverage, assembly, review identities, and approved-only diffs. Terminology scans may flag candidates but must respect approved contextual/asymmetric renderings and scoped voice changes. Literary quality and nuanced fidelity remain subject to the skill's source-grounded review and human judgment.

**F. Artifact locking**

How should simultaneous writers or revision conflicts be managed?

Recommended initial approach: immutable committed artifacts, per-stage writable directories, and atomic promotion of validated outputs.

**G. Workflow execution durability**

How should in-progress agent executions be recovered after service interruption?

Recommended initial approach: persist execution identifiers and state transitions, implement runtime-specific recovery where supported, and reconcile incomplete executions before retrying.

---

## 14. Long-Term Architectural Direction

The framework should evolve into a generalized editorial workflow platform in which specialized agents collaborate through explicit artifacts under the supervision of a durable orchestrator.

The orchestrator may eventually become agentic in its planning and decision-making, but the following responsibilities must remain enforced by deterministic infrastructure:

- Workflow lifecycle and state integrity
- Agent execution permissions
- Artifact versioning and provenance
- Human approval enforcement
- Retry and failure semantics
- Auditability and observability

The intended result is a human-supervised, extensible system that combines the flexibility of LLM agents with the reliability and traceability expected of professional editorial software.
