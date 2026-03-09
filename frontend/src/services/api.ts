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
  file_url: string;
};

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

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
