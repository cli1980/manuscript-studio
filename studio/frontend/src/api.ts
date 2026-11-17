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

export interface ApprovedSheetSummary {
  receipt_id: string;
  sheet_id: string;
  revision: string;
  title: string;
  sha256: string;
  created_at: string;
  decision_source: string;
  kind: string;
  stage: string;
  stage_title: string;
  chapter_id: string | null;
  scope: string;
  pass_number: number | null;
  attempt: number | null;
  superseded: boolean;
  implied_closure: boolean;
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
  design_review?: { proposal: InteriorProposal; sha256: string; schema: JsonSchema;
    format_target: FormatTarget | null; vendor_warnings: string[] };
}

export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export interface JsonSchema {
  "x-preset-templates"?: Record<string, string>;
  $ref?: string;
  type?: string | string[];
  properties?: Record<string, JsonSchema>;
  $defs?: Record<string, JsonSchema>;
  items?: JsonSchema;
  enum?: JsonValue[];
  const?: JsonValue;
  minimum?: number;
  maximum?: number;
}
export interface InteriorProposal {
  proposal_id: string;
  revision: number;
  basis: { preparation: { units: { chapter_id: string }[] } };
  vendor_profile: VendorProfile | null;
  edition_brief: JsonValue;
  design_system: JsonValue;
  reading: { essence: string; genres: string[]; synopsis: string; mood: string[] };
  text_roles: { id: string; name: string; function: string; style_id: string; occurrences: {
    chapter_id: string; chapter_sha256: string; paragraph_index: number; paragraph_sha256: string;
  }[] }[];
  questions: { id: string; question: string; kind: string; blocking: boolean; options: string[] }[];
  recommendations: { id: string; path: string; rationale: string; alternatives: string[] }[];
}
export interface InteriorSpec {
  edition_brief: JsonValue;
  design_system: JsonValue;
  role_styles: Record<string, string>;
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
  source_differences?: { field: string; source_value: unknown; reviewed_value: unknown }[];
}

export interface MetadataField { field: string; group: "suggested" | "computed"; kind: string; options: string[]; pattern: string | null; minimum: number | null }

export type ViewerTarget = { kind: "overview" } | { kind: "chapter"; chapter_id: string };

export interface RunSummary {
  viewer_target: ViewerTarget | null;
  production?: {
    id: string; status: string; plan_sha256: string; proposal_sha256: string; accepted: boolean;
    notice: string; attempts: number; error?: { code: string; message: string } | null;
    summary: { units: number; paragraphs: number; styles: string[]; policy: Record<string, JsonValue>;
      vendor_warnings: JsonValue[] };
    docx: { sha256: string; bytes: number; name: string } | null;
  } | null;
  id: string;
  execution?: ExecutionIdentity | null;
  retired: boolean;
  recorded_status?: string;
  acceptance_title?: string;
  settings?: { passage_size?: number } | null;
  handed_off_work?: string | null;
  manuscript_language: string | null;
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

export interface ExecutionIdentity {
  profile: string;
  revision: string;
  harness: string;
  model_key: string;
  model: string;
  endpoint: string | null;
  base_url: string | null;
  sandbox: string;
}

export interface ExecutionCatalog {
  name: string;
  harness: string;
  default_model?: string;
  models: (ExecutionIdentity & { workflows: string[] })[];
}

export interface FormatTarget {
  purpose: "print-ready" | "submission" | "editorial-review";
  vendor_id: string | null; binding: "paperback" | "hardcover";
}
export interface VendorProfile {
  profile_id: string; version: string; variant_id: "paperback" | "hardcover"; sha256: string;
  data: {
    name: string;
    source: { title: string; edition: string; url: string; sha256: string; reviewed_at: string };
    docx_guidance: { recommended_safety_mm: number; gutter: string; page_size: string; delivery: string };
    variant: { name: string; vendor_binding: string; notes: string[] };
    rules: { id: string; classification: string; phase: string; pages: number[]; applies_to: string; statement: string }[];
  };
}
export interface VendorProfileOption {
  id: string; name: string; version: string;
  variants: { id: string; name: string; binding: string; profile: VendorProfile }[];
}

export interface RunDetail extends RunSummary {
  usage?: TokenUsage;
  available_actions: Action[];
  gate?: Gate;
  metadata?: MetadataView;
  metadata_fields?: MetadataField[];
  acceptance?: { acceptance_id: string; title: string; action_label: string; finalizes: boolean; notice: string;
    vendor_profiles?: VendorProfileOption[]; format_target?: FormatTarget | null;
    outputs: { chapter_id: string; sha256: string; bytes: number }[] };
  stages: string[];
  stage_titles: Record<string, string>;
  template_title: string | null;
  restart_of: string | null;
  superseded_by: string | null;
}

export interface TokenUsage {
  input_tokens: number | null;
  output_tokens: number | null;
  cached_input_tokens: number | null;
  total_tokens: number | null;
  reported_attempts: number;
  attempts: number;
  partial: boolean;
  warnings: string[];
}

export interface Template { id: string; title: string; workflow: string; consumes: string | null; stages: string[];
  // Select stages and the stages the user can choose there (e.g. editing passes).
  choices: Record<string, StageOption[]>;
  passage_size: { cjk_chars: number; words: number } | null }

export interface WorkSummary {
  id: string;
  title: string;
  owner: string;
  manuscript_language: string | null;
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
  metadata_editor_run: string | null;
  metadata_history: { publication_id: string; record_revision: number; created_at: string; stage: string; status: string }[];
  publications: Publication[];
  // The work and run this work was created from (a formatted document), and works created from this one.
  origin: { work_id: string; workflow: string; run_id: string; source_version: string } | null;
  handed_off: { work_id: string; title: string; run_id: string; source_version: string }[];
}

export interface ChapterIndex {
  prepared: boolean;
  overview: { work_id: string; title: string; source_unit_id: string | null;
    outputs: Record<string, { status: string; attempt: number; ready: boolean; saving?: boolean }> };
  stages: string[];
  chapters: { chapter_id: string; order: number; display_number: number | null; title: string | null; role: string; outputs: Record<string, { status: string; attempt: number; ready: boolean; saving?: boolean }> }[];
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

export interface Overview {
  work_id: string;
  title: string;
  source_unit_id: string | null;
  prepared: boolean;
  analysis?: { analysis_id: string; approval_status: "provisional"; qualifications: string[];
    coverage_verification: string; current_text_matches_source: boolean;
    documents: { path: string; sha256: string; text: string }[] } | null;
  source: ChapterDetail | null;
  metadata: MetadataView | null;
  metadata_fields: MetadataField[];
  metadata_edit: { target: "run" | "work" | null; run_id: string | null };
}

export interface WorkflowEvent { id: number; created_at: string; kind: string; payload: Record<string, unknown> }

/** The server's change fingerprints: per run its state revision, last visible event, and worker; per work its log. */
export interface LiveSnapshot {
  version: number;
  runs: Record<string, { revision: number; event: number; worker: Record<string, unknown> }>;
  works: Record<string, string>;
}

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
  execution: () => request<ExecutionCatalog>("/api/execution"),
  templates: () => request<Template[]>("/api/templates"),
  works: () => request<WorkSummary[]>("/api/works"),
  work: (id: string) => request<WorkDetail>(`/api/works/${encodeURIComponent(id)}`),
  artifact: (id: string, path: string) => request<string>(`/api/works/${encodeURIComponent(id)}/artifact?path=${encodeURIComponent(path)}`),
  sourceUrl: (id: string) => `/api/works/${encodeURIComponent(id)}/source`,  // A download link, not a fetch.
  docxUrl: (id: string, buildId: string) => `/api/runs/${encodeURIComponent(id)}/docx/${encodeURIComponent(buildId)}`,
  publishedDocxUrl: (id: string, publicationId: string) =>
    `/api/works/${encodeURIComponent(id)}/docx/${encodeURIComponent(publicationId)}`,
  runs: () => request<RunSummary[]>("/api/runs"),
  run: (id: string) => request<RunDetail>(`/api/runs/${id}`),
  events: (id: string, after: number) => request<{ events: WorkflowEvent[]; last_id: number }>(`/api/runs/${id}/events?after=${after}`),
  live: () => request<LiveSnapshot>("/api/live"),
  chapters: (id: string) => request<ChapterIndex>(`/api/runs/${id}/chapters`),
  overview: (id: string) => request<Overview>(`/api/runs/${id}/overview`),
  approvedSheets: (id: string) => request<ApprovedSheetSummary[]>(`/api/runs/${id}/approved-sheets`),
  approvedSheetDownload: (id: string, receipt: string) =>
    `/api/runs/${id}/approved-sheets/${encodeURIComponent(receipt)}.md`,
  chapter: (id: string, chapter: string) => request<ChapterDetail>(`/api/runs/${id}/chapters/${encodeURIComponent(chapter)}`),
  create: (payload: unknown) => post<RunDetail>("/api/runs", payload),
  editWorkMetadata: (id: string, payload: { field: string; value: unknown; rationale: string }) => post<WorkDetail>(`/api/works/${encodeURIComponent(id)}/metadata`, payload),
  createWork: (payload: { upload: { name: string; data: string }; manuscript_language?: string }) => post<WorkDetail>("/api/works", payload),
  reply: (id: string, gate_id: string, text: string) => post<RunDetail>(`/api/runs/${id}/reply`, { gate_id, text }),
  reviewInteriorDesign: (id: string, payload: {
    gate_id: string; expected_sha256: string; action: "save" | "approve" | "request-revision";
    spec?: InteriorSpec; answers?: Record<string, string>; feedback?: string;
  }) => post<RunDetail>(`/api/runs/${id}/interior-design`, payload),
  authorizeDocx: (id: string, gate_id: string, expected_plan_sha256: string) =>
    post<RunDetail>(`/api/runs/${id}/docx/authorize`, { gate_id, expected_plan_sha256 }),
  accept: (id: string, acceptance_id: string, confirm_final: boolean, format_target?: FormatTarget) =>
    post<RunDetail>(`/api/runs/${id}/accept`, { acceptance_id, confirm_final, format_target }),
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
