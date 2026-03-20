from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import (
    DocumentVersion,
    MatchedSection,
    Project,
    ProjectStatus,
    RequirementSnapshot,
    RiskItem,
    ValidationResult,
)


class AgentMessage(BaseModel):
    """Unified message format used by graph state and API payloads."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str = Field(min_length=1)


class ToolInputBase(BaseModel):
    """Base input envelope for tools."""

    model_config = ConfigDict(extra="forbid")

    session_id: str | None = None
    project_id: str | None = None
    operator_id: str = "system"


class ToolOutputBase(BaseModel):
    """Base output envelope for tools."""

    model_config = ConfigDict(extra="forbid")

    success: bool = True
    message: str = ""
    trace: list[str] = Field(default_factory=list)


class ExtractionResult(ToolOutputBase):
    """Normalized extraction output."""

    structured_data: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)


class ClauseMatchResult(ToolOutputBase):
    """Normalized clause match output."""

    selected_clause_ids: list[str] = Field(default_factory=list)
    matched_sections: list[MatchedSection] = Field(default_factory=list)


class ValidationToolResult(ToolOutputBase):
    """Normalized validation output."""

    risk_summary: list[RiskItem] = Field(default_factory=list)
    can_export_formal: bool = False
    high_risk_codes: list[str] = Field(default_factory=list)

    def to_validation_result(self) -> ValidationResult:
        return ValidationResult(
            risk_summary=self.risk_summary,
            can_export_formal=self.can_export_formal,
        )


class RenderToolResult(ToolOutputBase):
    """Normalized render output."""

    rendered_content: str = ""
    preview_html: str = ""
    used_clause_ids: list[str] = Field(default_factory=list)
    unresolved_placeholders: list[str] = Field(default_factory=list)
    doc_version_id: str | None = None


class ExportToolResult(ToolOutputBase):
    """Normalized export output."""

    file_path: str | None = None
    format: Literal["docx", "pdf"] = "docx"
    mode: Literal["draft", "formal"] = "draft"
    blocked: bool = False


class AgentResponsePayload(BaseModel):
    """Payload returned by chat/agent endpoints."""

    assistant_message: str = ""
    project_id: str | None = None
    current_step: str = ""
    next_action: str = ""
    requires_user_input: bool = False
    options: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)


class CreateProjectToolInput(ToolInputBase):
    """Input for project creation."""

    project_name: str = Field(min_length=1)
    department: str = Field(min_length=1)
    created_by: str = "system"


class ProjectRefToolInput(ToolInputBase):
    """Input that requires a project id."""

    project_id: str = Field(min_length=1)


class ProjectToolResult(ToolOutputBase):
    """Project read/create result."""

    project: Project | None = None


class ProjectSnapshotToolResult(ToolOutputBase):
    """Snapshot query result."""

    snapshot: RequirementSnapshot | None = None
    structured_data: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


class ProjectDocumentToolResult(ToolOutputBase):
    """Document version query result."""

    document: DocumentVersion | None = None


class ProjectStatusToolResult(ToolOutputBase):
    """Project status query result."""

    status: ProjectStatus | None = None


class ExtractRequirementsToolInput(ToolInputBase):
    """Input for requirement extraction."""

    raw_input_text: str = Field(min_length=1)


class MergeClarificationsToolInput(ToolInputBase):
    """Input for clarification merge."""

    structured_data: dict[str, Any] = Field(default_factory=dict)
    user_clarifications: dict[str, Any] = Field(default_factory=dict)


class CheckMissingFieldsToolInput(ToolInputBase):
    """Input for missing-field check."""

    structured_data: dict[str, Any] = Field(default_factory=dict)


class ProposeClarificationQuestionsToolInput(ToolInputBase):
    """Input for clarification question generation."""

    missing_fields: list[str] = Field(default_factory=list)


class ListClauseAlternativesToolInput(ToolInputBase):
    """Input for clause alternatives query."""

    structured_data: dict[str, Any] = Field(default_factory=dict)
    clause_type: str = Field(min_length=1)


class MatchClausesToolInput(ToolInputBase):
    """Input for clause matching."""

    structured_data: dict[str, Any] = Field(default_factory=dict)
    selected_clause_ids: list[str] = Field(default_factory=list)


class OverrideClauseSelectionToolInput(MatchClausesToolInput):
    """Input for clause override."""

    override_clause_id: str = Field(min_length=1)


class ExplainClauseSelectionToolInput(MatchClausesToolInput):
    """Input for clause selection explanation."""

    clause_type: str | None = None


class ClauseAlternativesResult(ToolOutputBase):
    """Alternatives for a clause type."""

    clause_type: str = ""
    selected_clause_id: str | None = None
    alternatives: list[str] = Field(default_factory=list)


class ClauseSelectionExplanationResult(ToolOutputBase):
    """Human-readable explanation for clause selection."""

    explanations: list[str] = Field(default_factory=list)
    matched_sections: list[MatchedSection] = Field(default_factory=list)


class ValidateDocumentToolInput(MatchClausesToolInput):
    """Input for document validation."""

    rendered_content: str | None = None
    unresolved_placeholders: list[str] = Field(default_factory=list)


class ExplainRiskSummaryToolInput(ToolInputBase):
    """Input for risk summary explanation."""

    risk_summary: list[RiskItem] = Field(default_factory=list)


class RiskSummaryExplanationResult(ToolOutputBase):
    """Explained risk summary output."""

    summary_text: str = ""
    high_risk_codes: list[str] = Field(default_factory=list)
    medium_risk_codes: list[str] = Field(default_factory=list)
    low_risk_codes: list[str] = Field(default_factory=list)


class SuggestFixPlanToolInput(ToolInputBase):
    """Input for fix-plan suggestion."""

    validation_result: ValidationToolResult
    missing_fields: list[str] = Field(default_factory=list)


class SuggestFixPlanResult(ToolOutputBase):
    """Fix-plan suggestion output."""

    blocking_issues: list[str] = Field(default_factory=list)
    fix_steps: list[str] = Field(default_factory=list)
    can_downgrade_to_draft: bool = True


class AutoRepairWithPeToolInput(ToolInputBase):
    """Input for one-shot PE risk repair action."""

    raw_input_text: str = ""
    structured_data: dict[str, Any] = Field(default_factory=dict)
    selected_clause_ids: list[str] = Field(default_factory=list)
    risk_summary: list[RiskItem] = Field(default_factory=list)


class AutoRepairWithPeToolResult(ToolOutputBase):
    """Output for one-shot PE risk repair action."""

    structured_data: dict[str, Any] = Field(default_factory=dict)
    selected_clause_ids: list[str] = Field(default_factory=list)
    applied_actions: list[str] = Field(default_factory=list)
    used_llm: bool = False


class CheckFormalExportEligibilityToolInput(ToolInputBase):
    """Input for formal export guard checks."""

    validation_result: ValidationToolResult


class FormalExportEligibilityResult(ToolOutputBase):
    """Formal export eligibility output."""

    can_export_formal: bool = False
    reason: str = ""


class RenderPreviewToolInput(MatchClausesToolInput):
    """Input for render preview."""


class ExportDocumentToolInput(ToolInputBase):
    """Input for file export."""

    project_name: str = Field(min_length=1)
    rendered_content: str = Field(min_length=1)
    format: Literal["docx", "pdf"] = "docx"
    mode: Literal["draft", "formal"] = "draft"
    version: int = Field(default=1, ge=1)
    doc_type: str = "tender"
    can_export_formal: bool = False


class BuildUserOptionsToolInput(ToolInputBase):
    """Input for clarification option generation."""

    missing_fields: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)


class UserOptionsToolResult(ToolOutputBase):
    """Clarification option output for user interaction."""

    requires_user_input: bool = False
    prompt: str = ""
    options: list[dict[str, Any]] = Field(default_factory=list)


class ClarificationReviewToolInput(ToolInputBase):
    """Input for clarification review before merge."""

    messages: list[AgentMessage] = Field(default_factory=list)
    raw_input_text: str = ""
    structured_data: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    user_clarifications: dict[str, Any] = Field(default_factory=dict)


class ClarificationReviewToolResult(ToolOutputBase):
    """Output for clarification review before merge."""

    accepted: bool = False
    confidence: float = 0.0
    normalized_clarifications: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    follow_up_questions: list[dict[str, str]] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    used_llm: bool = False


class RequestHumanConfirmationToolInput(ToolInputBase):
    """Input for human confirmation check."""

    action: str = Field(min_length=1)
    message: str = ""
    options: list[dict[str, Any]] = Field(default_factory=list)


class HumanConfirmationToolResult(ToolOutputBase):
    """Human confirmation policy output."""

    pending_human_confirmation: bool = False
    action: str = ""
    prompt: str = ""
    options: list[dict[str, Any]] = Field(default_factory=list)
