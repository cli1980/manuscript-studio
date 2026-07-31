# Cultural Voice and Dialect Transfer

Use this module when dialect, oral storytelling, folklore, culturally specific humor, kinship language, ritual language, social hierarchy, code-switching, or changing regional and historical registers materially shape the source.

## Contents

1. Governing Aim
2. Activate and Diagnose
3. Resolve and Maintain `voice.md`
4. Design the Target Voice
5. Apply the Two-Path Workflow
6. Conduct the Voice and Culture Audit
7. Avoid Common Failure Modes

## Governing Aim

Reproduce the source voice's literary and social function rather than its surface linguistic features.

The target reader should perceive the same kind of speaker speaking from within the same kind of cultural and social world, with comparable distance, authority, intimacy, humor, roughness, restraint, and development.

Use readable English while preserving meaningful cultural distance. Do not make unfamiliarity disappear when it carries narrative, social, historical, religious, or emotional information.

## Activate and Diagnose

Before drafting, identify what makes the source marked relative to its surrounding language. Check:

- regional, rural, urban, class, generational, occupational, and historical speech;
- particles, ellipsis, repetition, topic-fronting, syntax, rhythm, and characteristic argument patterns;
- oral storytelling, folktale formulas, ritual speech, songs, sayings, proverbs, rhymes, and audience address;
- kinship terms, honorifics, self-reference, insults, politeness, taboo, and hierarchy;
- code-switching between formal, intimate, public, private, native, and adopted registers;
- culture-specific objects, institutions, beliefs, cosmologies, humor, and folk logic;
- narrator alignment with or distance from a character's speech;
- changes caused by chapter development or movement between places.

Describe the source effect before choosing English devices. Do not equate a source dialect with an English dialect merely because both are rural, working-class, old-fashioned, comic, or nonstandard.

## Resolve and Maintain `voice.md`

Treat `(character or narrator, chapter, place)` as the primary key for every voice entry.

Resolve the active voice in this order:

1. Match the exact character or narrator, chapter, and place.
2. If no exact entry exists, use an earlier entry for the same character or narrator and place only as provisional evidence.
3. Consult broader narrator, community, or project baselines for additional constraints, never as replacements for the pinned entry.
4. Create a new provisional pinned entry when the source shows a new voice or a meaningful change.

Use addressee, community, time, relationship state, social status, emotional pressure, disguise, and code-switching as secondary qualifiers within the primary-key entry.

Use this schema:

```markdown
# Voice Record

## Project Baseline
- Narrative distance and default register:
- Cultural-transfer policy:
- Prohibited false equivalents:

## Pinned Voice Entries
### Character or narrator | Chapter | Place
- Secondary qualifiers:
- Source evidence and effect:
- Target voice palette:
- Forms of address and cultural terms:
- Relational mappings: cite `glossary.md` only; record local voice effects here without duplicating the mapping.
- Continuity relationship to earlier entries:
- Status: observed | provisional | approved

## Evolution Index
- Character or narrator: Chapter/Place -> Chapter/Place — cause and effect of change
```

Append new entries; do not overwrite earlier scopes. A later voice does not invalidate an earlier voice. Do not retroactively harmonize finalized chapters unless the user explicitly approves that scope.

Record objective source observations without interrupting drafting. Mark target strategies provisional until they have been tested or approved. Record durable user decisions promptly.

## Design the Target Voice

Build a portable literary vernacular unless the source or user provides a justified English analogue.

Prefer a controlled palette of:

- sentence length, fragments, coordination, and breath groups;
- repetition, parallelism, topic-fronting, self-correction, and circular reasoning;
- contractions and limited nonstandard grammar not exclusive to one English-speaking region;
- diction shaped by age, occupation, education, intimacy, and social position;
- forms of address, self-reference, politeness, indirectness, and rhetorical behavior;
- concrete material vocabulary and culturally situated imagery;
- oral cadence, formulaic openings, audience cues, chants, and performable sayings.

Use conspicuous phonetic spelling and eye dialect rarely. Do not automatically turn Chinese dialect into Appalachian, Southern American, African American, Cockney, Yorkshire, Irish, or another named English dialect. Such substitutions import the wrong geography, history, class system, ethnicity, and stereotypes.

Preserve culture-specific terms when their unfamiliarity carries value and the scene supplies enough meaning. Translate directly when opacity adds nothing. Add unobtrusive context only when comprehension requires it. Use compensation only when a source effect cannot survive locally, and record the displaced effect in `voice.md`.

Resolve recurring kinship, ritual-kinship, hierarchical, and other relational terms through `glossary.md`. Preserve the relationship rather than forcing one English surface form in narration and every dialogue context. Use an approved asymmetric rendering when the glossary licenses it for the current speaker, addressee, and register. Let `voice.md` govern the local effect on intimacy, authority, or distance without duplicating the lexical mapping.

For puns, rhymes, proverbs, and folk formulas, preserve function and performance before surface form. Keep repetition or awkward folk logic when it characterizes the speaker. Do not correct a character's confident misconception merely to help the reader.

Control density. Marked voice should remain legible and cumulative, not become a puzzle in every sentence. Let narrator, character, and community registers differ when the source distinguishes them.

## Apply the Two-Path Workflow

### Path A

In addition to ordinary fidelity, identify every materially marked feature and its function. Preserve:

- who sounds marked to whom;
- the degree and direction of markedness;
- social and cultural relations carried by grammar or address;
- oral structure, performance, humor, and folk logic;
- deviations from the applicable pinned `voice.md` entry;
- the cause and scope of any new voice state.

Path A may retain limited source-shaped phrasing when it exposes an effect fluent English could erase.

### Path B

Draft independently from the source using the applicable pinned voice palette. Reproduce the distribution and movement of markedness rather than matching source features one for one.

Do not make all dialogue equally colloquial. Do not hold a character to an earlier chapter or place when the source shows change or code-switching. Keep the English prose unified even when voices differ.

### Consolidation

Use Path B as the prose base. Use Path A to detect cultural or vocal flattening, false English-dialect signals, misplaced register, normalized folk logic, lost social relations, or erased voice movement. Recast corrections within Path B's voice rather than inserting literal fragments mechanically.

## Conduct the Voice and Culture Audit

During Step 3.2, ask:

- Does the English match the correct character or narrator, chapter, and place entry?
- Does the target reader hear the same kind of speaker and social relationship?
- Has a culturally meaningful term been erased, overexplained, or exoticized?
- Does each relational term preserve the glossary-defined relationship even when its English realization changes by context?
- Has oral performance become neutral exposition?
- Have repetition, comic timing, folk logic, or patterned sound been polished away?
- Has a real English dialect falsely relocated the character?
- Have characters or communities become less differentiated than in the source?
- Has the narrator moved closer to or farther from a voice without source support?
- Has an intentional chapter or place change been treated as inconsistency and harmonized away?
- Does the passage remain legible as English literature?

Correct objective attribution and consistency errors directly. Put only materially different reader effects or voice strategies into the decision ledger. Record accepted durable strategies in `voice.md` under their exact primary key.

## Avoid Common Failure Modes

- Do not replace cultural equivalence with generic fluency.
- Do not preserve every particle or syntax feature mechanically.
- Do not use one permanent voice profile for a developing or traveling character.
- Do not assign one dialect to an entire place when the source contains multiple communities or registers.
- Do not use rustic spelling as a shortcut for rurality.
- Do not make folklore quaint, mystical, or explanatory when the source treats it as ordinary life.
- Do not replace source cosmology with an English-language cultural analogue merely because it is familiar.
- Do not erase kinship structure, hierarchy, or self-reference without weighing its social function.
- Do not confuse consistency with sameness across characters, chapters, or places.
