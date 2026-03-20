from __future__ import annotations

from functools import lru_cache

from app.agent.graph import build_agent_graph
from app.agent.nodes import AgentNodeDependencies
from app.agent.runtime import AgentWorkflowRunner
from app.core.settings import settings
from app.llm.deepseek_client import DeepSeekClient
from app.repositories.agent_state_repository import AgentStateRepository
from app.renderers.template_renderer import TemplateRenderer
from app.repositories.clause_repository import ClauseRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.template_repository import TemplateRepository
from app.rules.rule_engine import RuleEngine
from app.services.clause_service import ClauseService
from app.services.export_service import ExportService
from app.services.extraction_service import ExtractionService
from app.services.project_service import ProjectService
from app.services.risk_repair_service import RiskRepairService
from app.services.clarification_review_service import ClarificationReviewService


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


@lru_cache(maxsize=1)
def get_agent_workflow_runner() -> AgentWorkflowRunner:
    project_service = get_project_service()
    risk_repair_service = RiskRepairService(DeepSeekClient())
    clarification_review_service = ClarificationReviewService(DeepSeekClient())
    deps = AgentNodeDependencies(
        project_service=project_service,
        extraction_service=project_service.extraction_service,
        clarification_review_service=clarification_review_service,
        clause_service=project_service.clause_service,
        export_service=project_service.export_service,
        export_guard=project_service.export_guard,
        risk_repair_service=risk_repair_service,
    )
    workflow = build_agent_graph(
        deps=deps,
        enable_interrupts=False,
    )
    state_repository = AgentStateRepository(settings.runtime_dir)
    return AgentWorkflowRunner(
        workflow=workflow,
        state_repository=state_repository,
    )
