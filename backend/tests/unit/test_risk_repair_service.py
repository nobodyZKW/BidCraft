from __future__ import annotations

from app.api.dependencies import get_project_service
from app.models.domain import RiskItem, RiskSeverity
from app.services.risk_repair_service import RiskRepairService


class _StubLlmClient:
    def __init__(self, payload: dict | None):
        self.payload = payload

    def invoke_structured(self, request):  # type: ignore[no-untyped-def]
        return self.payload


def _base_structured() -> dict:
    return {
        "project_name": "Server procurement project",
        "procurement_type": "goods",
        "budget_amount": 3000000,
        "currency": "CNY",
        "method": "public_tender",
        "delivery_days": 45,
        "warranty_months": 24,
        "payment_terms": "",
        "delivery_batches": 1,
        "acceptance_standard": "acceptance by test report",
        "qualification_requirements": [],
        "evaluation_method": "comprehensive_scoring",
        "technical_requirements": [],
        "special_terms": [],
        "missing_fields": [],
        "clarification_questions": [],
    }


def test_risk_repair_service_uses_llm_plan_when_valid() -> None:
    service = get_project_service()
    llm_payload = {
        "structured_patch": {"payment_terms": "20/70/10"},
        "enforce_clause_types": ["liability"],
        "reset_clause_overrides": False,
        "notes": ["llm plan"],
    }
    repair_service = RiskRepairService(_StubLlmClient(llm_payload))

    result = repair_service.apply_repair(
        raw_input_text="budget 3000000 cny",
        structured_data=_base_structured(),
        selected_clause_ids=[],
        risk_summary=[
            RiskItem(
                code="MISSING_PAYMENT_TERMS",
                message="missing payment terms",
                severity=RiskSeverity.high,
                location="payment terms",
            )
        ],
        clause_service=service.clause_service,
    )

    assert result.used_llm is True
    assert result.structured_data["payment_terms"] == "20/70/10"
    assert result.selected_clause_ids


def test_risk_repair_service_fallback_when_llm_unavailable() -> None:
    service = get_project_service()
    repair_service = RiskRepairService(_StubLlmClient(None))

    result = repair_service.apply_repair(
        raw_input_text="server procurement",
        structured_data=_base_structured(),
        selected_clause_ids=[],
        risk_summary=[
            RiskItem(
                code="MISSING_PAYMENT_TERMS",
                message="missing payment terms",
                severity=RiskSeverity.high,
                location="payment terms",
            ),
            RiskItem(
                code="MISSING_ACCEPTANCE_STANDARD",
                message="missing acceptance standard",
                severity=RiskSeverity.high,
                location="acceptance",
            ),
        ],
        clause_service=service.clause_service,
    )

    assert result.used_llm is False
    assert result.structured_data["payment_terms"] == "30/60/10"
    assert result.structured_data["acceptance_standard"]
