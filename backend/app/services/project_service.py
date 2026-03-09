from __future__ import annotations

from typing import Any

from app.models.domain import ProjectStatus, RenderResult, ValidationResult
from app.renderers.template_renderer import TemplateRenderer
from app.repositories.project_repository import ProjectRepository
from app.rules.rule_engine import RuleEngine
from app.services.clause_service import ClauseService
from app.services.export_service import ExportService
from app.services.extraction_service import ExtractionService


class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        extraction_service: ExtractionService,
        clause_service: ClauseService,
        template_renderer: TemplateRenderer,
        rule_engine: RuleEngine,
        export_service: ExportService,
    ):
        self.project_repository = project_repository
        self.extraction_service = extraction_service
        self.clause_service = clause_service
        self.template_renderer = template_renderer
        self.rule_engine = rule_engine
        self.export_service = export_service

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

    def extract(self, project_id: str, raw_input_text: str, operator_id: str) -> dict[str, Any]:
        project = self._must_get_project(project_id)
        structured_data = self.extraction_service.extract(raw_input_text)
        snapshot = self.project_repository.save_snapshot(
            project_id=project_id,
            raw_input_text=raw_input_text,
            structured_data=structured_data,
            missing_fields=structured_data.get("missing_fields", []),
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
    ):
        self._must_get_project(project_id)
        structured_data = self._must_get_structured(project_id)
        selected_clauses, sections = self.clause_service.match(
            structured_data=structured_data,
            selected_clause_ids=selected_clause_ids,
        )
        return selected_clauses, sections

    def _build_document(
        self,
        project_id: str,
        selected_clause_ids: list[str] | None,
    ) -> tuple[dict[str, Any], list, str, str, list[str], list[str], ValidationResult]:
        structured_data = self._must_get_structured(project_id)
        selected_clauses, _ = self.match_clauses(
            project_id=project_id,
            selected_clause_ids=selected_clause_ids,
        )
        rendered_text, preview_html, unresolved, used_clause_ids = self.template_renderer.render(
            structured_data=structured_data,
            selected_clauses=selected_clauses,
        )
        validation = self.rule_engine.evaluate(
            structured_data=structured_data,
            selected_clauses=selected_clauses,
            rendered_content=rendered_text,
            unresolved_placeholders=unresolved,
        )
        return (
            structured_data,
            selected_clauses,
            rendered_text,
            preview_html,
            used_clause_ids,
            unresolved,
            validation,
        )

    def validate(
        self,
        project_id: str,
        selected_clause_ids: list[str],
        operator_id: str,
    ) -> ValidationResult:
        project = self._must_get_project(project_id)
        _, _, _, _, _, _, validation = self._build_document(project_id, selected_clause_ids)

        next_status = ProjectStatus.ready if validation.can_export_formal else ProjectStatus.reviewing
        self.project_repository.update_project_status(project_id, next_status)
        self.project_repository.log_event(
            operator_id=operator_id,
            project_id=project_id,
            action="run_validate",
            before_snapshot={"project_status": project.status.value},
            after_snapshot=validation.model_dump(mode="json"),
        )
        return validation

    def render(
        self,
        project_id: str,
        selected_clause_ids: list[str],
        operator_id: str,
    ) -> RenderResult:
        self._must_get_project(project_id)
        _, _, rendered_text, preview_html, used_clause_ids, unresolved, validation = self._build_document(
            project_id=project_id,
            selected_clause_ids=selected_clause_ids,
        )
        doc = self.project_repository.save_document_version(
            project_id=project_id,
            rendered_content=rendered_text,
            used_clause_ids=used_clause_ids,
            risk_result=validation.model_dump(mode="json"),
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
            rendered_content=rendered_text,
            preview_html=preview_html,
            used_clause_ids=used_clause_ids,
            unresolved_placeholders=unresolved,
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
        if fmt not in {"docx", "pdf"}:
            raise ValueError("format 仅支持 docx 或 pdf")
        if mode not in {"draft", "formal"}:
            raise ValueError("mode 仅支持 draft 或 formal")

        _, _, rendered_text, _, used_clause_ids, _, validation = self._build_document(
            project_id=project_id,
            selected_clause_ids=selected_clause_ids,
        )
        if mode == "formal" and not validation.can_export_formal:
            raise ValueError("存在高风险项，禁止导出正式版。")

        version = self.project_repository.count_documents(project_id) + 1
        export_path = self.export_service.export(
            project_name=project.project_name,
            rendered_content=rendered_text,
            doc_type="tender",
            version=version,
            fmt=fmt,
            mode=mode,
        )
        self.project_repository.save_document_version(
            project_id=project_id,
            rendered_content=rendered_text,
            used_clause_ids=used_clause_ids,
            risk_result=validation.model_dump(mode="json"),
            export_status=mode,
            file_urls={fmt: str(export_path)},
        )

        next_status = ProjectStatus.exported if mode == "formal" else ProjectStatus.reviewing
        self.project_repository.update_project_status(project_id, next_status)
        self.project_repository.log_event(
            operator_id=operator_id,
            project_id=project_id,
            action="export_file",
            before_snapshot={},
            after_snapshot={"file_path": str(export_path), "mode": mode, "format": fmt},
        )
        return str(export_path)

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

        export_blocked = mode == "formal" and not validation.can_export_formal
        delivered_mode = "draft" if export_blocked else mode
        if export_blocked:
            file_path = self.export(
                project_id=project.project_id,
                fmt=fmt,
                mode="draft",
                selected_clause_ids=[],
                operator_id=operator_id,
            )
            message = (
                "存在高风险项，已拦截正式版导出；"
                "系统已自动生成草稿版，请使用下载链接获取。"
            )
        else:
            file_path = self.export(
                project_id=project.project_id,
                fmt=fmt,
                mode=mode,
                selected_clause_ids=[],
                operator_id=operator_id,
            )
            message = ""

        return {
            "project_id": project.project_id,
            "missing_fields": structured.get("missing_fields", []),
            "clarification_questions": structured.get("clarification_questions", []),
            "risk_summary": validation.risk_summary,
            "can_export_formal": validation.can_export_formal,
            "preview_html": render_result.preview_html,
            "file_path": file_path,
            "export_blocked": export_blocked,
            "delivered_mode": delivered_mode,
            "message": message,
        }
