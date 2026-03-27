from __future__ import annotations

from functools import lru_cache

from app.agent.graph import build_agent_graph
from app.agent.nodes import AgentNodeDependencies
from app.agent.run_logger import AgentRunLogger
from app.agent.runtime import AgentWorkflowRunner
from app.core.settings import settings
from app.llm.deepseek_client import DeepSeekClient
from app.repositories.agent_state_repository import AgentStateRepository
from app.renderers.template_renderer import TemplateRenderer
from app.repositories.clause_repository import ClauseRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.rule_repository import RuleRepository
from app.repositories.template_repository import TemplateRepository
from app.rules.rule_engine import RuleEngine
from app.services.agent_decision_service import AgentDecisionService
from app.services.clause_service import ClauseService
from app.services.export_service import ExportService
from app.services.extraction_service import ExtractionService
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService
from app.services.project_service import ProjectService
from app.services.risk_repair_service import RiskRepairService
from app.services.clarification_review_service import ClarificationReviewService
from app.services.document_edit_service import DocumentEditService
from app.services.evaluation_service import EvaluationService
from app.retrieval.types import KnowledgeDocument


@lru_cache(maxsize=1)
def get_llm_client() -> DeepSeekClient:
    return DeepSeekClient()


@lru_cache(maxsize=1)
def get_knowledge_retrieval_service() -> KnowledgeRetrievalService:
    clause_repo = ClauseRepository(settings.data_dir / "clauses" / "clauses.json")
    rule_repo = RuleRepository(settings.data_dir / "seeds" / "rule_config.json")

    documents: list[KnowledgeDocument] = []
    for clause in clause_repo.load_all():
        documents.append(
            KnowledgeDocument(
                source_id=clause.clause_id,
                title=clause.clause_name,
                content=clause.content_template,
                source_type="clause",
                metadata={
                    "clause_id": clause.clause_id,
                    "clause_type": clause.clause_type,
                    "version": clause.version,
                },
            )
        )

    for rule in rule_repo.load_all():
        documents.append(
            KnowledgeDocument(
                source_id=str(rule["rule_code"]),
                title=str(rule["rule_name"]),
                content=(
                    f"rule_code={rule['rule_code']}; "
                    f"severity={rule['severity']}; "
                    f"rule_type={rule['rule_type']}; "
                    f"config={rule.get('config', {})}"
                ),
                source_type="rule",
                metadata={
                    "rule_code": str(rule["rule_code"]),
                    "severity": str(rule["severity"]),
                    "rule_type": str(rule["rule_type"]),
                },
            )
        )

    return KnowledgeRetrievalService(documents)


@lru_cache(maxsize=1)
def get_project_service() -> ProjectService:
    project_repo = ProjectRepository(settings.runtime_dir)
    clause_repo = ClauseRepository(settings.data_dir / "clauses" / "clauses.json")
    template_repo = TemplateRepository(settings.data_dir / "templates" / "document_template.json")

    extraction_service = ExtractionService(get_llm_client())
    clause_service = ClauseService(clause_repo, get_knowledge_retrieval_service())
    template_renderer = TemplateRenderer(template_repo)
    rule_engine = RuleEngine(get_knowledge_retrieval_service())
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
    risk_repair_service = RiskRepairService(get_llm_client())
    clarification_review_service = ClarificationReviewService(get_llm_client())
    agent_decision_service = AgentDecisionService(get_llm_client())
    document_edit_service = DocumentEditService()
    deps = AgentNodeDependencies(
        project_service=project_service,
        extraction_service=project_service.extraction_service,
        clarification_review_service=clarification_review_service,
        clause_service=project_service.clause_service,
        export_service=project_service.export_service,
        export_guard=project_service.export_guard,
        risk_repair_service=risk_repair_service,
        agent_decision_service=agent_decision_service,
        document_edit_service=document_edit_service,
    )
    workflow = build_agent_graph(
        deps=deps,
        enable_interrupts=False,
    )
    state_repository = AgentStateRepository(settings.runtime_dir)
    return AgentWorkflowRunner(
        workflow=workflow,
        state_repository=state_repository,
        run_logger=AgentRunLogger(settings.runtime_dir / "agent_runs.jsonl"),
    )


@lru_cache(maxsize=1)
def get_evaluation_service() -> EvaluationService:
    return EvaluationService(
        project_service=get_project_service(),
        cases_path=settings.data_dir / "seeds" / "requirement_cases.json",
        report_path=settings.runtime_dir / "evaluation_latest.json",
    )
