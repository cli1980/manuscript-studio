# Internal Workflow State

Use this specification for every active chapter. It defines the temporary artifacts, their contents, and the state required to pause and resume safely.

## Working Layout

Store chapter workflow state under:

```text
.literary-translation-work/<work>/<chapter>/
├── passage-map.md
├── source-passages/
│   ├── passage-01.md
│   └── passage-02.md
├── provisional/
│   ├── passage-01.md
│   └── passage-02.md
├── review-state.md
├── chapter-sanity-review.md
└── assembled/
    └── chapter.md
```

Use stable, zero-padded passage numbers consistently across the map, source files, checkpoints, and state table.

These artifacts are internal workflow state. Do not save them to the user's Library, treat them as deliverables, announce them as created artifacts, or present links to them unless the user asks to inspect them. Retain them while the chapter is active or paused. They may be discarded after the chapter is completed or the user abandons the workflow.

## Passage Map and Source Files

Save `passage-map.md` in the chapter working folder. For every passage, record:

- its zero-padded number and source filename;
- its opening and closing source words;
- the structural reason for the boundary.

Also record the map's approval status as `pending` or `approved`. While approval is pending, the map is a proposal: do not create or update `source-passages/`, initialize passage checkpoints, or begin Step 3. If the user negotiates any boundary, redo Step 2, replace the pending proposal with the complete revised map, and request explicit approval again. Record `approved` only after the user approves the current complete map.

Save each extracted source passage under `source-passages/`. Each file must contain:

1. a heading identifying the work, chapter, and passage number;
2. the exact source-language passage, preserving punctuation and paragraph breaks;
3. optional boundary or context metadata only when it aids navigation.

Do not translate, normalize, silently correct, or paraphrase the source text. Extract source-passage files only from an approved map. Before Step 3, verify that the ordered source-text bodies, excluding headings and metadata, reproduce the complete chapter exactly once, with no missing, duplicated, or reordered text. Confirm that filenames, map entries, passage order, and the approved map correspond.

## Passage Checkpoints

Use `provisional/passage-NN.md` as the single checkpoint for the passage's current English text. After Step 3.1, it contains the complete refined provisional translation. During Step 3.2, update that same file with objective corrections and accepted decisions. At passage finalization, it becomes the finalized passage checkpoint.

After every save, reread the checkpoint and verify that:

- every source paragraph is represented in order;
- no text is missing or duplicated;
- no unjustified information, implication, ambiguity, viewpoint, emphasis, or tone change has been introduced.
- no applicable cultural position, social relation, oral effect, or pinned `(character or narrator, chapter, place)` voice has been flattened, exaggerated, or assigned to the wrong scope.

## Review State

Maintain `review-state.md` with:

- the current passage-map approval status;
- a passage-status table covering every mapped passage, using `unstarted`, `provisional`, `reviewing`, or `finalized`;
- the current passage number and workflow phase;
- the current checkpoint path and next action;
- the applicable `voice.md` primary keys and any provisional new or changed `(character or narrator, chapter, place)` entry discovered in the current passage;
- the fixed Step 3.2 ledger with source locations, exact original-language excerpts, exact problematic English sentences or segments, and issue statuses;
- the current issue and cursor location;
- the last completed decision and any unresolved decision;
- any late blocker and why it qualifies.

When Step 3.1 finishes, mark the passage `provisional`, set the phase to `provisional`, and set the next action to `begin Step 3.2`. Do not create its issue ledger yet or remove records for earlier passages.

When Step 3.2 begins, set both the phase and passage status to `reviewing`. Update the checkpoint and state before every user-facing response. When the cursor reaches `passage-end` and the passage is finalized, mark the passage `finalized`.

## Assembled Chapter

Maintain `assembled/chapter.md` as the source-ordered assembly of finalized passage checkpoints. Insert or replace only the affected passage segment during passage finalization.

Do not begin chapter completion until every mapped passage has one finalized checkpoint and its passage-status entry is `finalized`.

Before chapter completion, rebuild the assembled chapter from all finalized checkpoints in passage-map order. Include only translation text, without passage headings or workflow metadata, and verify that every mapped passage appears exactly once with no missing, duplicated, or stale text.

Maintain `chapter-sanity-review.md` for the completion gate. Record:

- status: `not-started`, `pending`, or `approved`;
- the assembled chapter version or checksum reviewed;
- the complete source-ordered proposed-edit diff, with location, current wording, proposed wording, reason, and user disposition;
- an explicit `No textual changes proposed` entry when the diff is empty;
- unresolved user feedback and the next action;
- the user's explicit approval of the complete current diff.

Set the status to `pending` before presenting the diff. Do not apply proposed edits, write or overwrite the durable chapter file, declare completion, or advance to another chapter while it is pending. If the user negotiates any item, redo the sanity check as needed, replace the prior proposal with the complete revised diff, and request explicit approval again. Rebuilding or otherwise changing the assembled chapter invalidates any earlier approval unless the change consists only of applying the exact approved diff.

After explicit approval, apply only approved edits to the affected checkpoints, rebuild the assembled chapter, verify it, and mark the matching sanity review `approved`. If verification identifies another necessary edit, set the gate back to `pending` and present a new complete diff. Durable chapter output requires an `approved` sanity review matching the assembled chapter.

## Resume and Recovery

When resuming, read and verify `glossary.md`, the applicable `voice.md` entries, the passage map and its approval status, relevant source passage, checkpoint, `review-state.md`, `chapter-sanity-review.md` when chapter completion has begun, and assembled chapter before responding. If map approval is pending or cannot be verified, resume at the Step 2 human gate; do not extract passages or enter Step 3. If the chapter sanity review is pending, resume at its human gate by presenting the complete current diff and requesting explicit approval; do not deliver the durable chapter or advance.

If chat history conflicts with saved state, reconstruct the workflow from the source files, saved checkpoints, and recorded user decisions. Do not skip or reopen settled issues. If a required checkpoint is missing, incomplete, or does not represent the expected full-passage phase, return to the phase that creates it rather than advancing.

The completed chapter under `translated_english/`, normalized source chapters, `glossary.md`, and `voice.md` are durable project artifacts. Everything under `.literary-translation-work/` remains temporary internal workflow state.
