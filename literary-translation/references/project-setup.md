# Translation Project Setup

Use this procedure when starting a new literary translation project or when an existing project lacks normalized source files, a glossary, or output folders.

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
├── original_<source-language>/
└── translated_english/
```

These are durable, project-accessible artifacts.

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
- technical, cultural, religious, political, or worldbuilding terms;
- recurring objects, motifs, and phrases when consistent rendering matters.

Distinguish provisional mappings from user-approved mappings. Do not fabricate a confident mapping when context is insufficient.

Before sustained translation begins, show or summarize the proposed glossary and remind the user to review and update it. This reminder is advisory, not a mandatory pause, unless unresolved entries materially affect the chapter about to be translated.

Whenever the user corrects, approves, or replaces a mapping:

1. update `glossary.md` promptly;
2. preserve useful aliases or the former mapping in notes when needed for search and continuity;
3. apply the new decision prospectively;
4. check the active chapter for affected occurrences;
5. ask before retroactively changing already finalized chapters if the scope is not explicit.
