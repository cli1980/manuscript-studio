# SC-05 - Chapter viewer

**Current route:** `#/runs/:runId/chapters[/:chapterId]`

**Flows:** UF-06, UF-07, UF-08, UF-11, UF-12, UF-13, UF-15

**Implementation:** [Chapters.tsx](../../../studio/frontend/src/views/Chapters.tsx),
[workflow presentation](../../../studio/frontend/src/workflows.ts)

## Current contract

- The status bar shows progress and problems, linking to run management.
  Before preparation, the page shows preparation state or an active question.
- A chapter list navigates prepared units and their stage statuses.
  The front-matter unit hosts metadata and workflow-declared document reviews.
  Supplied titles disclose their origin and how to correct them.
- Translation panes show original and translation; editing shows current text.
  Only supported draft/document surfaces offer inline feedback. Manuscript
  text itself stays read-only.
- The viewer can show passage-map details, approved document snapshots, current
  glossary/voice documents, and applied consistency fixes.
- Chapter decisions follow the reading area. Unattached whole-book/pass
  decisions and final acceptance appear at the end of the content column.
  This position is scrolled into view once rather than moving the gate above text.
- Whole-book statuses appear in the list, but are not selectable `_whole`
  document routes. This is not yet a whole-book reader.

## Target boundary

See the [viewer design](../designs/studio-interface.md): selectable whole-book
reading, paragraph alignment, accepted-version content source, editing diffs,
and formatted-document preview remain targets. Workflow-specific consistency
presentation also still exists in this component, despite the abstraction target.

## Validation

Source-mapped. Existing [browser checks](../../../studio/tests/test_cases.py):
`test_whole_book_decision_follows_reading_area`,
`test_feedback_stays_with_its_review`. These are not new full editing E2E evidence.
