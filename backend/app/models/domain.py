from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    draft = "draft"
    reviewing = "reviewing"
    ready = "ready"
    exported = "exported"


class RiskSeverity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Project(BaseModel):
    project_id: str
    project_name: str
    department: str
    status: ProjectStatus = ProjectStatus.draft
    created_by: str = "system"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RequirementSnapshot(BaseModel):
    snapshot_id: str
    project_id: str
    raw_input_text: str
    structured_data: dict[str, Any]
    missing_fields: list[str]
    version: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Clause(BaseModel):
    clause_id: str
    clause_name: str
    clause_type: str
    content_template: str
    applicable_procurement_types: list[str]
    applicable_methods: list[str]
    required_fields: list[str]
    forbidden_conditions: list[str]
    risk_level: str
    version: str
    effective_date: date
    expiry_date: date | None = None
    status: str
    locked: bool = False


class MatchedSection(BaseModel):
    section_id: str
    selected_clause_id: str
    alternatives: list[str]
    reason: str


class RiskItem(BaseModel):
    code: str
    message: str
    severity: RiskSeverity
    location: str


class ValidationResult(BaseModel):
    risk_summary: list[RiskItem]
    can_export_formal: bool


class RenderResult(BaseModel):
    doc_version_id: str
    rendered_content: str
    preview_html: str
    used_clause_ids: list[str]
    unresolved_placeholders: list[str]


class DocumentVersion(BaseModel):
    doc_version_id: str
    project_id: str
    doc_type: str = "tender"
    rendered_content: str
    used_clause_ids: list[str]
    risk_result: dict[str, Any]
    export_status: str
    file_urls: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditEvent(BaseModel):
    operator_id: str
    project_id: str
    action: str
    before_snapshot: dict[str, Any]
    after_snapshot: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
