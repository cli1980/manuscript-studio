# Manuscript Formatting Specification

## Contents

1. Purpose and authority
2. Edition profiles
3. Evidence-based design choices
4. Required specification schema
5. TOC and navigation
6. Readiness and invalidation

## Purpose and authority

Use this specification as the reusable bridge between manuscript meaning and format-specific construction. It controls presentation, not wording. Bind it to a manuscript identity, preserve user-approved exceptions, and keep measurements portable by recording both design intent and adapter-specific values.

Do not treat genre as a decorative stereotype. Use genre, work type, audience, narrative voice, structural density, and intended use together. A supplied publisher, contest, agent, school, or production template overrides general recommendations where it explicitly controls.

## Edition profiles

| Profile | Primary purpose | Typical treatment | TOC default |
|---|---|---|---|
| `submission` | Agent, publisher, contest, or evaluator intake | Restrained industry manuscript conventions; high editability; minimal decoration | Omit for ordinary fiction unless required; include for structured nonfiction or an explicit requirement |
| `editorial-review` | Author/editor collaboration and navigation | Highly readable body, visible hierarchy, stable page references, practical headers | Include when the work has chapters or named sections |
| `reader-facing` | Polished digital or printed reading copy | Designed typography, intentional chapter openings, controlled page furniture | Include when it materially aids navigation |

Never combine profiles silently. If the author wants both a standards-compliant submission and a designed edition, create two outputs from one shared structural map and record separate adapter overrides.

## Evidence-based design choices

### Typography

Choose a body face for sustained reading and a restrained display or companion face only when it improves hierarchy. Verify installed availability and rendering before approval.

- Literary fiction and memoir usually favor an unobtrusive serif with moderate contrast and generous rhythm.
- Commercial fiction favors speed and clarity; avoid typography that advertises itself more strongly than the prose.
- Narrative nonfiction may use a serif body with a clear heading companion and deeper hierarchy.
- Young-reader editions may require larger type, shorter measures, and more generous leading.
- Poetry requires glyph coverage and line-fit testing; never shrink or reflow globally to hide lineation problems.
- Plays and screenplays follow their controlling dramatic-format convention rather than a novel profile.

Record a primary font and at least one metric-compatible or visually acceptable fallback. Do not specify a commercial font unless licensing and availability are established.

### Paragraph model

Choose one main prose model:

- `first-line`: first-line indentation, normally no extra space between consecutive body paragraphs;
- `block`: no first-line indentation, with deliberate paragraph spacing;
- `special-form`: source-controlled lineation or layout for poetry, drama, letters, lists, quotations, code, or other exceptional material.

For first-line prose, record whether the first paragraph after a chapter title, section heading, or scene break is flush left. Preserve intentional fragments, one-line paragraphs, and scene rhythm.

### Geometry and rhythm

Derive page size, margins, line length, font size, leading, paragraph spacing, and hyphenation as one system. Avoid selecting each value independently. Record widow/orphan behavior, heading keep rules, and whether chapter openings start on a new page or recto.

### Page furniture

Record title-page treatment, copyright or edition notice, dedication/epigraph behavior, running heads, footer content, folio position, front-matter numbering, body numbering start, and blank-page policy. Suppress running heads and folios where the selected convention requires it.

### Structural and special content

Inventory chapters, parts, sections, appendices, acknowledgments, notes, figures, tables, captions, extracts, letters, and ornamental or semantic scene breaks. Define a named style for every recurring role. Do not use empty paragraphs, repeated spaces, manual tabs, or repeated glyphs as layout controls.

## Required specification schema

Save `format-spec.md` with these sections:

```markdown
# Manuscript Format Specification

## Identity and status
- Manuscript identity/fingerprint:
- Structural-map identity:
- Specification revision:
- Status: proposed | approved | invalidated
- Approval date and review revision:

## Edition intent
- Output format:
- Edition profile:
- Intended reader/use:
- Work type and genre:
- Style evidence:
- Controlling template or requirement:

## Page and section geometry
- Page size and orientation:
- Margins and gutter:
- Section-break rules:
- Chapter-start rule:

## Typography
- Body font, fallback, size, and color:
- Heading/chapter font system:
- Special-form fonts:
- Line spacing and baseline rhythm:

## Paragraph system
- Main prose model and indentation:
- Paragraph spacing:
- First paragraph after headings/breaks:
- Alignment and hyphenation:
- Widow/orphan and keep rules:
- Scene-break treatment:

## Hierarchy and navigation
- Structural levels and mapped source elements:
- TOC inclusion and depth:
- Dynamic or static-linked TOC method:
- Page-number and link verification method:

## Front matter, back matter, and page furniture
- Ordered components:
- Running heads and footers:
- Folio style and numbering transitions:

## Figures, tables, notes, and special forms
- Placement and wrapping:
- Caption and numbering system:
- Notes and cross-references:
- Accessibility requirements:

## Format adapter values
- DOCX-specific measurements or mechanics:
- PDF-specific exceptions:
- EPUB-specific exceptions:

## Approved exceptions and open items
## QA results and output identities
```

Use explicit values rather than “standard,” “normal,” or application defaults. Record units. Distinguish general design intent from output-specific implementation.

## TOC and navigation

Build the TOC from the approved structural hierarchy, never from visual appearance alone. Map source chapter and section identities to semantic heading levels before generation.

For DOCX:

- use real Word Heading styles or an equivalent outline level;
- define the included level range;
- prefer a refreshed dynamic TOC when field updating is available;
- otherwise create a static linked TOC with accurate displayed pages;
- audit missing, duplicated, truncated, or wrongly nested entries;
- verify that no placeholder remains.

For reflowable future formats, page numbers may be inappropriate. Preserve hierarchy and links while allowing the adapter to omit fixed-page references.

## Readiness and invalidation

The specification is `approved` only after every consequential design group resolves and the user closes the current revision. It is output-ready only when the requested format has a validated adapter and all required fonts, source components, and structural identities are available.

Invalidate navigation and pagination after any structural or textual change that can move content. Invalidate typography only when the governing requirement, approved design choice, font availability, or rendering result changes. Reuse all unaffected decisions.
