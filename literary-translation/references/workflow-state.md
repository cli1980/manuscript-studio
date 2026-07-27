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

Save each extracted source passage under `source-passages/`. Each file must contain:

1. a heading identifying the work, chapter, and passage number;
2. the exact source-language passage, preserving punctuation and paragraph breaks;
3. optional boundary or context metadata only when it aids navigation.

Do not translate, normalize, silently correct, or paraphrase the source text. Before Step 3, verify that the ordered source-text bodies, excluding headings and metadata, reproduce the complete chapter exactly once, with no missing, duplicated, or reordered text. Confirm that filenames, map entries, and passage order correspond.

## Passage Checkpoints

Use `provisional/passage-NN.md` as the single checkpoint for the passage's current English text. After Step 3.1, it contains the complete refined provisional translation. During Step 3.2, update that same file with objective corrections and accepted decisions. At passage finalization, it becomes the finalized passage checkpoint.

After every save, reread the checkpoint and verify that:

- every source paragraph is represented in order;
- no text is missing or duplicated;
- no unjustified information, implication, ambiguity, viewpoint, emphasis, or tone change has been introduced.

## Review State

Maintain `review-state.md` with:

- a passage-status table covering every mapped passage, using `unstarted`, `provisional`, `reviewing`, or `finalized`;
- the current passage number and workflow phase;
- the current checkpoint path and next action;
- the fixed Step 3.2 ledger with source locations and issue statuses;
- the current issue and cursor location;
- the last completed decision and any unresolved decision;
- any late blocker and why it qualifies.

When Step 3.1 finishes, mark the passage `provisional`, set the phase to `provisional`, and set the next action to `begin Step 3.2`. Do not create its issue ledger yet or remove records for earlier passages.

When Step 3.2 begins, set both the phase and passage status to `reviewing`. Update the checkpoint and state before every user-facing response. When the cursor reaches `passage-end` and the passage is finalized, mark the passage `finalized`.

## Assembled Chapter

Maintain `assembled/chapter.md` as the source-ordered assembly of finalized passage checkpoints. Insert or replace only the affected passage segment during passage finalization.

Do not begin chapter completion until every mapped passage has one finalized checkpoint and its passage-status entry is `finalized`.

Before chapter completion, rebuild the assembled chapter from all finalized checkpoints in passage-map order. Include only translation text, without passage headings or workflow metadata, and verify that every mapped passage appears exactly once with no missing, duplicated, or stale text.

## Resume and Recovery

When resuming, read and verify the passage map, relevant source passage, checkpoint, `review-state.md`, and assembled chapter before responding.

If chat history conflicts with saved state, reconstruct the workflow from the source files, saved checkpoints, and recorded user decisions. Do not skip or reopen settled issues. If a required checkpoint is missing, incomplete, or does not represent the expected full-passage phase, return to the phase that creates it rather than advancing.

The completed chapter under `translated_english/`, normalized source chapters, and `glossary.md` are durable project artifacts. Everything under `.literary-translation-work/` remains temporary internal workflow state.
