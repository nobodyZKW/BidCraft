from __future__ import annotations

from datetime import date

from app.agent.types import (
    CheckFormalExportEligibilityToolInput,
    ExplainRiskSummaryToolInput,
    SuggestFixPlanToolInput,
    ValidateDocumentToolInput,
    ValidationToolResult,
)
from app.api.dependencies import get_project_service
from app.models.domain import RiskItem, RiskSeverity, ValidationResult
from app.rules.export_guard import FormalExportGuard
from app.tools.validation_tools import (
    check_formal_export_eligibility_tool,
    explain_risk_summary_tool,
    suggest_fix_plan_tool,
    validate_document_tool,
)


def _structured(payment_terms: str) -> dict:
    return {
        "project_name": "Server procurement project",
        "procurement_type": "goods",
        "budget_amount": 3000000,
        "currency": "CNY",
        "method": "public_tender",
        "delivery_days": 45,
        "warranty_months": 24,
        "payment_terms": payment_terms,
        "delivery_batches": 1,
        "acceptance_standard": "acceptance by test report",
        "qualification_requirements": [],
        "evaluation_method": "comprehensive_scoring",
        "technical_requirements": [],
        "special_terms": [],
        "missing_fields": [],
        "clarification_questions": [],
    }


def test_validation_tools_with_guard_and_explain_and_fix_plan() -> None:
    service = get_project_service()
    validation = validate_document_tool(
        ValidateDocumentToolInput(
            structured_data=_structured("70/20/10"),
            selected_clause_ids=[],
        ),
        clause_service=service.clause_service,
        template_renderer=service.template_renderer,
        rule_engine=service.rule_engine,
    )
    assert validation.high_risk_codes

    explained = explain_risk_summary_tool(
        ExplainRiskSummaryToolInput(risk_summary=validation.risk_summary)
    )
    assert explained.summary_text.startswith("high=")

    suggested = suggest_fix_plan_tool(
        SuggestFixPlanToolInput(
            validation_result=validation,
            missing_fields=[],
        )
    )
    assert suggested.fix_steps

    eligibility = check_formal_export_eligibility_tool(
        CheckFormalExportEligibilityToolInput(validation_result=validation)
    )
    assert eligibility.can_export_formal is False


def test_formal_export_guard_allows_low_risk() -> None:
    guard = FormalExportGuard()
    result = ValidationResult(
        risk_summary=[
            RiskItem(
                code="LOW",
                message="ok",
                severity=RiskSeverity.low,
                location="doc",
            )
        ],
        can_export_formal=True,
    )
    assert guard.can_export_formal(result) is True
    guard.assert_formal_export_allowed(result)


def test_formal_export_guard_blocks_high_risk() -> None:
    guard = FormalExportGuard()
    result = ValidationResult(
        risk_summary=[
            RiskItem(
                code="HIGH",
                message="blocked",
                severity=RiskSeverity.high,
                location="doc",
            )
        ],
        can_export_formal=False,
    )
    assert guard.can_export_formal(result) is False
    try:
        guard.assert_formal_export_allowed(result)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")

