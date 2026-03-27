from __future__ import annotations

from app.agent.types import AgentMessage
from app.services.clarification_review_service import ClarificationReviewService


class _StubLlmClient:
    def __init__(self, payload: dict | None):
        self.payload = payload

    def invoke_structured(self, request):  # type: ignore[no-untyped-def]
        return self.payload


def test_clarification_review_service_llm_accepts_payload() -> None:
    service = ClarificationReviewService(
        _StubLlmClient(
            {
                "accepted": True,
                "confidence": 0.95,
                "normalized_clarifications": {"budget_amount": 3000000},
                "errors": [],
                "follow_up_questions": [],
                "reasoning": ["ok"],
            }
        )
    )
    result = service.review(
        messages=[AgentMessage(role="user", content="budget is 3000000 cny")],
        raw_input_text="budget is 3000000 cny",
        structured_data={},
        missing_fields=["budget_amount"],
        clarification_questions=["provide budget"],
        user_clarifications={"budget_amount": "3000000"},
    )
    assert result.accepted is True
    assert result.used_llm is True
    assert result.normalized_clarifications["budget_amount"] == 3000000


def test_clarification_review_service_fallback_rejects_invalid_payload() -> None:
    service = ClarificationReviewService(_StubLlmClient(None))
    result = service.review(
        messages=[AgentMessage(role="user", content="payment maybe flexible")],
        raw_input_text="payment maybe flexible",
        structured_data={},
        missing_fields=["payment_terms"],
        clarification_questions=["provide payment terms"],
        user_clarifications={"payment_terms": "maybe later"},
    )
    assert result.accepted is False
    assert result.used_llm is False
    assert result.errors


def test_clarification_review_service_fallback_normalizes_user_friendly_values() -> None:
    service = ClarificationReviewService(_StubLlmClient(None))
    result = service.review(
        messages=[AgentMessage(role="user", content="补充澄清")],
        raw_input_text="补充澄清",
        structured_data={},
        missing_fields=[
            "budget_amount",
            "payment_terms",
            "acceptance_standard",
            "delivery_days",
            "warranty_months",
        ],
        clarification_questions=[],
        user_clarifications={
            "budget_amount": "300万元",
            "payment_terms": "30/60/10",
            "acceptance_standard": "国家标准",
            "delivery_days": "30天",
            "warranty_months": "12个月",
        },
    )
    assert result.accepted is True
    assert result.normalized_clarifications["budget_amount"] == 3000000
    assert result.normalized_clarifications["payment_terms"] == "30/60/10"
    assert result.normalized_clarifications["acceptance_standard"] == "按国家标准验收"
    assert result.normalized_clarifications["delivery_days"] == 30
    assert result.normalized_clarifications["warranty_months"] == 12
