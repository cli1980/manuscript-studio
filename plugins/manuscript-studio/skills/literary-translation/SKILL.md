---
name: literary-translation
description: Translate literary works chapter by chapter from a shared prepared-manuscript package, using a living glossary and evolving voice record, whole-chapter analysis, systematic passage division with interactive boundary approval, two-path drafting, source-grounded editorial review with reusable approval sheets, and durable completed-chapter output. Use when translating fiction, memoir, narrative nonfiction, poetry-inflected prose, or other literary writing from a source language into natural English, especially for new translation projects, passage-by-passage collaboration, close fidelity review, preservation of voice and reader experience, continuity with earlier translated chapters, or culturally dense writing shaped by dialect, oral storytelling, folklore, socially marked speech, or changing regional and historical registers.
---

# Literary Translation

Translate a complete chapter through a chapter-level reading followed by a repeating passage workflow. Treat the source as authoritative throughout.

## Governing Standard

Produce English that works as literature while preserving how the source communicates:

> An English reader should receive the same information, with the same emphasis, implications, uncertainties, and manner of revelation, as a source-language reader.

Use natural English rather than reproducing source-language syntax. Do not add explanation, motivation, atmosphere, symbolism, certainty, or drama absent from the source.

## Initialize or Resume the Project

Determine the project state before beginning Step 1.

For a new project, or an existing project missing a verified prepared source, `glossary.md`, `voice.md`, or `translated_english/`, read [references/project-setup.md](references/project-setup.md) in full. Delegate location-scoped manuscript discovery, extraction, chapter normalization, and source metadata to the sibling [prepare-manuscript skill](../prepare-manuscript/SKILL.md); do not duplicate its preparation workflow here.

Use the shared `work.json` and its current revision manifest as the source handoff. Read chapters in manifest order and preserve the prepared source files. Update only `workflows.literary-translation` under the [shared status contract](../prepare-manuscript/references/preparation-contract.md#downstream-status-and-ownership), pointing to the translation project's actual state location. Bind the operation and chapter scope to the prepared revision. Chapter completion is not whole-work completion.

Read and reuse the [shared manuscript metadata](../prepare-manuscript/references/manuscript-metadata.md).
Use `manuscript_language` for the designated input, not `original_language`.
Preserve user edits and record the fields used; shared metadata may be enriched
or explicitly corrected under that contract. Reconcile language changes with the
translation configuration. A metadata-only edit does not replace source text or
revoke unrelated passage approvals. Keep glossary, voice, and target-edition
metadata in the translation records; do not relabel the source as English merely
because an English translation was produced.

Read [references/workflow-state.md](references/workflow-state.md) in full before creating, verifying, or resuming an internal chapter workspace, and follow it throughout the chapter workflow.

For an existing active chapter, verify the required internal artifacts, then resume from the last verified workflow phase without repeating settled work.

Before starting the full chapter workflow, confirm access to the complete original-language chapter. If it cannot be located, ask the user to provide it. Do not perform whole-chapter analysis, passage division, two-path drafting, or finalization from a translation, summary, or incomplete excerpt in place of the original. An isolated passage may be translated only provisionally, as described under **Establish Chapter Context**.

Treat `glossary.md` and `voice.md` as living project state. Record user-approved or corrected terminology in `glossary.md` and durable voice or cultural-transfer decisions in `voice.md` promptly rather than leaving binding decisions only in chat history. Pin every voice entry to a character or narrator, chapter, and place; preserve earlier entries when the voice later changes.

Initialize both files as ordinary UTF-8 Markdown artifacts during project setup and keep them directly editable by the user. Reread their current on-disk contents when starting or resuming work and before each chapter. Treat direct user edits as binding; preserve user-added content and merge updates locally rather than regenerating or silently overwriting either file.

## Establish Chapter Context

Obtain:

- the complete source chapter;
- prior translated text and established decisions when available;
- `glossary.md` and its established names and terminology;
- glossary-defined relational terms and any approved context-dependent or asymmetric renderings;
- `voice.md` and the profiles pinned to the current character or narrator, chapter, and place;
- any benchmark translation defining the target English style.

If the user supplies only one isolated passage and no chapter context, translate it provisionally or request the complete chapter before fixing context-sensitive choices.

During discovery, determine whether dialect, oral storytelling, folklore, culturally specific humor, kinship language, ritual language, social hierarchy, code-switching, or changing regional and historical registers materially shape the work. When they do, read [references/cultural-voice-and-dialect.md](references/cultural-voice-and-dialect.md) in full and apply it throughout analysis, drafting, review, and finalization. Do not map a source dialect automatically onto a named target-language dialect.

Consult the immediately preceding completed English chapter when one exists. Consult other source chapters or prior translations only when the current chapter contains a specific continuity dependency, such as established terminology, recurring phrasing, a deliberate echo or motif, character knowledge or voice, chronology, or withheld information. Inspect only enough context to resolve that dependency; do not perform a full cross-chapter review by default. Use previous English translations to preserve continuity, but let the original source control whenever they conflict.

## Step 1: Read the Complete Chapter

Read the chapter before sustained passage translation. Produce a concise chapter translation brief covering:

1. **Chapter essence** — narrative purpose and the change achieved.
2. **Emotional arc** — dominant mood, pressure, turns, and ending state.
3. **Viewpoint and distance** — focal character, narrative access, tense, and shifts.
4. **Character dynamics and voices** — intentions, relationships, subtext, power, register, and rhetorical behavior.
5. **Structure and rhythm** — scenes, pacing, tonal turns, parallels, and contrasts.
6. **Continuity** — established terms, recurring images, repeated wording, and cross-chapter echoes.
7. **Ambiguities and risks** — withheld information, degrees of certainty, cultural or technical issues, and likely translation distortions.
8. **Voice and cultural movement** — the applicable character-or-narrator × chapter × place entries from `voice.md`, socially or culturally marked language, oral or folkloric structures, and any change within the chapter.

Keep the brief concise and decision-oriented. Record only chapter-level observations that will affect passage boundaries, wording, voice, continuity, or review. Do not analyze individual sentences or draft translation yet.

## Step 2: Map the Chapter into Passages

Read [references/passage-division.md](references/passage-division.md) in full before creating the passage map or changing a boundary.

Divide the chapter into the largest coherent units that remain manageable for close translation and review. Read the sibling [review-approval-sheet skill](../review-approval-sheet/SKILL.md) in full. Persist the complete proposed map in `passage-map.md` and its synchronized revision-bound interface in `passage-map-review.json`, with one stable `PM###` item for each passage unit and its closing boundary, including one item when the complete chapter remains a single passage. Validate and render the interactive sheet, then stop at this human gate; do not extract source passages or begin Step 3 until every map item is resolved and the user separately confirms final closure of the complete current map.

Treat questions, qualifications, counterproposals, and requests to move, merge, or split boundaries as negotiation, not approval. Parse any interactive response against the saved revision, apply the translation domain rules, then redo Step 2 using the user's feedback: regenerate the complete proposed map and interface, increment the revision, invalidate affected boundary approvals and final closure, and present the complete current map again. Repeat until all current boundaries are individually resolved and the separate closure is confirmed. Do not treat silence, “continue,” a correction itself, or approval of only one boundary as approval of the whole map.

### Prepare the Internal Passage Set

Only after explicit approval, mark the current passage map approved and extract every source passage according to [references/workflow-state.md](references/workflow-state.md). Do this automatically; do not wait for the user to copy passages manually. Use the saved source files—not reconstructed chat excerpts—as inputs to the later loop.

Do not begin Step 3 until the current complete map is explicitly approved and the corresponding internal passage set exists and passes the reference's exact-once validation.

## Step 3: Repeat for Each Passage

Load the current numbered source-passage file. Do not translate beyond it unless requested. Carry the chapter brief, finalized preceding passage, terminology, and user decisions forward.

### Step 3.1: Create the Provisional Translation

Create two internal translation drafts independently before consolidating them.

#### Path A: Fidelity-First Translation Tryout

Translate the complete passage into readable English while preserving as much of the source information and communicative structure as possible. Produce continuous English prose, not notes, glosses, or a word-for-word crib. Some sentences may sound translated when staying close to the source helps expose information or relationships that a more natural rendering might lose. Account for:

- explicit facts and logical relations;
- implication and withheld information;
- certainty, ambiguity, and emphasis;
- viewpoint and narrative distance;
- imagery, sensory detail, and meaningful repetition;
- emotional relations, tone, register, and character voice.
- culturally and socially marked effects, oral logic, forms of address, folk structures, and deviations from the applicable pinned voice entry when the cultural-voice module is active.

Path A is a diagnostic translation tryout, not the final prose model. Keep it readable, but tolerate limited source-shaped phrasing when it makes omissions, ambiguities, emphasis, or interpretive shifts easier to detect. Do not make it awkward merely to imitate source-language syntax.

#### Path B: Direct Literary Translation

Translate the complete passage directly from the source and chapter context without reusing or referring to Path A's wording. Prioritize natural syntax, idiom, cadence, dialogue, local register, reader effect, and fit with the chapter brief. When the cultural-voice module is active, implement the applicable target-voice strategy from `voice.md` without forcing sameness across different characters or narrators, chapters, or places.

#### Refine Path B

Use Path B as the base text. Audit it against Path A and the source. Revise Path B wherever the audit reveals lost or altered information, implication, ambiguity, imagery, logic, viewpoint, emphasis, tone, cultural position, social relation, oral effect, or applicable voice movement.

Do not average the drafts, stitch them together, or replace natural Path B phrasing merely because Path A follows the source surface more closely. Recast each necessary correction within Path B's unified English prose.

> Path B supplies the prose. Path A supplies the fidelity benchmark. The source decides every disagreement.

The refined Path B is the provisional translation. Do not show raw Path A or the unrefined Path B unless the user explicitly requests them. Resolve interpretive conflicts internally during Step 3.1: preserve source ambiguity where possible, choose the best-supported provisional wording, and carry any meaningful unresolved choice into Step 3.2. Do not interrupt the completion gate to present alternatives or request a decision.

#### Mandatory Step 3.1 Completion Gate

Treat Step 3.1 as an indivisible prerequisite for Step 3.2. For the complete current passage, finish all four operations in order:

1. Path A: complete fidelity-first translation tryout;
2. Path B: independent direct literary translation;
3. source-grounded audit of Path B against Path A;
4. one refined Path B covering the entire passage.

Do not begin editorial review, present alternatives, label anything a decision, or ask the user to choose wording until all four operations are complete. Sentence-level alternatives do not substitute for the two-path process; both paths must address the complete passage.

Save and verify the refined full-passage provisional checkpoint, then initialize its review state, according to [references/workflow-state.md](references/workflow-state.md).

Reread the saved checkpoint, then show the user its complete translation text exactly as saved before raising the first editorial issue. Never display an unsaved provisional draft or alter the text while displaying it.

Immediately after the draft, state:

> Step 3.1 is complete for Passage [number]. The full provisional translation above has been produced through two-path drafting and consolidation and saved as the passage checkpoint. I am now beginning Step 3.2.

Do not make this statement unless the checkpoint exists and contains the displayed refined draft.

When resuming after an interruption, apply the reference's recovery rules. If the checkpoint is missing, incomplete, or not the refined full-passage draft, resume or restart Step 3.1. Do not proceed directly to editorial review.

### Step 3.2: Conduct an Independent Translation Editorial Review

Reset the process. Treat the provisional translation simply as an English draft. Set aside Path A and Path B; do not cite or continue reconciling them.

Use the source as the sole authority. The chapter brief and established continuity supply context but cannot override it.

#### Build the Review Ledger

Review the complete source passage and provisional translation once for both source fidelity and English prose. Check meaning, logic, implication, ambiguity, emphasis, viewpoint, tone, revelation, naturalness, idiom, cadence, voice, dialogue, and coherence. When the cultural-voice module is active, also check cultural density, social positioning, oral performance, forms of address, folk logic, character differentiation, and the character-or-narrator × chapter × place entry recorded in `voice.md`. Natural English may rearrange syntax, but must not add, remove, explain, intensify, soften, normalize, exoticize, or reorder information in a way that changes the reader's experience.

Correct objective errors directly when only one credible correction exists, including grammar, reference, clear mistranslation or omission, unjustified addition, broken logic, inconsistent terminology, or accidental viewpoint, tense, or certainty shifts. Save those corrections to the provisional checkpoint before freezing the ledger.

Create a fixed, source-ordered issue ledger only for choices where defensible alternatives would create materially different reader effects or change characterization, culpability, intimacy, certainty, emotional force, implication, or revelation. Persist it according to [references/workflow-state.md](references/workflow-state.md). For each issue, record:

- decision number;
- a stable source location and the exact original-language excerpt corresponding to the problem;
- the exact current English sentence or segment that is problematic;
- a concise editorial question;
- status: `pending`, `current`, `settled`, or `withdrawn`.

Order issues by first occurrence in the source and set both the workflow phase and current passage status to `reviewing`. If the ledger is empty, mark the cursor `passage-end` and proceed directly to **Finalize the Passage**.

#### Review the Ledger Once

When the fixed ledger contains multiple independent decisions that are understandable from their paired source and English spans, create or update synchronized `issue-review.json` interface state and render the shared approval sheet. Put the exact **Original** and **Current translation**, source effect, problem, alternatives, recommendation, and dependency information in each item's labeled details. The user may submit any explicitly decided subset. Parse it against the saved revision and apply settled decisions in source order. If an issue depends on an earlier answer, requires discussion, or cannot be captured safely as a deterministic option, use the single-issue dialogue below instead. Never batch dependent choices as though they were independent.

Present only the earliest pending issue. Give:

1. a paired display labeled **Original** and **Current translation**, quoting the exact original-language excerpt and the exact problematic English sentence or segment from the saved checkpoint;
2. the source effect and the problem in the English;
3. concrete alternatives with distinct reader effects;
4. one recommendation and its decisive reason;
5. a request for the user's decision.

Always show this pair for every editorial decision, including after resuming an interrupted review. Do not replace the original with a back-translation, transliteration, summary, source anchor, or explanation. When source and English sentence boundaries do not align, quote the smallest exact spans that make the relationship clear, adding limited adjacent context from each text when necessary.

Do not invent alternatives or request a decision when the source, grammar, established terminology, or a prior binding decision permits only one credible correction.

Accept a revision-bound interactive disposition, selection, qualification, replacement wording, rejection of all options, source correction, defense of the current wording, revision of an earlier decision, question, or “continue” as a valid response. Then:

1. if the issue remains unresolved, answer the user and repeat the decision request;
2. if it is settled, apply the decision to the checkpoint and update `glossary.md` when terminology changes;
3. record the decision and briefly confirm the resulting wording or interpretation;
4. present the next pending issue in the same response, or proceed to finalization when none remain.

If the user explicitly revises an earlier decision, reopen only that item, apply the revision, and then resume from the prior cursor position.

After freezing the ledger, add a late issue only for:

- an objective source-fidelity, grammar, reference, continuity, or terminology error that cannot be corrected without a meaningful choice;
- a conflict introduced by an accepted revision; or
- a genuine finalization blocker that could not reasonably have been identified during the initial complete review.

Record why the late issue qualifies. Do not add late issues for optional style changes or marginal improvements. After every ledger item is `settled` or `withdrawn`, mark the cursor `passage-end` and proceed to finalization; do not rebuild the ledger or conduct another optional-issue scan.

#### Continue and Preserve State

Keep Step 3.2 active until the passage is finalized, the user explicitly pauses or changes tasks, or a genuine blocking ambiguity requires information. While it is active, every response must end by awaiting one clearly presented decision, presenting the finalized passage, or stating why the workflow is paused or blocked.

Persist checkpoint and review state according to [references/workflow-state.md](references/workflow-state.md). Update both before each user-facing response and apply the reference's recovery rules when resuming.

### Finalize the Passage

When the cursor reaches `passage-end`, including when the ledger was empty:

1. Verify that every ledger item is `settled` or `withdrawn`.
2. Apply all accepted decisions and leave unaffected wording unchanged.
3. Read the passage continuously for cadence, transitions, tense, reference, and sound.
4. Compare it with the source, chapter brief, preceding text, terminology, and approved decisions.
5. Correct objective errors directly. If a meaningful choice is a qualified late blocker, resolve only that blocker through dialogue and return immediately to finalization. Do not reopen optional wording or conduct a second stylistic review.
6. Save and assemble the finalized passage, and mark its state `finalized`, according to [references/workflow-state.md](references/workflow-state.md). Update `glossary.md` for terminology or name decisions and `voice.md` for durable, scoped voice or cultural-transfer decisions. Append a new pinned entry rather than overwriting an earlier character-or-narrator × chapter × place state.
7. Present the final translation exactly as saved, add a short decision note only when it aids continuity, then stop and wait for the next passage.

## Complete the Chapter

Repeat Step 3 until the chapter ends or the user asks to pause or stop.

Do not begin chapter completion until the internal state satisfies the chapter-completion gate in [references/workflow-state.md](references/workflow-state.md).

When all passages are finalized:

1. Rebuild and verify the assembled chapter according to [references/workflow-state.md](references/workflow-state.md).
2. Conduct one complete chapter sanity check before making any further textual change:
   - Compare the complete assembled English chapter with the complete source chapter under the governing standard and verify consistency with `glossary.md`, the chapter brief, established continuity, and approved decisions.
   - Limit possible direct edits to grammar, punctuation, broken cross-passage syntax or references, tense and terminology consistency, missing or duplicated text, and objective content-integrity errors. Do not retranslate, stylistically polish, or alter sound sentences.
   - If a possible edit affects meaning, implication, ambiguity, imagery, characterization, voice, emphasis, repetition, cadence, emotional force, or an approved decision, exclude it from the sanity-check diff and return only the affected passage to Step 3.2. After that passage is finalized again, rebuild the chapter and restart the complete sanity check.
3. Freeze and persist the complete source-ordered sanity-check diff according to [references/workflow-state.md](references/workflow-state.md). For every proposed edit, give its location, current wording, proposed wording, and reason.
4. When edits are proposed, create or update synchronized `chapter-sanity-review.json` state with one stable `SC###` item per edit, validate and render the shared interactive sheet, and allow item-level acceptance, rejection, modification, or revision. Parse responses against the saved revision, update the complete diff, and keep final closure unavailable until every current item is resolved. If no edits are proposed, state **No textual changes proposed** and ask directly for approval to complete the chapter; an empty interface sheet is unnecessary. Stop at this human gate: do not apply proposed edits, save or overwrite the durable chapter file, declare the chapter complete, or move to the next chapter while approval is pending.
5. Treat questions, qualifications, replacement wording, or requests to add, remove, accept, reject, or revise edits as negotiation rather than approval of the complete diff. Resolve the feedback, redo the sanity check as needed, persist and present the complete revised diff and synchronized interface, and require separate final closure after all items are resolved. Partial approval does not clear the gate, and a correction or revision is not approval of its replacement.
6. After parsed final closure, apply only the accepted edits to both the affected passage checkpoints and the assembled chapter; leave rejected text unchanged. Rebuild and verify the assembled chapter, mark the sanity-check gate `approved`, and make no additional textual change outside the approved diff. If rebuilding reveals a new necessary edit, restart the sanity check and human gate.

Save the verified chapter as a durable Markdown file under `translated_english/`. Preserve the project's established filename for that chapter; otherwise derive a stable sortable filename from the source order, chapter number, and English chapter title, for example:

`00_chapter_1_new_year.md`

If the target already represents the same chapter, update it. If its chapter identity or version is ambiguous, ask the user before overwriting it. Never overwrite a file belonging to another chapter.

Reread the saved durable file, verify that it matches the assembled chapter, then present the complete saved translation and make the file available.

If the user asked to translate the full work or to continue, select the next untranslated chapter in source order and return to **Establish Chapter Context**. Carry forward `glossary.md`, `voice.md`, relevant decisions, prior completed English chapters, and any benchmark translation. Otherwise, stop after delivering the completed chapter.

## Operating Rules

- Keep uncertainty uncertain and implication implicit when the source does.
- Preserve focal knowledge; do not introduce judgments unavailable to the viewpoint character.
- Preserve deliberate repetitions and echoes without forcing identical English where the source meaning changes.
- Distinguish voices through syntax, register, directness, and rhetorical behavior, not conspicuous quirks.
- Preserve intentional voice development and code-switching; do not harmonize away changes pinned to character or narrator, chapter, or place.
- Prefer precise action, image, rhythm, and silence over explanatory emotional language.
- Make local fixes locally.
- Treat user-approved wording and qualifications as binding continuity decisions unless the user revises them.
