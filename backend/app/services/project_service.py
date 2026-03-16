from __future__ import annotations

from typing import Any

from app.agent.types import (
    ExportDocumentToolInput,
    ExtractRequirementsToolInput,
    MatchClausesToolInput,
    RenderPreviewToolInput,
    ValidateDocumentToolInput,
    ValidationToolResult,
)
from app.models.domain import Clause, ProjectStatus, RenderResult, ValidationResult
from app.renderers.template_renderer import TemplateRenderer
from app.repositories.project_repository import ProjectRepository
from app.rules.export_guard import FORMAL_EXPORT_BLOCK_MESSAGE, FormalExportGuard
from app.rules.rule_engine import RuleEngine
from app.services.clause_service import ClauseService
from app.services.export_service import ExportService
from app.services.extraction_service import ExtractionService
from app.tools.clause_tools import match_clauses_tool
from app.tools.export_tools import export_document_tool
from app.tools.extraction_tools import extract_requirements_tool
from app.tools.render_tools import render_preview_tool
from app.tools.validation_tools import validate_document_tool


class ProjectService:
    """Backward-compatible facade for legacy REST routes."""

    def __init__(
        self,
        project_repository: ProjectRepository,
        extraction_service: ExtractionService,
        clause_service: ClauseService,
        template_renderer: TemplateRenderer,
        rule_engine: RuleEngine,
        export_service: ExportService,
        export_guard: FormalExportGuard | None = None,
    ):
        self.project_repository = project_repository
        self.extraction_service = extraction_service
        self.clause_service = clause_service
        self.template_renderer = template_renderer
        self.rule_engine = rule_engine
        self.export_service = export_service
        self.export_guard = export_guard or FormalExportGuard()

    def create_project(self, project_name: str, department: str, created_by: str):
        project = self.project_repository.create_project(
            project_name=project_name,
            department=department,
            created_by=created_by,
        )
        self.project_repository.log_event(
            operator_id=created_by,
            project_id=project.project_id,
            action="create_project",
            before_snapshot={},
            after_snapshot=project.model_dump(mode="json"),
        )
        return project

    def _must_get_project(self, project_id: str):
        project = self.project_repository.get_project(project_id)
        if not project:
            raise KeyError(f"Project not found: {project_id}")
        return project

    def get_project(self, project_id: str):
        return self._must_get_project(project_id)

    def get_latest_snapshot(self, project_id: str):
        self._must_get_project(project_id)
        return self.project_repository.get_latest_snapshot(project_id)

    def get_latest_document(self, project_id: str):
        self._must_get_project(project_id)
        return self.project_repository.get_latest_document(project_id)

    def get_project_status(self, project_id: str) -> ProjectStatus:
        project = self._must_get_project(project_id)
        return project.status

    @staticmethod
    def _normalize_selected_clause_ids(selected_clause_ids: list[str] | None) -> list[str]:
        return selected_clause_ids or []

    @staticmethod
    def _validation_from_tool(validation_result: ValidationToolResult) -> ValidationResult:
        return validation_result.to_validation_result()

    def extract(self, project_id: str, raw_input_text: str, operator_id: str) -> dict[str, Any]:
        project = self._must_get_project(project_id)
        extraction_result = extract_requirements_tool(
            ExtractRequirementsToolInput(
                project_id=project_id,
                operator_id=operator_id,
                raw_input_text=raw_input_text,
            ),
            extraction_service=self.extraction_service,
        )
        structured_data = extraction_result.structured_data
        snapshot = self.project_repository.save_snapshot(
            project_id=project_id,
            raw_input_text=raw_input_text,
            structured_data=structured_data,
            missing_fields=extraction_result.missing_fields,
        )
        self.project_repository.update_project_status(project_id, ProjectStatus.reviewing)
        self.project_repository.log_event(
            operator_id=operator_id,
            project_id=project_id,
            action="run_extract",
            before_snapshot={"project_status": project.status.value},
            after_snapshot=snapshot.model_dump(mode="json"),
        )
        return structured_data

    def _must_get_structured(self, project_id: str) -> dict[str, Any]:
        snapshot = self.project_repository.get_latest_snapshot(project_id)
        if not snapshot:
            raise ValueError("请先提交需求并运行抽取。")
        return snapshot.structured_data

    def match_clauses(
        self,
        project_id: str,
        selected_clause_ids: list[str] | None = None,
    ) -> tuple[list[Clause], list]:
        self._must_get_project(project_id)
        structured_data = self._must_get_structured(project_id)
        match_result = match_clauses_tool(
            MatchClausesToolInput(
                project_id=project_id,
                structured_data=structured_data,
                selected_clause_ids=self._normalize_selected_clause_ids(selected_clause_ids),
            ),
            clause_service=self.clause_service,
        )
        selected_clauses = self.clause_service.get_by_ids(match_result.selected_clause_ids)
        return selected_clauses, match_result.matched_sections

    @staticmethod
    def _validate_export_params(fmt: str, mode: str) -> None:
        if fmt not in {"docx", "pdf"}:
            raise ValueError("format 仅支持 docx 或 pdf")
        if mode not in {"draft", "formal"}:
            raise ValueError("mode 仅支持 draft 或 formal")

    def validate(
        self,
        project_id: str,
        selected_clause_ids: list[str],
        operator_id: str,
    ) -> ValidationResult:
        project = self._must_get_project(project_id)
        structured_data = self._must_get_structured(project_id)
        validation_result = validate_document_tool(
            ValidateDocumentToolInput(
                project_id=project_id,
                operator_id=operator_id,
                structured_data=structured_data,
                selected_clause_ids=self._normalize_selected_clause_ids(selected_clause_ids),
            ),
            clause_service=self.clause_service,
            template_renderer=self.template_renderer,
            rule_engine=self.rule_engine,
        )
        validation = self._validation_from_tool(validation_result)
        final_validation = ValidationResult(
            risk_summary=validation.risk_summary,
            can_export_formal=self.export_guard.can_export_formal(validation),
        )
        next_status = (
            ProjectStatus.ready if final_validation.can_export_formal else ProjectStatus.reviewing
        )
        self.project_repository.update_project_status(project_id, next_status)
        self.project_repository.log_event(
            operator_id=operator_id,
            project_id=project_id,
            action="run_validate",
            before_snapshot={"project_status": project.status.value},
            after_snapshot=final_validation.model_dump(mode="json"),
        )
        return final_validation

    def render(
        self,
        project_id: str,
        selected_clause_ids: list[str],
        operator_id: str,
    ) -> RenderResult:
        self._must_get_project(project_id)
        structured_data = self._must_get_structured(project_id)
        clause_ids = self._normalize_selected_clause_ids(selected_clause_ids)

        render_result = render_preview_tool(
            RenderPreviewToolInput(
                project_id=project_id,
                operator_id=operator_id,
                structured_data=structured_data,
                selected_clause_ids=clause_ids,
            ),
            clause_service=self.clause_service,
            template_renderer=self.template_renderer,
        )
        validation_result = validate_document_tool(
            ValidateDocumentToolInput(
                project_id=project_id,
                operator_id=operator_id,
                structured_data=structured_data,
                selected_clause_ids=clause_ids,
                rendered_content=render_result.rendered_content,
                unresolved_placeholders=render_result.unresolved_placeholders,
            ),
            clause_service=self.clause_service,
            template_renderer=self.template_renderer,
            rule_engine=self.rule_engine,
        )
        validation = self._validation_from_tool(validation_result)
        final_validation = ValidationResult(
            risk_summary=validation.risk_summary,
            can_export_formal=self.export_guard.can_export_formal(validation),
        )

        doc = self.project_repository.save_document_version(
            project_id=project_id,
            rendered_content=render_result.rendered_content,
            used_clause_ids=render_result.used_clause_ids,
            risk_result=final_validation.model_dump(mode="json"),
            export_status="draft",
        )
        self.project_repository.log_event(
            operator_id=operator_id,
            project_id=project_id,
            action="run_render",
            before_snapshot={},
            after_snapshot=doc.model_dump(mode="json"),
        )
        return RenderResult(
            doc_version_id=doc.doc_version_id,
            rendered_content=render_result.rendered_content,
            preview_html=render_result.preview_html,
            used_clause_ids=render_result.used_clause_ids,
            unresolved_placeholders=render_result.unresolved_placeholders,
        )

    def export(
        self,
        project_id: str,
        fmt: str,
        mode: str,
        selected_clause_ids: list[str],
        operator_id: str,
    ) -> str:
        project = self._must_get_project(project_id)
        self._validate_export_params(fmt, mode)
        structured_data = self._must_get_structured(project_id)
        clause_ids = self._normalize_selected_clause_ids(selected_clause_ids)

        render_result = render_preview_tool(
            RenderPreviewToolInput(
                project_id=project_id,
                operator_id=operator_id,
                structured_data=structured_data,
                selected_clause_ids=clause_ids,
            ),
            clause_service=self.clause_service,
            template_renderer=self.template_renderer,
        )
        validation_result = validate_document_tool(
            ValidateDocumentToolInput(
                project_id=project_id,
                operator_id=operator_id,
                structured_data=structured_data,
                selected_clause_ids=clause_ids,
                rendered_content=render_result.rendered_content,
                unresolved_placeholders=render_result.unresolved_placeholders,
            ),
            clause_service=self.clause_service,
            template_renderer=self.template_renderer,
            rule_engine=self.rule_engine,
        )
        validation = self._validation_from_tool(validation_result)
        final_validation = ValidationResult(
            risk_summary=validation.risk_summary,
            can_export_formal=self.export_guard.can_export_formal(validation),
        )

        if mode == "formal":
            self.export_guard.assert_formal_export_allowed(final_validation)

        version = self.project_repository.count_documents(project_id) + 1
        export_result = export_document_tool(
            ExportDocumentToolInput(
                project_id=project_id,
                operator_id=operator_id,
                project_name=project.project_name,
                rendered_content=render_result.rendered_content,
                format=fmt,
                mode=mode,
                version=version,
                doc_type="tender",
                can_export_formal=final_validation.can_export_formal,
            ),
            export_service=self.export_service,
        )
        if export_result.blocked or not export_result.file_path:
            raise ValueError(FORMAL_EXPORT_BLOCK_MESSAGE)

        self.project_repository.save_document_version(
            project_id=project_id,
            rendered_content=render_result.rendered_content,
            used_clause_ids=render_result.used_clause_ids,
            risk_result=final_validation.model_dump(mode="json"),
            export_status=mode,
            file_urls={fmt: export_result.file_path},
        )
        next_status = ProjectStatus.exported if mode == "formal" else ProjectStatus.reviewing
        self.project_repository.update_project_status(project_id, next_status)
        self.project_repository.log_event(
            operator_id=operator_id,
            project_id=project_id,
            action="export_file",
            before_snapshot={},
            after_snapshot={"file_path": export_result.file_path, "mode": mode, "format": fmt},
        )
        return export_result.file_path

    def generate_from_text(
        self,
        project_name: str,
        department: str,
        raw_input_text: str,
        fmt: str,
        mode: str,
        created_by: str,
        operator_id: str,
    ) -> dict[str, Any]:
        tool_calls = [
            "extraction_tools.py:extract_requirements_tool",
            "validation_tools.py:validate_document_tool",
            "render_tools.py:render_preview_tool",
            "export_tools.py:export_document_tool",
            "rules/export_guard.py:FormalExportGuard",
        ]
        project = self.create_project(
            project_name=project_name,
            department=department,
            created_by=created_by,
        )
        structured = self.extract(
            project_id=project.project_id,
            raw_input_text=raw_input_text,
            operator_id=operator_id,
        )
        validation = self.validate(
            project_id=project.project_id,
            selected_clause_ids=[],
            operator_id=operator_id,
        )
        render_result = self.render(
            project_id=project.project_id,
            selected_clause_ids=[],
            operator_id=operator_id,
        )

        export_blocked = mode == "formal" and not self.export_guard.can_export_formal(validation)
        delivered_mode = "draft" if export_blocked else mode
        file_path = self.export(
            project_id=project.project_id,
            fmt=fmt,
            mode=delivered_mode,
            selected_clause_ids=[],
            operator_id=operator_id,
        )
        message = ""
        if export_blocked:
            message = (
                "存在高风险项，已拦截正式版导出；"
                "系统已自动生成草稿版，请使用下载链接获取。"
            )

        return {
            "project_id": project.project_id,
            "missing_fields": structured.get("missing_fields", []),
            "clarification_questions": structured.get("clarification_questions", []),
            "risk_summary": validation.risk_summary,
            "can_export_formal": self.export_guard.can_export_formal(validation),
            "preview_html": render_result.preview_html,
            "file_path": file_path,
            "export_blocked": export_blocked,
            "delivered_mode": delivered_mode,
            "message": message,
            "tool_calls": tool_calls,
        }
