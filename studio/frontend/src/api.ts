// Typed client for the local workflow API. The server owns every rule; the UI only submits explicit choices.

export interface Action {
  action: string;
  enabled: boolean;
  reason: string | null;
  irreversible: boolean;
  confirmation: string | null;
}

export interface SheetDecision { id: string; command: string; label: string; requires_note: boolean; effect: string }
export interface SheetItem {
  id: string;
  chapter_id?: string;
  summary: string;
  details: { label: string; value: string }[];
  status: string;
  status_label?: string;
  allowed_decisions: string[];
}
export interface Sheet {
  sheet_id: string;
  revision: string;
  title: string;
  decisions: SheetDecision[];
  items: SheetItem[];
  gate: { closure_required: boolean; final_closure: string };
  submission: { instruction: string; rules: string[]; closure_command: string; closure_label: string };
}

export interface Gate {
  id: string;
  kind: string;
  message: string;
  stage: string;
  chapter_id: string | null;
  record_revision?: number;
  sheet: Sheet | null;
  commands: string[];
  binding_text: string | null;
  documents: { path: string; sha256: string; text: string }[];
  answer_to: { text: string; created_at: string } | null;
  // Engine-owned choices (e.g. accepting an editing pass, then choosing the next): each option is an exact reply.
  options?: GateOption[] | null;
  pass?: number | null;
}

export interface GateOption { command: string; title: string; description?: string | null; stage?: string; finish?: boolean }
export interface StageOption { stage: string; title: string; description?: string }
export interface Pass { number: number; stage: string; completed: boolean; accepted: boolean }

export interface MetadataView {
  record_revision: number;
  schema_version: number;
  metadata: Record<string, unknown>;
  provenance: Record<string, { origin: string; review_status: string; confidence: string | null }>;
  locked: string[];
  unknown: string[];
  stale: string[];
}

export interface MetadataField { field: string; group: "author" | "suggested" | "computed"; kind: string; options: string[]; pattern: string | null; minimum: number | null }

export interface RunSummary {
  id: string;
  settings?: { passage_size?: number } | null;
  handed_off_work?: string | null;
  manuscript_language: string;
  template_id: string;
  workflow: string;
  work_id: string;
  status: string;
  stage: string;
  chapter_id: string | null;
  attempts: number;
  error: string | null;
  progress: { completed: number; total: number } | null;
  whole_book_status?: string | null;
  passes?: Pass[];
  finalized: boolean;
  engine_current: boolean;
  gate_kind?: string;
  gate_chapter_id?: string | null;
  gate_review?: boolean;
  export_path?: string | null;
  document_path?: string | null;
  created_at?: string;
  worker: { active: boolean; paused: boolean; stopped?: string | null; error?: string };
}

export interface RunDetail extends RunSummary {
  available_actions: Action[];
  gate?: Gate;
  metadata?: MetadataView;
  metadata_fields?: MetadataField[];
  acceptance?: { acceptance_id: string; notice: string; outputs: { chapter_id: string; sha256: string; bytes: number }[] };
  stages: string[];
  stage_titles: Record<string, string>;
  template_title: string | null;
  restart_of: string | null;
  superseded_by: string | null;
}

export interface Template { id: string; title: string; workflow: string; consumes: string | null; stages: string[];
  // Select stages and the stages the user can choose there (e.g. editing passes).
  choices: Record<string, StageOption[]>;
  passage_size: { cjk_chars: number; words: number } | null }

export interface WorkSummary {
  id: string;
  title: string;
  owner: string;
  manuscript_language: string;
  source_name: string;
  created_at: string;
  workflows: Record<string, { status: string; finalized_run_id: string | null; version?: string | null }>;
  unfinished_run: string | null;
  runs: number;
  artifacts: number;
}

export interface Publication {
  id: string; created_at: string; artifact: string; version: number; status: string; review_status: string;
  stage: string; run_id: string | null; workflow: string | null; bytes: number; contract?: string;
}

export interface WorkDetail extends Omit<WorkSummary, "runs" | "artifacts"> {
  runs: { id: string; template_id: string; status: string; stage: string; created_at: string }[];
  heads: Record<string, { id: string; version: number; status: string; review_status: string; created_at: string; contract?: string }>;
  metadata: { record_revision: number; metadata: Record<string, unknown>; provenance: MetadataView["provenance"] } | null;
  metadata_fields: MetadataField[];
  metadata_history: { publication_id: string; record_revision: number; created_at: string; stage: string; status: string }[];
  publications: Publication[];
  // The work and run this work was created from (a formatted document), and works created from this one.
  origin: { work_id: string; workflow: string; run_id: string; source_version: string } | null;
  handed_off: { work_id: string; title: string; run_id: string; source_version: string }[];
}

export interface ChapterIndex {
  prepared: boolean;
  stages: string[];
  chapters: { chapter_id: string; order: number; title: string | null; role: string; outputs: Record<string, { status: string; attempt: number; ready: boolean; saving?: boolean }> }[];
  // Chosen passes (e.g. editing) among the stages, keyed "<number>-<stage>": the stage and a readable title.
  stage_info?: Record<string, { stage: string; title: string }>;
  whole_book: Record<string, string | null>;
}

export interface ChapterDetail {
  chapter: { chapter_id: string; order: number; title: string | null; role: string;
    // Set when the source has no title: the front matter's title heading came from other evidence.
    supplied_title?: { text: string; basis: "metadata" | "document_properties" | "source_name"; evidence: string } | null };
  prepared_text: string;
  outputs: { stage: string; title?: string; attempt: number | null; sha256: string; text: string;
    consistency_changes?: { id: string; before: string; after: string; reason: string; receipt_id: string }[] }[];
  passage_map: { passages: { id: string; first_paragraph: number; last_paragraph: number }[];
    exceptions: { id: string; kind: string; first_paragraph: number; last_paragraph: number; reason: string }[] } | null;
  // Completed front-matter reviews: the shared metadata and each workflow's own (e.g. translation brief).
  reviews: { kind: string; record_revision?: number; created_at?: string; decision_source: string;
    current_documents?: { path: string; sha256: string; text: string }[];
    documents: { path: string; sha256: string; text: string }[] }[];
}

export interface WorkflowEvent { id: number; created_at: string; kind: string; payload: Record<string, unknown> }

export class ApiError extends Error {
  constructor(message: string, public status: number, public code?: string) { super(message); }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) } });
  const type = response.headers.get("content-type") ?? "";
  const body = type.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof body === "string" ? body : body.detail;
    throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail), response.status, body?.code);
  }
  return body as T;
}

const post = <T>(path: string, payload: unknown = {}) => request<T>(path, { method: "POST", body: JSON.stringify(payload) });

export const api = {
  templates: () => request<Template[]>("/api/templates"),
  works: () => request<WorkSummary[]>("/api/works"),
  work: (id: string) => request<WorkDetail>(`/api/works/${encodeURIComponent(id)}`),
  artifact: (id: string, path: string) => request<string>(`/api/works/${encodeURIComponent(id)}/artifact?path=${encodeURIComponent(path)}`),
  runs: () => request<RunSummary[]>("/api/runs"),
  run: (id: string) => request<RunDetail>(`/api/runs/${id}`),
  events: (id: string, after: number) => request<{ events: WorkflowEvent[]; last_id: number }>(`/api/runs/${id}/events?after=${after}`),
  chapters: (id: string) => request<ChapterIndex>(`/api/runs/${id}/chapters`),
  chapter: (id: string, chapter: string) => request<ChapterDetail>(`/api/runs/${id}/chapters/${encodeURIComponent(chapter)}`),
  create: (payload: unknown) => post<RunDetail>("/api/runs", payload),
  editWorkMetadata: (id: string, payload: { field: string; value: unknown; rationale: string }) => post<WorkDetail>(`/api/works/${encodeURIComponent(id)}/metadata`, payload),
  createWork: (payload: { upload: { name: string; data: string }; manuscript_language: string }) => post<WorkDetail>("/api/works", payload),
  reply: (id: string, gate_id: string, text: string) => post<RunDetail>(`/api/runs/${id}/reply`, { gate_id, text }),
  accept: (id: string, acceptance_id: string, confirm_final: boolean) => post<RunDetail>(`/api/runs/${id}/accept`, { acceptance_id, confirm_final }),
  editMetadata: (id: string, payload: { field: string; value: unknown; rationale: string; gate_id?: string }) => post<RunDetail>(`/api/runs/${id}/metadata`, payload),
  confirmMetadata: (id: string, gate_id: string, record_revision: number) => post<RunDetail>(`/api/runs/${id}/metadata/confirm`, { gate_id, record_revision }),
  action: (id: string, name: string, payload: unknown = {}) => post<RunDetail>(`/api/runs/${id}/${name}`, payload),
};

export function readBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
