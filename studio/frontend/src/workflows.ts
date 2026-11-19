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
  // The exact bound text shown for this decision; other panels may link here instead of repeating it.
  reviewTarget?: string;
  // Inline comments can be drafted on this pane; they are sent as feedback on the pending decision.
  commentKey?: string;
  commentLabel?: string;    // how the feedback names the text, e.g. "the translation"
}

/** How a decision is presented: its heading, an optional explanation, and button labels for exact commands. */
export interface DecisionCopy {
  heading: string;
  intro?: string;
  message?: string;
  commandLabels?: Record<string, string>;
}

/** The engine's ID for a whole-book job (e.g. a consistency pass); its decisions show at the end of the viewer. */
export const WHOLE_BOOK = "_whole";

const viewer = (runId: string, chapterId?: string | null) =>
  chapterId && chapterId !== WHOLE_BOOK ? `#/runs/${runId}/chapters/${encodeURIComponent(chapterId)}`
    : `#/runs/${runId}/overview`;

export interface OverviewReviewGroup { title: string; kinds: string[] }

const sizeOf = (output: ChapterDetail["outputs"][number]) =>
  `${output.attempt != null ? `attempt ${output.attempt} · ` : ""}${output.sha256.slice(0, 10)}`;

export class WorkflowUI {
  constructor(readonly workflow: string) {}

  // ----- wording -------------------------------------------------------------------------

  /** Who answers the reviewer's feedback in this workflow's decisions. */
  get agentName(): string { return "agent"; }

  get frontMatterLabel(): string { return "Front Matter"; }
  get overviewReviewGroups(): OverviewReviewGroup[] { return []; }

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

  decisionCopy(gate: Gate, target?: RunSummary["viewer_target"]): DecisionCopy {
    const location = target?.kind === "overview" ? "Overview"
      : gate.chapter_id && gate.chapter_id !== WHOLE_BOOK ? gate.chapter_id : null;
    return { heading: `Your review: ${reviewName(gate.kind)}${location ? ` · ${location}` : ""}` };
  }

  /** The chapter status shown while a decision on it is pending. */
  awaitingLabel(gate: Gate): string {
    return gate.kind === "metadata_review" || gate.documents?.length > 0
      ? `awaiting your review: ${reviewName(gate.kind)}` : `awaiting your decision: ${reviewName(gate.kind)}`;
  }

  /** A notice after the reviewer's reply, e.g. that a chapter is approved; null for none. */
  afterReply(_gate: Gate, _text: string, _target?: RunSummary["viewer_target"]): string | null { return null; }

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
    if (run.production && run.status === "WAITING_FOR_ACCEPTANCE") return null;
    if (run.status === "WAITING_FOR_HUMAN" && run.gate) return this.gateLink(run);
    if (run.status === "WAITING_FOR_ACCEPTANCE" && run.acceptance) return viewer(run.id);
    return null;
  }

  override landingPage(runId: string) { return viewer(runId); }

  override gateLink(run: RunSummary) {
    return viewer(run.id, run.viewer_target?.kind === "chapter" ? run.viewer_target.chapter_id : null);
  }
}

/** Literary translation: two panes, the original beside the translation. The chapter approval presents the
 *  assembled draft in the translation pane, where inline comments are feedback. */
export class TranslationWorkflowUI extends ChapterViewerWorkflowUI {
  override get agentName() { return "translator"; }
  override get frontMatterLabel() { return "Front-matter translation"; }
  override get overviewReviewGroups(): OverviewReviewGroup[] {
    return [{ title: "Translation brief", kinds: ["brief_samples", "translation_brief"] }];
  }

  override stageVerb(stage: string) { return stage === "translate" ? "translating" : super.stageVerb(stage); }

  override decisionCopy(gate: Gate, target?: RunSummary["viewer_target"]): DecisionCopy {
    if (gate.kind === "translation_consistency") return {
      heading: "Whole-book consistency review",
      intro: "All chapters are translated. Review objective inconsistencies across the book. After closure, approved fixes "
        + "are applied and checked against the source before final acceptance.",
      commandLabels: { "confirm consistency": "Confirm no inconsistencies" },
    };
    if (gate.kind !== "chapter_sanity") return super.decisionCopy(gate, target);
    const front = target?.kind === "overview";
    return {
      heading: front ? "Approve front-matter translation" : `Approve ${gate.chapter_id}`,
      intro: gate.sheet ? `The final check proposes edits. Decide each one; the ${front ? "front matter" : "chapter"} is approved at closure.` : undefined,
      message: gate.sheet ? undefined : `No textual changes proposed. The ${front ? "front matter" : "chapter"} is ready for review. Approve it or send feedback.`,
      commandLabels: { "approve chapter": front ? "Approve front matter" : "Approve chapter" },
    };
  }

  override awaitingLabel(gate: Gate) { return gate.kind === "chapter_sanity" ? "awaiting your approval" : super.awaitingLabel(gate); }

  override afterReply(gate: Gate, text: string, target?: RunSummary["viewer_target"]) {
    // Only the approval command or the edit sheet's closure approves the chapter; item decisions do not.
    const approved = gate.kind === "chapter_sanity" && (gate.commands.includes(text) || text === gate.sheet?.submission.closure_command);
    return approved ? `${target?.kind === "overview" ? "Front matter" : gate.chapter_id} is approved. The workflow continues automatically; after all manuscript units are saved, `
      + "the whole-book consistency review starts here." : null;
  }

  override panes(chapter: ChapterDetail, gate: Gate | null): Pane[] {
    const source: Pane = { key: "source", title: "Original", text: chapter.prepared_text };
    if (gate && ["chapter_sanity", "translation_issue"].includes(gate.kind) && gate.binding_text != null) {
      const chapterApproval = gate.kind === "chapter_sanity";
      return [source, { key: "draft", title: chapterApproval ? "Translation" : "Translation under review",
        text: gate.binding_text, badge: chapterApproval ? "awaiting your approval" : "provisional text",
        awaiting: true, reviewTarget: "reviewed-translation",
        commentKey: chapterApproval && !gate.sheet ? `comments:${gate.id}:draft` : undefined,
        commentLabel: "the translation" }];
    }
    const done = chapter.outputs.map((o) => ({ key: o.stage, title: "Translation", text: o.text, meta: sizeOf(o) }));
    return [source, ...(done.length ? done : [{ key: "translation", title: "Translation", text: null, note: "Not translated yet." }])];
  }
}

const EDITING_VERBS: Record<string, string> = { developmental: "developmental review", line: "line editing", copy: "copyediting" };

/** Literary editing: one pane, the text being edited (the original until a pass changes the chapter). The user
 *  chooses passes one at a time; pass choices and whole-book decisions show at the end of the viewer. */
export class EditingWorkflowUI extends ChapterViewerWorkflowUI {
  override get agentName() { return "editor"; }
  override get frontMatterLabel() { return "Front-matter editing"; }

  override decisionCopy(gate: Gate, target?: RunSummary["viewer_target"]): DecisionCopy {
    return gate.kind === "interior_design_review"
      ? { heading: "Review formatting specification" } : super.decisionCopy(gate, target);
  }

  override stageVerb(stage: string) { return EDITING_VERBS[stage] ?? super.stageVerb(stage); }

  override stageSummary(template: Template) {
    const passes = Object.values(template.choices).flat().map((o) => o.title.toLowerCase());
    return `Using the selected prepared Work version, choose editing passes one at a time (${passes.join(", ")}), `
      + "in any order and as often as needed, and accept each pass's output. Finish editing and approve the manuscript; "
      + "the final formatting phase then starts automatically with interior design and its editable specification review. "
      + "Review the generation plan, download the checked editable DOCX and accept it to finish. PDF and rendered-page checks are deferred.";
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
};

export function workflowUI(workflow: string | undefined | null): WorkflowUI {
  return (workflow && WORKFLOWS[workflow]) || new WorkflowUI(workflow ?? "");
}
