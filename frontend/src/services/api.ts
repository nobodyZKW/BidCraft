export type KnowledgeCitation = {
  source_id: string;
  title: string;
  excerpt: string;
};

export type MatchedSection = {
  section_id: string;
  selected_clause_id: string;
  alternatives: string[];
  reason: string;
  citations?: KnowledgeCitation[];
};

export type RiskItem = {
  code: string;
  message: string;
  severity: "high" | "medium" | "low";
  location: string;
  citations?: KnowledgeCitation[];
};

export type TraceSummary = {
  trace_count: number;
  tool_call_count: number;
  llm_decision_count: number;
  last_trace: string;
  run_id: string;
  duration_ms: number;
};

export type EvalCaseResult = {
  case_id: string;
  category: string;
  input_text: string;
  missing_fields: string[];
  risk_count: number;
  high_risk_count: number;
  can_export_formal: boolean;
  passed: boolean;
  expectation: string;
};

export type EvalCategoryResult = {
  category: string;
  total_cases: number;
  passed_cases: number;
  pass_rate: number;
  cases: EvalCaseResult[];
};

export type EvalReport = {
  generated_at: string;
  mode: string;
  total_cases: number;
  passed_cases: number;
  pass_rate: number;
  categories: EvalCategoryResult[];
};

export type GenerateDocumentRequest = {
  project_name: string;
  department: string;
  raw_input_text: string;
  format: "docx" | "pdf";
  mode: "draft" | "formal";
};

export type GenerateDocumentResponse = {
  project_id: string;
  missing_fields: string[];
  clarification_questions: string[];
  risk_summary: RiskItem[];
  can_export_formal: boolean;
  preview_html: string;
  file_url: string | null;
  export_blocked: boolean;
  delivered_mode: "draft" | "formal";
  message: string;
  tool_calls: string[];
};

export type AgentOption = Record<string, unknown>;

export type AgentArtifacts = {
  missing_fields?: string[];
  clarification_questions?: string[];
  matched_sections?: MatchedSection[];
  risk_summary?: RiskItem[];
  can_export_formal?: boolean;
  preview_html?: string;
  file_path?: string;
  file_url?: string | null;
  error?: string | null;
  trace?: string[];
  trace_summary?: TraceSummary;
};

export type AgentChatRequest = {
  message: string;
  session_id?: string;
  project_id?: string;
  user_clarifications?: Record<string, unknown>;
};

export type AgentContinueRequest = {
  message?: string;
  user_clarifications?: Record<string, unknown>;
};

export type AgentChatResponse = {
  assistant_message: string;
  project_id: string | null;
  current_step: string;
  next_action: string;
  requires_user_input: boolean;
  options: AgentOption[];
  tool_calls: string[];
  artifacts: AgentArtifacts;
};

export type AgentProjectStateResponse = {
  project_id: string;
  state: Record<string, unknown>;
};

export const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${text}`);
  }
  return (await resp.json()) as T;
}

export async function generateDocument(
  payload: GenerateDocumentRequest
): Promise<GenerateDocumentResponse> {
  return postJSON<GenerateDocumentResponse>("/api/projects/generate", payload);
}

export async function agentChat(
  payload: AgentChatRequest
): Promise<AgentChatResponse> {
  return postJSON<AgentChatResponse>("/api/agent/chat", payload);
}

export async function continueAgentProject(
  projectId: string,
  payload: AgentContinueRequest
): Promise<AgentChatResponse> {
  return postJSON<AgentChatResponse>(
    `/api/agent/projects/${projectId}/continue`,
    payload
  );
}

export async function getAgentProjectState(
  projectId: string
): Promise<AgentProjectStateResponse> {
  const resp = await fetch(`${BASE_URL}/api/agent/projects/${projectId}/state`);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${text}`);
  }
  return (await resp.json()) as AgentProjectStateResponse;
}

export async function runEvaluation(): Promise<EvalReport> {
  return postJSON<EvalReport>("/api/evals/run", {});
}

export async function getLatestEvaluation(): Promise<EvalReport> {
  const resp = await fetch(`${BASE_URL}/api/evals/latest`);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${text}`);
  }
  return (await resp.json()) as EvalReport;
}
