from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import MatchedSection, Project, RiskItem


class CreateProjectRequest(BaseModel):
    project_name: str = Field(min_length=1, description="Project name")
    department: str = Field(min_length=1, description="Department")
    created_by: str = Field(default="system", description="Creator id")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_name": "Server Procurement Project",
                "department": "IT Department",
                "created_by": "buyer_001",
            }
        }
    )


class CreateProjectResponse(BaseModel):
    project_id: str = Field(description="Project id")


class ExtractRequest(BaseModel):
    raw_input_text: str = Field(min_length=1, description="Raw requirement text")
    operator_id: str = Field(default="system", description="Operator id")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "raw_input_text": (
                    "Server procurement project, budget 3000000 CNY, "
                    "delivery 45 days, payment 30/60/10, "
                    "acceptance by test report, warranty 24 months."
                ),
                "operator_id": "buyer_001",
            }
        }
    )


class ExtractResponse(BaseModel):
    structured_data: dict = Field(description="Structured extraction payload")
    missing_fields: list[str] = Field(description="Missing fields")
    clarification_questions: list[str] = Field(description="Clarification prompts")


class MatchClausesRequest(BaseModel):
    selected_clause_ids: list[str] = Field(default_factory=list, description="Manual clause id list")
    operator_id: str = Field(default="system", description="Operator id")

    model_config = ConfigDict(
        json_schema_extra={"example": {"selected_clause_ids": [], "operator_id": "buyer_001"}}
    )


class MatchClausesResponse(BaseModel):
    sections: list[MatchedSection] = Field(description="Matched section list")


class ValidateRequest(BaseModel):
    selected_clause_ids: list[str] = Field(default_factory=list, description="Manual clause id list")
    operator_id: str = Field(default="system", description="Operator id")

    model_config = ConfigDict(
        json_schema_extra={"example": {"selected_clause_ids": [], "operator_id": "buyer_001"}}
    )


class ValidateResponse(BaseModel):
    risk_summary: list[RiskItem] = Field(description="Risk findings")
    can_export_formal: bool = Field(description="Whether formal export is allowed")


class RenderRequest(BaseModel):
    selected_clause_ids: list[str] = Field(default_factory=list, description="Manual clause id list")
    operator_id: str = Field(default="system", description="Operator id")

    model_config = ConfigDict(
        json_schema_extra={"example": {"selected_clause_ids": [], "operator_id": "buyer_001"}}
    )


class RenderResponse(BaseModel):
    doc_version_id: str = Field(description="Document version id")
    preview_html: str = Field(description="Rendered preview html")


class ExportRequest(BaseModel):
    format: str = Field(description="Export format: docx or pdf")
    mode: str = Field(description="Export mode: draft or formal")
    selected_clause_ids: list[str] = Field(default_factory=list, description="Manual clause id list")
    operator_id: str = Field(default="system", description="Operator id")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "format": "pdf",
                "mode": "formal",
                "selected_clause_ids": [],
                "operator_id": "buyer_001",
            }
        }
    )


class ExportResponse(BaseModel):
    file_url: str = Field(description="Downloadable file URL")


class ProjectResponse(BaseModel):
    project: Project = Field(description="Project detail")


class GenerateDocumentRequest(BaseModel):
    project_name: str = Field(min_length=1, description="Project name")
    department: str = Field(min_length=1, description="Department")
    raw_input_text: str = Field(min_length=1, description="Raw requirement text")
    format: str = Field(default="docx", description="Export format: docx/pdf")
    mode: str = Field(default="draft", description="Export mode: draft/formal")
    created_by: str = Field(default="system", description="Creator id")
    operator_id: str = Field(default="system", description="Operator id")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_name": "Server Procurement Project",
                "department": "IT Department",
                "raw_input_text": (
                    "Server procurement project, budget 3000000 CNY, "
                    "delivery 45 days, payment 30/60/10, "
                    "acceptance by test report, warranty 24 months."
                ),
                "format": "pdf",
                "mode": "formal",
                "created_by": "buyer_001",
                "operator_id": "buyer_001",
            }
        }
    )


class GenerateDocumentResponse(BaseModel):
    project_id: str = Field(description="Project id")
    missing_fields: list[str] = Field(description="Missing fields")
    clarification_questions: list[str] = Field(description="Clarification prompts")
    risk_summary: list[RiskItem] = Field(description="Risk findings")
    can_export_formal: bool = Field(description="Whether formal export is allowed")
    preview_html: str = Field(description="Rendered preview html")
    file_url: str | None = Field(default=None, description="Downloadable file URL")
    export_blocked: bool = Field(default=False, description="Whether formal export was blocked")
    delivered_mode: str = Field(default="draft", description="Actual export mode")
    message: str = Field(default="", description="Additional message")
    tool_calls: list[str] = Field(default_factory=list, description="Called tools")

