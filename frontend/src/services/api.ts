export type RiskItem = {
  code: string;
  message: string;
  severity: "high" | "medium" | "low";
  location: string;
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
  matched_sections?: Array<Record<string, unknown>>;
  risk_summary?: RiskItem[];
  can_export_formal?: boolean;
  preview_html?: string;
  file_path?: string;
  error?: string | null;
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
