# Structured Story Ledger Schema

Use this schema for `query-package/static/story-ledger.md`. The ledger becomes the approved, agent-neutral story source for query pitches and on-demand synopses only after its evidence audit and mandatory item-by-item human approval both pass. Build or repair it from the complete designated manuscript, bind it to that manuscript version, and generate synopses from it without reopening the raw manuscript only after explicit author closure.

The ledger is not a chapter summary. It is a linked model of what happens, why it happens, who knows what, how characters and relationships change, and what resolves. Use stable IDs so every synopsis clause can be traced without relying on narrative adjacency or model memory.
## Contents

- [Controlled values](#controlled-values)
- [1. Provenance and approval header](#1-provenance-and-approval-header)
- [2. Synopsis control card](#2-synopsis-control-card)
- [3. Entity registry](#3-entity-registry)
- [4. Chronology and narrative-order map](#4-chronology-and-narrative-order-map)
- [5. Causal event spine](#5-causal-event-spine)
- [6. Plot-thread records](#6-plot-thread-records)
- [7. Character-arc records](#7-character-arc-records)
- [8. Relationship-arc records](#8-relationship-arc-records)
- [9. Revelation and knowledge matrix](#9-revelation-and-knowledge-matrix)
- [10. Object and authority provenance](#10-object-and-authority-provenance)
- [11. Ending and resolution matrix](#11-ending-and-resolution-matrix)
- [12. Controlled claims and ambiguities](#12-controlled-claims-and-ambiguities)
- [13. Synopsis compression map](#13-synopsis-compression-map)
- [14. Completeness and integrity audit](#14-completeness-and-integrity-audit)
- [15. Mandatory human review gate](#15-mandatory-human-review-gate)
- [On-demand synopsis generation](#on-demand-synopsis-generation)


## Controlled values

Use these exact values unless the field is explicitly free text:

- ledger status: `draft`, `awaiting-confirmation`, `approved`, or `stale`;
- synopsis readiness: `ready`, `not-ready`, or `ready-with-open-items`;
- human-review gate: `not-built`, `open`, `passed`, or `invalidated`;
- human-review unit: `pending`, `approved`, `approved-with-qualification`, `accepted-as-ambiguous`, `correction-required`, or `invalidated`;
- claim type: `fact`, `character-belief`, `inference`, or `ambiguous`;
- confidence: `high`, `medium`, or `low`;
- resolution: `resolved`, `partially-resolved`, `deliberately-open`, or `unresolved-gap`;
- synopsis priority: `P0`, `P1`, `P2`, or `P3`.

Synopsis priorities mean:

- `P0`: indispensable at every requested length, including the ending and central choice;
- `P1`: include in a normal one-to-two-page synopsis;
- `P2`: include in longer synopses or when the agent's emphasis makes it relevant;
- `P3`: supporting context normally omitted from a synopsis.

Use stable prefixes: `EV` for events, `CH` for characters, `EN` for other entities, `TH` for plot threads, `RL` for relationships, `RV` for revelations, `OB` for objects or artifacts, `CL` for controlled claims, and `RS` for resolutions. IDs must remain stable across wording revisions.

## 1. Provenance and approval header

Record:

- title and author;
- ledger revision and revision date;
- ledger status and synopsis readiness;
- designated manuscript path or attachment identity;
- manuscript checksum, modification time, and word count when available;
- manuscript language and edition;
- complete-manuscript coverage statement;
- ledger creator and evidence method;
- human-review artifact identity, queue revision, and bound ledger revision;
- human-review gate status and unit counts by status;
- final closure date and the author's exact closure response when passed;
- invalidated approvals and their dependent records when applicable;
- author confirmation date and the exact entries confirmed or qualified;
- unresolved `P0` or `P1` items;
- superseded ledger identity when applicable.

An approved ledger becomes stale when the bound manuscript identity changes. Do not silently transplant it to a changed manuscript.

## 2. Synopsis control card

Provide a concise, factual control record with IDs pointing to the detailed sections:

- protagonist and starting state;
- setting and chronology baseline;
- destabilizing event or inciting disruption;
- initial external objective;
- internal need, conflict, or governing misbelief when material;
- principal opposition and its operative goal;
- central stakes: personal, relational, societal, and existential as applicable;
- point of no return;
- major escalation or midpoint change;
- final-act turn;
- climax;
- protagonist's decisive choice;
- immediate outcome;
- denouement and material end state;
- resolved Book One movement;
- deliberately open series threads;
- controlling tone and synopsis emphasis constraints.

Do not force conventional beat labels onto a novel that lacks them. Use `not-applicable` and describe the manuscript's actual structural function.

## 3. Entity registry

Create one row for every name that could affect synopsis accuracy:

| ID | Canonical name | Type | Aliases/titles | First relevant locator | Synopsis identification | Distinctions and constraints |
|---|---|---|---|---|---|---|

Include characters, factions, institutions, locations, ships, programs, species, technologies, and named historical or legendary figures. State identity equivalences and non-equivalences explicitly. Record concealed identities without flattening the manuscript's reveal order.

## 4. Chronology and narrative-order map

Record every non-linear segment that affects comprehension:

| Segment ID | Narrative position | Story time | POV/source | Locator | Function | Truth status | Related events/revelations |
|---|---|---|---|---|---|---|---|

Include flashbacks, dreams, diaries, testimony, legends, implanted or recovered memories, parallel action, and epilogues. Distinguish when the audience sees information from when it happened and when a character learns it.

## 5. Causal event spine

Create one event record for every causally meaningful change, not merely one record per chapter. Use this repeatable structure:

### `EV###` — Event label

- **Narrative position:** chapter/section and sequence.
- **Story time:** exact or relative.
- **Stable locator:** chapter or section, scene ordinal, paragraph/page/line range when available, plus a short anchor phrase. A chapter title alone is insufficient when the chapter contains multiple material events.
- **POV or information source:** character, narrator, document, dream, or testimony.
- **Synopsis priority:** `P0`–`P3`.
- **Claim type and confidence:** controlled values.
- **Threads:** linked `TH` IDs.
- **Characters/entities:** linked IDs.
- **Prior state or trigger:** what makes the event possible; cite earlier event or revelation IDs, or state an established starting condition.
- **Actor objective:** what the acting character or faction is trying to accomplish at this moment.
- **Opposition or constraint:** who or what resists that objective.
- **Choice/action:** the consequential decision or action.
- **Event:** the objective occurrence, separated from interpretation.
- **Immediate result:** what changes before the scene or sequence ends.
- **Downstream consequence:** later event IDs caused or enabled by this event. Distinguish `causes`, `enables`, `motivates`, `reveals`, and `coincides-with`.
- **Knowledge change:** linked `RV` IDs and which characters or audience learn what.
- **Character/relationship change:** linked `CH` or `RL` arc steps.
- **Object/entity state change:** linked `OB` or `EN` records.
- **Permitted synopsis wording:** a concise claim safe to paraphrase.
- **Required qualification:** attribution, uncertainty, or limitation that must survive compression.
- **Prohibited overstatement:** likely but unsupported wording to avoid.
- **Author confirmation:** date and scope when applicable.

Never create a causal edge solely because two events are adjacent. When the manuscript supports correlation but not causation, label the relationship `coincides-with` or leave it unlinked.

## 6. Plot-thread records

Create one record for the main plot and each material subplot:

### `TH##` — Thread name

- dramatic question;
- initiating event;
- stakeholders and competing objectives;
- ordered event IDs;
- intersections with the main plot and the precise effect of each intersection;
- escalation pattern;
- climax or decisive turn;
- outcome and resolution status;
- end-state consequence;
- synopsis priority and minimum length at which it should appear;
- safe compression note.

A subplot qualifies as material when removing it would change a main-plot decision, causal turn, climax, ending, or essential character transformation.

## 7. Character-arc records

Create a record for the protagonist, antagonist or principal opposition, and every character whose choices change the main plot:

### `CH##` — Character name

- identity and aliases;
- opening external situation;
- opening worldview, need, wound, allegiance, or misbelief when material;
- external goal and how it changes;
- stakes;
- relevant knowledge at the opening;
- key choices in event order, with `EV` IDs;
- pressures and opposition shaping each choice;
- relationship changes, with `RL` IDs;
- major revelation received or withheld, with `RV` IDs;
- climax function and final choice;
- end state and degree of transformation;
- unresolved arc component, if deliberate;
- synopsis priority and permitted interpretive language.

Do not convert a reader inference about psychology into objective motive. Use `character-belief`, `inference`, or `ambiguous` as required.

## 8. Relationship-arc records

For each relationship that alters a major choice or outcome, record:

| ID | Parties | Opening state | Turning events | Knowledge asymmetry | Choice or plot effect | Ending state | Priority |
|---|---|---|---|---|---|---|---|

Include romance, family, mentorship, rivalry, political allegiance, betrayal, and concealed partnership only when materially consequential.

## 9. Revelation and knowledge matrix

Create one record per major truth, false belief, secret, identity reveal, prophecy, testimony, or disputed theory:

| ID | Proposition | Objective status | Holder before reveal | Audience learns at | Character learns at | Delivery source | Event effect | Required qualification | Priority |
|---|---|---|---|---|---|---|---|---|---|

Record separately:

- what is objectively established;
- what a character claims or believes;
- when the audience receives the proposition;
- when each consequential character learns or accepts it;
- what earlier belief it displaces;
- which choices it causes, enables, or merely accompanies.

## 10. Object and authority provenance

For each material object, credential, technology, document, title, command authority, or symbolic artifact, record:

| ID | Name | Origin/creator | Custody or authority sequence | State changes | Powers/limits | Events affected | Ending state | Uncertainty |
|---|---|---|---|---|---|---|---|---|

Use explicit event links for transfers, copies, impersonations, delegated authority, forged authority, destruction, activation, and recovery. Do not infer that possession automatically grants authority or that resemblance proves identity.

## 11. Ending and resolution matrix

Record every material outcome:

| ID | Dramatic question/thread | Pre-climax state | Decisive event/choice | Outcome | Who knows | Resolution status | Book One consequence | Series consequence | Priority |
|---|---|---|---|---|---|---|---|---|---|

This section must state the protagonist's final material situation, the cost of the climax, the fates or statuses of major characters, the state of central relationships, the principal external outcome, and which threads are deliberately deferred. Distinguish a deliberate series opening from a missing resolution.

## 12. Controlled claims and ambiguities

Create a record for every consequential claim that cannot be presented as an unqualified fact:

| ID | Proposition | Claim type | Evidence locator/IDs | Confidence | Credible alternatives | Permitted wording | Prohibited wording | Author confirmation/status |
|---|---|---|---|---|---|---|---|---|

Use this section for disputed causation, uncertain motives, supernatural or scientific claims, apparent deaths, implied parentage, unreliable testimony, deliberate identity uncertainty, and author-resolved intent not stated directly in the text.

## 13. Synopsis compression map

Define reusable selections rather than drafting synopsis prose:

| Profile | Target size | Required event/thread/arc IDs | Optional IDs | Excluded IDs | Emphasis and transition notes |
|---|---|---|---|---|---|
| Micro | 250–400 words | all `P0` | selected `P1` | `P2`–`P3` | central arc and ending only |
| Standard | 500–1,000 words | `P0`–`P1` | selected `P2` | `P3` | normal one-to-two-page synopsis |
| Extended | 1,000–2,000 words | `P0`–`P2` | selected `P3` | none by rule | expand material subplots and arcs |

Add agent- or genre-specific emphasis only in the on-demand package. Do not alter the underlying event facts or priority scheme merely to flatter an agent.

## 14. Completeness and integrity audit

Complete this audit before opening the human review, but do not mark synopsis readiness `ready` until the human gate in Section 15 also passes:

- the ledger is bound to the complete, unchanged manuscript;
- every `P0` and `P1` event has a stable locator, claim type, confidence, permitted wording, and explicit cause/trigger and consequence;
- the control card links to the full inciting-to-ending spine;
- the climax, decisive choice, cost, outcome, denouement, and deliberately open threads are explicit;
- every main-plot causal edge is supported rather than inferred from adjacency;
- every material subplot intersects the main plot through identified events and has a resolution status;
- every consequential character choice appears in both the event spine and the relevant arc;
- every material relationship change and revelation is cross-linked;
- chronology and reveal order are unambiguous;
- aliases, concealed identities, object provenance, copies, impersonations, and authority transfers are explicit;
- all consequential non-facts have controlled wording and any required author confirmation;
- the compression map can produce micro, standard, and extended selections without inventing transitions;
- no unresolved gap affects a `P0` or `P1` claim.

Record audit counts and failures at the end of the ledger. Approval of general positioning does not cure a failed ledger audit. A passing evidence audit changes the ledger to `awaiting-confirmation`, human-review gate `open`, and synopsis readiness `not-ready`.

## 15. Mandatory human review gate

Read [story-ledger-human-review.md](story-ledger-human-review.md) in full. Create `query-package/static/story-ledger-review.md`, bind it to the exact ledger and manuscript identities, and convert every synopsis-eligible story proposition into a single atomic `HG` approval unit.

Create the synchronized `query-package/static/story-ledger-review.json`, validate and render it through the sibling shared approval-sheet skill, and present the complete interactive sheet. The Markdown review remains the authoritative domain audit record; the JSON is the revision-bound interface state. The author may dispose multiple items in one response and in any order, but every disposition must explicitly enumerate its `HG` ID. Parse against the saved revision and persist every answer in both records. Never treat silence, approval of a range without enumerated IDs, positioning approval, package approval, or blanket approval of the ledger as item confirmation.

A correction invalidates the originating unit and every recorded dependent. Propagate the correction, re-audit the affected ledger records, and present each corrected unit again. Do not count a correction as approval.

After all units are resolved and saved, render a separate final-closure submission with the review totals and surviving qualifications. Only after that closure is parsed may the ledger become `approved`, the human-review gate become `passed`, and synopsis readiness become `ready` or `ready-with-open-items`.

The gate fails while any unit is `pending`, `correction-required`, or `invalidated`, while a required ambiguity lacks safe wording, while the review and ledger revisions differ, or before explicit final closure. Any later material ledger correction reopens the affected units and invalidates final closure.

## On-demand synopsis generation

When an agent's verified guidelines request a synopsis, generate it only as a fresh component of that agent's complete one-time package. Do not inspect, quote, summarize, or reuse any prior synopsis or other on-demand output.

1. Verify that the ledger is `approved`, synopsis readiness is `ready` or applicable `ready-with-open-items`, the human-review gate is `passed`, the review artifact matches the ledger revision, and the ledger is bound to the unchanged manuscript identity. Do not reopen the raw manuscript.
2. Start from an empty staged synopsis file and select the closest compression profile, then adjust only for the newly verified length, format, or emphasis.
3. Draft from selected event, thread, arc, revelation, and resolution IDs. Preserve causal edges, knowledge timing, and required qualifications.
4. Include the ending and material resolution. Do not manufacture closure for deliberately open series threads.
5. Split the draft into atomic clauses and map every material clause to ledger IDs.
6. Remove or rewrite any clause that lacks a ledger source, overstates its claim type, violates prohibited wording, leaks an attribute across an ambiguous identity or time boundary, assigns unsupported motive or knowledge, or invents causation.
7. Record claim-audit counts, ledger revision, `Build mode: fresh-reproduction`, and `Prior on-demand source: none` in the on-demand manifest.
8. Place the synopsis only inside the complete staged ZIP; never persist or deliver it as a loose on-demand file.

If generation exposes a missing fact or causal connection, stop. Mark the ledger `not-ready` for the affected synopsis profile and request authorization for a targeted ledger refresh from the manuscript or a narrowly scoped author confirmation. Do not silently revisit the manuscript, guess, or seek separate approval of otherwise grounded synopsis prose.
