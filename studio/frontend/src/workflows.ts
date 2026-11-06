import type { ChapterDetail, Gate, RunDetail, RunSummary, Template } from "./api";
import { reviewName } from "./views/common";

// Per-workflow behavior of the studio's pages. The pages (chapter viewer, decision panel, run page, start forms)
// are generic; they ask the run's WorkflowUI what differs. The base class keeps everything on the run page;
// subclasses override only what their workflow does differently. This module holds behavior and data, no JSX.

/** One reading pane of the chapter viewer. */
export interface Pane {
  key: string;
  title: string;
  text: string | null;      // null shows the note instead
  note?: string;
  badge?: string;           // e.g. "awaiting your approval"
  meta?: string;            // e.g. attempt and hash
  awaiting?: boolean;
  // Inline comments can be drafted on this pane; they are sent as feedback on the pending decision.
  commentKey?: string;
  commentLabel?: string;    // how the feedback names the text, e.g. "the translation"
}

/** How a decision is presented: its heading, an optional explanation, and button labels for exact commands. */
export interface DecisionCopy {
  heading: string;
  intro?: string;
  commandLabels?: Record<string, string>;
}

/** The engine's ID for a whole-book job (e.g. a consistency pass); its decisions show at the top of the viewer. */
export const WHOLE_BOOK = "_whole";

const viewer = (runId: string, chapterId?: string | null) =>
  `#/runs/${runId}/chapters${chapterId && chapterId !== WHOLE_BOOK ? `/${encodeURIComponent(chapterId)}` : ""}`;

const sizeOf = (output: ChapterDetail["outputs"][number]) =>
  `${output.attempt != null ? `attempt ${output.attempt} · ` : ""}${output.sha256.slice(0, 10)}`;

export class WorkflowUI {
  constructor(readonly workflow: string) {}

  // ----- wording -------------------------------------------------------------------------

  /** Who answers the reviewer's feedback in this workflow's decisions. */
  get agentName(): string { return "agent"; }

  /** How the start form describes a run of this template. Stages chosen at a select stage run in its place. */
  stageSummary(template: Template): string {
    const options = new Set(Object.values(template.choices).flat().map((o) => o.stage));
    const stages = template.stages.filter((s) => !options.has(s)).map((s) => template.choices[s]
      ? `${s} (your choice of ${template.choices[s].map((o) => o.title.toLowerCase()).join(", ")})` : s);
    return `Stages: ${stages.join(" → ")}. Preparation runs first; the agent then works until it needs you.`;
  }

  /** Readable name of a stage, e.g. a pass's title. */
  stageTitle(run: RunDetail, stage: string): string { return run.stage_titles[stage] ?? stage; }

  /** What the agent is doing while a chapter of this stage is in progress. */
  stageVerb(_stage: string): string { return "in progress"; }

  // ----- where decisions are made ---------------------------------------------------------

  /** Whether runs of this workflow have a chapter viewer to link to. */
  get hasChapterViewer(): boolean { return false; }

  /** The page where the run's pending decision is made, or null when it is made on the run page. */
  decisionPage(_run: RunDetail): string | null { return null; }

  /** Where to go right after starting a run. */
  landingPage(runId: string): string { return `#/runs/${runId}`; }

  /** Where lists and notices send the reviewer for a run's pending decision. */
  gateLink(run: RunSummary): string { return `#/runs/${run.id}`; }

  // ----- decisions -------------------------------------------------------------------------

  decisionCopy(gate: Gate): DecisionCopy {
    return { heading: `Your review: ${reviewName(gate.kind)}${gate.chapter_id && gate.chapter_id !== WHOLE_BOOK ? ` · ${gate.chapter_id}` : ""}` };
  }

  /** The chapter status shown while a decision on it is pending. */
  awaitingLabel(gate: Gate): string {
    return gate.kind === "metadata_review" || gate.documents?.length > 0
      ? `awaiting your review: ${reviewName(gate.kind)}` : `awaiting your decision: ${reviewName(gate.kind)}`;
  }

  /** A notice after the reviewer's reply, e.g. that a chapter is approved; null for none. */
  afterReply(_gate: Gate, _text: string): string | null { return null; }

  // ----- chapter viewer --------------------------------------------------------------------

  /** The reading panes of a chapter. `gate` is the decision pending on this chapter, if any. */
  panes(chapter: ChapterDetail, _gate: Gate | null): Pane[] {
    return [
      { key: "source", title: "Original", text: chapter.prepared_text },
      ...chapter.outputs.map((o) => ({ key: o.stage, title: o.title ?? o.stage, text: o.text, meta: sizeOf(o) })),
    ];
  }
}

/** Workflows reviewed in the chapter viewer: every decision, from preparation questions to final acceptance, is
 *  made there, beside the text it concerns. Subclasses define their panes and decision wording. */
export class ChapterViewerWorkflowUI extends WorkflowUI {
  override get hasChapterViewer() { return true; }

  override decisionPage(run: RunDetail) {
    if (run.status === "WAITING_FOR_HUMAN" && run.gate) return viewer(run.id, run.gate.chapter_id);
    if (run.status === "WAITING_FOR_ACCEPTANCE" && run.acceptance) return viewer(run.id);
    return null;
  }

  override landingPage(runId: string) { return viewer(runId); }

  override gateLink(run: RunSummary) { return viewer(run.id, run.gate_chapter_id); }
}

/** Literary translation: two panes, the original beside the translation. The chapter approval presents the
 *  assembled draft in the translation pane, where inline comments are feedback. */
export class TranslationWorkflowUI extends ChapterViewerWorkflowUI {
  override get agentName() { return "translator"; }

  override stageVerb(stage: string) { return stage === "translate" ? "translating" : super.stageVerb(stage); }

  override decisionCopy(gate: Gate): DecisionCopy {
    if (gate.kind !== "chapter_sanity") return super.decisionCopy(gate);
    return {
      heading: `Approve ${gate.chapter_id}`,
      intro: gate.sheet ? "The final check proposes edits. Decide each one; the chapter is approved at closure."
        : "Read the translation beside the original, then approve it, or select text in the translation to comment on "
          + "it and send your comments (comments are feedback and do not approve the chapter).",
      commandLabels: { "approve chapter": "Approve chapter" },
    };
  }

  override awaitingLabel(gate: Gate) { return gate.kind === "chapter_sanity" ? "awaiting your approval" : super.awaitingLabel(gate); }

  override afterReply(gate: Gate, text: string) {
    // Only the approval command or the edit sheet's closure approves the chapter; item decisions do not.
    const approved = gate.kind === "chapter_sanity" && (gate.commands.includes(text) || text === gate.sheet?.submission.closure_command);
    return approved ? `${gate.chapter_id} is approved. Translation continues with the next chapter; you will be brought back `
      + "here when it is ready." : null;
  }

  override panes(chapter: ChapterDetail, gate: Gate | null): Pane[] {
    const source: Pane = { key: "source", title: "Original", text: chapter.prepared_text };
    if (gate?.kind === "chapter_sanity" && gate.binding_text != null) {
      return [source, { key: "draft", title: "Translation", text: gate.binding_text, badge: "awaiting your approval",
        awaiting: true, commentKey: gate.sheet ? undefined : `comments:${gate.id}:draft`, commentLabel: "the translation" }];
    }
    const done = chapter.outputs.map((o) => ({ key: o.stage, title: "Translation", text: o.text, meta: sizeOf(o) }));
    return [source, ...(done.length ? done : [{ key: "translation", title: "Translation", text: null, note: "Not translated yet." }])];
  }
}

/** Manuscript formatting: one decision flow on a whole accepted version, so everything stays on the run page. */
export class FormattingWorkflowUI extends WorkflowUI {
  override get agentName() { return "formatter"; }
}

const EDITING_VERBS: Record<string, string> = { developmental: "developmental review", line: "line editing", copy: "copyediting" };

/** Literary editing: one pane, the text being edited (the original until a pass changes the chapter). The user
 *  chooses passes one at a time; pass choices and whole-book decisions show at the top of the viewer. */
export class EditingWorkflowUI extends ChapterViewerWorkflowUI {
  override get agentName() { return "editor"; }

  override stageVerb(stage: string) { return EDITING_VERBS[stage] ?? super.stageVerb(stage); }

  override stageSummary(template: Template) {
    const passes = Object.values(template.choices).flat().map((o) => o.title.toLowerCase());
    return `After preparation and metadata review you choose editing passes one at a time (${passes.join(", ")}), `
      + "in any order and as often as needed, and accept each pass's output. Final acceptance publishes the edited text.";
  }

  override panes(chapter: ChapterDetail): Pane[] {
    const edited = chapter.outputs.find((o) => o.stage === "current");
    return [edited
      ? { key: "text", title: "Text", text: edited.text, badge: "edited", meta: sizeOf(edited) }
      : { key: "text", title: "Text", text: chapter.prepared_text, meta: "original, not changed yet" }];
  }
}

const WORKFLOWS: Record<string, WorkflowUI> = {
  "literary-translation": new TranslationWorkflowUI("literary-translation"),
  "literary-editing": new EditingWorkflowUI("literary-editing"),
  "format-manuscript": new FormattingWorkflowUI("format-manuscript"),
};

export function workflowUI(workflow: string | undefined | null): WorkflowUI {
  return (workflow && WORKFLOWS[workflow]) || new WorkflowUI(workflow ?? "");
}
