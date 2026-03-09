from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.domain import MatchedSection, Project, RiskItem


class CreateProjectRequest(BaseModel):
    project_name: str = Field(min_length=1)
    department: str = Field(min_length=1)
    created_by: str = "system"


class CreateProjectResponse(BaseModel):
    project_id: str


class ExtractRequest(BaseModel):
    raw_input_text: str = Field(min_length=1)
    operator_id: str = "system"


class ExtractResponse(BaseModel):
    structured_data: dict
    missing_fields: list[str]
    clarification_questions: list[str]


class MatchClausesResponse(BaseModel):
    sections: list[MatchedSection]


class MatchClausesRequest(BaseModel):
    selected_clause_ids: list[str] = Field(default_factory=list)
    operator_id: str = "system"


class ValidateRequest(BaseModel):
    selected_clause_ids: list[str] = Field(default_factory=list)
    operator_id: str = "system"


class ValidateResponse(BaseModel):
    risk_summary: list[RiskItem]
    can_export_formal: bool


class RenderRequest(BaseModel):
    selected_clause_ids: list[str] = Field(default_factory=list)
    operator_id: str = "system"


class RenderResponse(BaseModel):
    doc_version_id: str
    preview_html: str


class ExportRequest(BaseModel):
    format: str
    mode: str
    selected_clause_ids: list[str] = Field(default_factory=list)
    operator_id: str = "system"


class ExportResponse(BaseModel):
    file_url: str


class ProjectResponse(BaseModel):
    project: Project


class GenerateDocumentRequest(BaseModel):
    project_name: str = Field(min_length=1)
    department: str = Field(min_length=1)
    raw_input_text: str = Field(min_length=1)
    format: str = "docx"
    mode: str = "draft"
    created_by: str = "system"
    operator_id: str = "system"


class GenerateDocumentResponse(BaseModel):
    project_id: str
    missing_fields: list[str]
    clarification_questions: list[str]
    risk_summary: list[RiskItem]
    can_export_formal: bool
    preview_html: str
    file_url: str | None = None
    export_blocked: bool = False
    delivered_mode: str = "draft"
    message: str = ""
