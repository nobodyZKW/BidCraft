from __future__ import annotations

from app.agent.graph import build_agent_graph
from app.agent.nodes import AgentNodeDependencies
from app.agent.state import create_initial_state
from app.api.dependencies import get_project_service
from app.llm.deepseek_client import DeepSeekClient
from app.services.agent_decision_service import AgentDecisionService
from app.services.clarification_review_service import ClarificationReviewService
from app.services.risk_repair_service import RiskRepairService
from app.tools.clause_tools import list_clause_alternatives_tool
from app.agent.types import ListClauseAlternativesToolInput


def _deps() -> AgentNodeDependencies:
    service = get_project_service()
    return AgentNodeDependencies(
        project_service=service,
        extraction_service=service.extraction_service,
        clarification_review_service=ClarificationReviewService(DeepSeekClient()),
        clause_service=service.clause_service,
        export_service=service.export_service,
        export_guard=service.export_guard,
        risk_repair_service=RiskRepairService(DeepSeekClient()),
        agent_decision_service=AgentDecisionService(DeepSeekClient()),
    )


def _workflow():
    return build_agent_graph(_deps(), enable_interrupts=False)


def _structured_data() -> dict:
    return {
        "project_name": "Server procurement project",
        "procurement_type": "goods",
        "budget_amount": 3000000,
        "currency": "CNY",
        "method": "public_tender",
        "delivery_days": 45,
        "warranty_months": 24,
        "payment_terms": "30/60/10",
        "delivery_batches": 1,
        "acceptance_standard": "acceptance by test report",
        "qualification_requirements": [],
        "evaluation_method": "comprehensive_scoring",
        "technical_requirements": [],
        "special_terms": [],
        "missing_fields": [],
        "clarification_questions": [],
    }


def test_graph_missing_fields_branch() -> None:
    graph = _workflow()
    state = create_initial_state(
        session_id="graph_missing",
        raw_input_text="Procure servers only.",
    )
    result = graph.invoke(state)
    assert result["missing_fields"]
    assert result["pending_human_confirmation"] is True


def test_graph_normal_generation_branch() -> None:
    graph = _workflow()
    state = create_initial_state(
        session_id="graph_normal",
        raw_input_text=(
            "Server procurement project, budget 3000000 CNY, delivery 45 days, "
            "payment 30/60/10, acceptance by test report, warranty 24 months."
        ),
    )
    result = graph.invoke(state)
    assert result["preview_html"].startswith("<html>")
    assert result["current_step"] == "respond"
    assert result["next_action"] == "done"


def test_graph_formal_export_confirm_branch() -> None:
    graph = _workflow()
    state = create_initial_state(
        session_id="graph_formal_confirm",
        raw_input_text=(
            "Please formal export. Server procurement project, budget 3000000 CNY, "
            "delivery 45 days, payment 30/60/10, acceptance by test report, warranty 24 months."
        ),
    )
    result = graph.invoke(state)
    assert result["user_intent"] == "formal_export"
    assert result["pending_human_confirmation"] is True
    assert "clarification_tools.confirm_export.pending" in result["tool_calls"]


def test_graph_override_payment_clause_branch() -> None:
    service = get_project_service()
    structured_data = _structured_data()
    alternatives = list_clause_alternatives_tool(
        ListClauseAlternativesToolInput(
            structured_data=structured_data,
            clause_type="payment",
        ),
        clause_service=service.clause_service,
    ).alternatives
    assert alternatives
    override_id = alternatives[-1]

    graph = _workflow()
    state = create_initial_state(
        session_id="graph_override",
        raw_input_text="Replace payment clause and re-validate.",
    )
    state["structured_data"] = structured_data
    state["missing_fields"] = []
    state["clarification_questions"] = []
    state["user_clarifications"] = {"override_clause_id": override_id}
    result = graph.invoke(state)
    assert result["user_intent"] == "override_payment_clause"
    assert override_id in result["selected_clause_ids"]
    assert result["validation_result"]


def test_graph_auto_repair_with_pe_branch() -> None:
    graph = _workflow()
    state = create_initial_state(
        session_id="graph_auto_repair",
        raw_input_text="Please auto repair risks with one API call.",
    )
    structured = _structured_data()
    structured["payment_terms"] = ""
    state["structured_data"] = structured
    state["missing_fields"] = []
    state["clarification_questions"] = []
    state["user_clarifications"] = {"auto_repair_with_pe": True}

    result = graph.invoke(state)
    assert "validation_tools.auto_repair_with_pe" in result["tool_calls"]
    assert result["structured_data"]["payment_terms"]


def test_graph_clarification_review_rejects_and_reasks() -> None:
    graph = _workflow()
    state = create_initial_state(
        session_id="graph_clarification_reject",
        raw_input_text="Continue workflow.",
    )
    structured = _structured_data()
    structured["payment_terms"] = ""
    structured["missing_fields"] = ["payment_terms"]
    structured["clarification_questions"] = ["Please provide payment terms."]
    state["structured_data"] = structured
    state["missing_fields"] = ["payment_terms"]
    state["clarification_questions"] = ["Please provide payment terms."]
    state["user_clarifications"] = {"payment_terms": "maybe later"}

    result = graph.invoke(state)
    assert result["pending_human_confirmation"] is True
    assert "clarification_tools.review_clarification.reject" in result["tool_calls"]
