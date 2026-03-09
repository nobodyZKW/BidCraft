from __future__ import annotations

from functools import lru_cache

from app.core.settings import settings
from app.llm.deepseek_client import DeepSeekClient
from app.renderers.template_renderer import TemplateRenderer
from app.repositories.clause_repository import ClauseRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.template_repository import TemplateRepository
from app.rules.rule_engine import RuleEngine
from app.services.clause_service import ClauseService
from app.services.export_service import ExportService
from app.services.extraction_service import ExtractionService
from app.services.project_service import ProjectService


@lru_cache(maxsize=1)
def get_project_service() -> ProjectService:
    project_repo = ProjectRepository(settings.runtime_dir)
    clause_repo = ClauseRepository(settings.data_dir / "clauses" / "clauses.json")
    template_repo = TemplateRepository(settings.data_dir / "templates" / "document_template.json")

    extraction_service = ExtractionService(DeepSeekClient())
    clause_service = ClauseService(clause_repo)
    template_renderer = TemplateRenderer(template_repo)
    rule_engine = RuleEngine()
    export_service = ExportService(settings.export_dir)

    return ProjectService(
        project_repository=project_repo,
        extraction_service=extraction_service,
        clause_service=clause_service,
        template_renderer=template_renderer,
        rule_engine=rule_engine,
        export_service=export_service,
    )
