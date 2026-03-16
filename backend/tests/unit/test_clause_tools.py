from __future__ import annotations

from app.agent.types import (
    ExplainClauseSelectionToolInput,
    ListClauseAlternativesToolInput,
    MatchClausesToolInput,
    OverrideClauseSelectionToolInput,
)
from app.api.dependencies import get_project_service
from app.tools.clause_tools import (
    explain_clause_selection_tool,
    list_clause_alternatives_tool,
    match_clauses_tool,
    override_clause_selection_tool,
)


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


def test_clause_tools_flow() -> None:
    service = get_project_service()
    structured = _structured_data()

    matched = match_clauses_tool(
        MatchClausesToolInput(structured_data=structured),
        clause_service=service.clause_service,
    )
    assert matched.selected_clause_ids

    alternatives = list_clause_alternatives_tool(
        ListClauseAlternativesToolInput(
            structured_data=structured,
            clause_type="payment",
        ),
        clause_service=service.clause_service,
    )
    assert alternatives.alternatives

    override_id = alternatives.alternatives[-1]
    overridden = override_clause_selection_tool(
        OverrideClauseSelectionToolInput(
            structured_data=structured,
            selected_clause_ids=matched.selected_clause_ids,
            override_clause_id=override_id,
        ),
        clause_service=service.clause_service,
    )
    assert override_id in overridden.selected_clause_ids

    explanation = explain_clause_selection_tool(
        ExplainClauseSelectionToolInput(
            structured_data=structured,
            selected_clause_ids=overridden.selected_clause_ids,
            clause_type="payment",
        ),
        clause_service=service.clause_service,
    )
    assert explanation.explanations
