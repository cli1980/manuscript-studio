# SC-02 - Work details

**Current route:** `#/works/:workId`

**Flows:** UF-02, UF-03, UF-04, UF-05, UF-09, UF-10, UF-14

**Implementation:** [Works.tsx](../../../studio/frontend/src/views/Works.tsx)

## Current contract

- Show identity/language/owner, an original-source download, and origin/derived
  work links when present.
- Before the first run, offer author details. Work metadata remains editable
  while no run is unfinished; each save includes rationale and a new revision.
- Offer direct workflow start when free. Its Advanced panel exposes a
  translation template's passage-size setting; the dashboard form does not.
- Show latest accepted workflow summaries, a run table, metadata and revision
  count, a flat artifact list with read-only content, and the publication log.
- Format as DOCX selects an accepted version, previews run/manifest provenance,
  chapter titles/size and decisions, then chooses Word or LibreOffice.
- Hide/disable conflicting starts while a run is unfinished. Loading,
  artifact, metadata, and formatting errors must remain distinguishable.

## Target boundary

The [explorer target](../designs/studio-interface.md) separates overview,
versions, runs, and library/log; adds workflow/version hierarchy, accepted-version
downloads/reading, source preview, and metadata-version comparison. Current
revision counts and publication rows do not implement those comparison/readers.

## Validation

Source-mapped only for this baseline.
[Original-download API test](../../../studio/tests/test_web.py):
`test_original_upload_downloads_under_its_name`.
