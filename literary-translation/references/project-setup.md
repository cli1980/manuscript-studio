# Translation Project Setup

Use this procedure when starting a new literary translation project or when an existing project lacks normalized source files, a glossary, a voice record, or output folders.

## 1. Locate the Original

Search available project files, attachments, Library content, and connected storage using the most direct file-search tool available. Search by work title, author, chapter title or number, source-language phrases, and likely filename variants.

Confirm that the located artifact is the original source rather than an earlier translation, synopsis, excerpt, or adaptation.

If the complete original-language source for the requested scope cannot be found, ask the user to provide it. The full chapter workflow requires at least the complete current chapter. An isolated excerpt may be translated only provisionally; do not substitute reverse translation or infer missing source text.

## 2. Inspect and Normalize Source Artifacts

Inventory the supplied source artifacts and determine:

- file type and source language;
- whether the work is already chapter-separated;
- chapter order, numbering, and titles;
- whether extraction preserves paragraphs, punctuation, dialogue, notes, and section breaks;
- whether OCR errors or missing pages require user attention.

If a single PDF, DOC, or DOCX contains multiple chapters:

1. Use the appropriate document or PDF workflow to extract its text.
2. Identify real chapter boundaries from headings and structure, not arbitrary length.
3. Save each chapter as a separate UTF-8 Markdown file.
4. Preserve source wording, punctuation, paragraph breaks, and order.
5. Do not silently modernize, correct, translate, or normalize the literary text.
6. Compare the extracted files with the artifact and resolve material extraction errors before translation.

Use:

- `original_chinese/` when the source is Chinese;
- `original_<source-language>/` otherwise, using a short lowercase language name such as `original_japanese/` or `original_spanish/`.

Use stable sortable filenames that preserve chapter order, for example:

- `00_chapter_1_新年.md`
- `01_chapter_2_异梦.md`

If the project already has a consistent source naming convention, preserve it.

## 3. Prepare Durable Project Structure

Ensure the project contains:

```text
project/
├── glossary.md
├── voice.md
├── original_<source-language>/
└── translated_english/
```

These are durable, project-accessible artifacts.

Create both `glossary.md` and `voice.md` as UTF-8 Markdown files during initialization, even when only their headings or baseline schemas can be populated. Never leave either artifact only in chat history or internal workflow state.

Treat both files as user-editable project sources of truth. Reread their current on-disk contents when starting or resuming work and before beginning each chapter. Treat direct user edits as binding unless they are ambiguous or conflict with another explicit user decision. Preserve user-added fields, comments, organization, and unsupported entries; merge skill-generated updates locally instead of regenerating or silently overwriting either file.

## 4. Create or Load the Glossary

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

## 5. Create or Load the Voice Record

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
