# Translation Project Setup

Use this procedure when starting a translation project or when its prepared-source
handoff, glossary, voice record, or output folders are missing.

## 1. Obtain the prepared manuscript

Read the sibling [prepare-manuscript skill](../../prepare-manuscript/SKILL.md) and
its [preparation contract](../../prepare-manuscript/references/preparation-contract.md).
Obtain the user's specific source location and requested work/chapter scope.
Delegate discovery, extraction, and verification to that skill, or reuse an
unchanged verified package. Do not search outside the designated source location.

Require a valid `work.json` with preparation `ready` and a verified revision
containing the complete requested original-language chapters. Resolve chapter
paths from the revision manifest and follow its order and stable chapter IDs.
Do not translate from a summary, earlier translation, edited workspace copy, or
incomplete extraction in place of the original.

Keep the prepared package outside the translation project's workflow/output
folders. Never modify its source chapters while translating. If a source error
or changed original is discovered, return it to preparation and bind subsequent
work to a newly verified revision. Do not silently carry old approvals to new text.

An isolated excerpt may still be translated provisionally under the main skill's
context rules; it does not become a ready prepared chapter.

For legacy `original_chinese/` or `original_<language>/` projects, follow the
shared migration procedure. Preserve existing files and user decisions, verify
them against the designated original, and record the new source binding without
silently renaming or deleting user files.

## 2. Prepare Translation-Specific Project Structure

Ensure the project contains:

```text
project/
├── glossary.md
├── voice.md
├── brief-samples.md      # created by the translation brief (section 5)
└── translated_english/
```

These are durable, project-accessible artifacts.

The chapter source lives in the neutral prepared package, not in a second
translation-owned extraction tree. Record its `work.json` locator, revision, and
active chapter ID in internal review state. Maintain only the
`workflows.literary-translation` summary in the work record, with the actual
translation project/state locator and the operation's chapter scope.

Create both `glossary.md` and `voice.md` as UTF-8 Markdown files during initialization, even when only their headings or baseline schemas can be populated. Never leave either artifact only in chat history or internal workflow state.

Treat both files as user-editable project sources of truth. Reread their current on-disk contents when starting or resuming work and before beginning each chapter. Treat direct user edits as binding unless they are ambiguous or conflict with another explicit user decision. Preserve user-added fields, comments, organization, and unsupported entries; merge skill-generated updates locally instead of regenerating or silently overwriting either file.

## 3. Create or Load the Glossary

If `glossary.md` exists, read it before translating. If it does not, create it from the original and any reliable prior translations.

Include only recurring or continuity-sensitive items:

| Source | Default English | Type | Notes/Status |
|---|---|---|---|
| source form | chosen mapping | person/place/term/title | provisional, approved, context limits, aliases |

Record:

- character names and aliases;
- place and organization names;
- ranks, titles, forms of address, and invented institutions;
- recurring kinship, ritual-kinship, hierarchical, and other relational terms;
- technical, cultural, religious, political, or worldbuilding terms;
- recurring objects, motifs, and phrases when consistent rendering matters.

### Record Relational Terms

Use a relational glossary entry when a source term identifies a durable relationship but its natural English realization changes between narration, reference, and direct address.

```markdown
### Source relational term or reciprocal pair
- Core relationship and social function:
- Narrative default:
- Direct-address renderings:
- Speaker/addressee or register qualifiers:
- Accepted asymmetric rendering: yes | no
- Status: provisional | approved
```

Preserve the underlying relationship even when the English surface form changes. A reciprocal pair does not need mechanically reciprocal English if that would make dialogue unnatural. Record the permitted asymmetry explicitly, including which speaker, addressee, register, or narrative context licenses each rendering.

Keep the lexical decision in `glossary.md`. A pinned `voice.md` entry may cite the glossary relationship and describe its local effect on intimacy, authority, distance, or register, but must not duplicate or silently replace the mapping.

Distinguish provisional mappings from user-approved mappings. Do not fabricate a confident mapping when context is insufficient.

Before sustained translation begins, present the proposed glossary and voice record for review as described in **Translation Brief Review** below.

Whenever the user corrects, approves, or replaces a mapping:

1. update `glossary.md` promptly;
2. preserve useful aliases or the former mapping in notes when needed for search and continuity;
3. apply the new decision prospectively;
4. check the active chapter for affected occurrences;
5. ask before retroactively changing already finalized chapters if the scope is not explicit.

## 4. Create or Load the Voice Record

If `voice.md` exists, read it before chapter analysis. If it does not, create it during discovery. Keep it concise when the work's voice is relatively uniform and expand it when voice, dialect, culture, or social register materially affects translation.

Use `voice.md` as durable, evolving project state. Record source effects and approved target-language strategies rather than prescriptive rewrites detached from source evidence.

Every entry must include:

- **Character or narrator** — the speaker, viewpoint, narrator, or defined community voice;
- **Chapter** — a stable chapter number or identifier;
- **Place** — the scene location or a stable location identifier;
- **Source evidence and effect** — the marked features and what they communicate;
- **Target strategy** — the English voice palette, cultural handling, and prohibited false equivalents;
- **Status** — `observed`, `provisional`, or `approved`.

Treat `(character or narrator, chapter, place)` as the primary key. Use addressee, community, time, relationship state, social status, and emotional pressure as secondary qualifiers inside that pinned entry.

Append a new pinned entry when the voice changes. Do not overwrite an earlier entry or retroactively harmonize finalized text merely because the character later travels, enters another community, code-switches, changes relationships or status, undergoes pressure or trauma, or develops across the story.

When the source materially depends on cultural voice or dialect, read [cultural-voice-and-dialect.md](cultural-voice-and-dialect.md) before drafting the chapter.

## 5. Translation Brief Review

Before the first chapter of a whole-work translation, draft the translation
brief: `glossary.md` and `voice.md` as they should stand when translation starts,
and `brief-samples.md`, which tries them on sample passages.

1. Read the complete prepared manuscript in manifest order. Start from the
   existing files when present (carried from earlier work or edited by the user)
   and preserve their entries.
2. Record in `glossary.md` the recurring names and aliases, places, titles and
   forms of address, relational terms, and cultural or worldbuilding terms the
   chapters depend on. Mark new mappings `provisional`.
3. Record in `voice.md` the narrator and the main characters, each entry pinned
   to character or narrator, chapter, and place, with source evidence and target
   strategy. Mark new entries `provisional` or `observed`.
4. Pick three sample passages at random, spread across the work (from different
   chapters when there are several; never front matter), each one or two
   consecutive paragraphs, and record their locations.
   Translate each sample three ways following the drafted glossary and voice.
   Every variant must be faithful to the source; the variants differ only in
   target-language strategy, such as closeness to source structure, register,
   or rhythm. Save them in `brief-samples.md`: for each, the source, the
   variants labelled A–C, and one line on what distinguishes each variant.
5. Do not translate any chapter while drafting the brief; the samples are
   tryouts, not chapter output.
6. Present the three files with a short summary of the proposals and the open
   questions, and ask the user to choose the preferred variant for each sample,
   optionally with reasons for accepting it and for rejecting the others.
7. Record in `brief-samples.md`, for each sample, every variant marked
   accepted or rejected and the user's reasons in their own words. Add the
   target strategy the choices and reasons imply to the voice entries.
8. Present the updated brief and wait for the user's explicit approval. Treat
   any other reply as corrections: apply them and present the revised brief
   again.

The approved brief is the user-approved starting point for every chapter. Keep
approved entries unless the user changes them through a later decision, and keep
extending both files as chapters reveal new terms and voices. Keep
`brief-samples.md` as approved unless the user changes it. It sets the tone and
voice to start from, not a rule for later passages: the accepted variants show the
preferred direction, the rejected variants and reasons what to avoid, and each
passage's source and context still decide. No sample variant is a finalized
translation of its passage. When an
orchestrator runs the brief as its own review, it records the approval and
presents the files; follow its gate contract instead of asking in chat.
