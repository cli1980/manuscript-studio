import type { RunDetail, RunSummary } from "./api";

// Per-workflow behavior of the studio's pages. The base class keeps everything on the run page; a workflow
// overrides only what differs (for literary translation: the chapter viewer is where a run is reviewed).

export class WorkflowUI {
  constructor(readonly workflow: string) {}

  /** Whether runs of this workflow have a chapter viewer to link to. */
  get hasChapterViewer(): boolean { return false; }

  /** The page where the run's pending decision is made, or null when it is made on the run page. */
  decisionPage(_run: RunDetail): string | null { return null; }

  /** Where to go right after starting a run. */
  landingPage(runId: string): string { return `#/runs/${runId}`; }

  /** Where lists and notices send the reviewer for a run's pending decision. */
  gateLink(run: RunSummary): string { return `#/runs/${run.id}`; }
}

const viewer = (runId: string, chapterId?: string | null) =>
  `#/runs/${runId}/chapters${chapterId ? `/${encodeURIComponent(chapterId)}` : ""}`;

/** Literary translation: every decision, from preparation questions to final acceptance, is made in the viewer. */
export class TranslationWorkflowUI extends WorkflowUI {
  override get hasChapterViewer() { return true; }

  override decisionPage(run: RunDetail) {
    if (run.status === "WAITING_FOR_HUMAN" && run.gate) return viewer(run.id, run.gate.chapter_id);
    if (run.status === "WAITING_FOR_ACCEPTANCE" && run.acceptance) return viewer(run.id);
    return null;
  }

  override landingPage(runId: string) { return viewer(runId); }

  override gateLink(run: RunSummary) { return viewer(run.id, run.gate_chapter_id); }
}

/** Manuscript formatting: one decision flow on a whole accepted version, so everything stays on the run page. */
export class FormattingWorkflowUI extends WorkflowUI {}

const WORKFLOWS: Record<string, WorkflowUI> = {
  "literary-translation": new TranslationWorkflowUI("literary-translation"),
  "format-manuscript": new FormattingWorkflowUI("format-manuscript"),
};

export function workflowUI(workflow: string | undefined | null): WorkflowUI {
  return (workflow && WORKFLOWS[workflow]) || new WorkflowUI(workflow ?? "");
}
