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

Before sustained translation begins, show or summarize the proposed glossary and remind the user to review and update it. This reminder is advisory, not a mandatory pause, unless unresolved entries materially affect the chapter about to be translated.

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
