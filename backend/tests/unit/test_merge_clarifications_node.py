from __future__ import annotations

from types import SimpleNamespace

from app.agent.nodes import merge_clarifications
from app.agent.state import create_initial_state
from app.services.clarification_review_service import ClarificationReviewResult


class _StubClarificationReviewService:
    def review(self, **kwargs):  # type: ignore[no-untyped-def]
        return ClarificationReviewResult(
            accepted=False,
            confidence=0.82,
            normalized_clarifications={
                "acceptance_standard": "acceptance by test report",
                "delivery_days": 45,
                "warranty_months": 24,
            },
            errors=[
                "budget_amount invalid: must be > 0",
                "payment_terms invalid: payment_terms must be like 30/60/10 and sum to 100",
            ],
            follow_up_questions=[
                {"field": "budget_amount", "question": "Please provide valid budget amount."},
                {"field": "payment_terms", "question": "Please provide valid payment terms."},
            ],
            reasoning=["Some clarifications are valid and should be kept."],
            used_llm=False,
        )


def test_merge_clarifications_keeps_valid_fields_and_reasks_invalid_only() -> None:
    state = create_initial_state(
        session_id="partial_clarification",
        raw_input_text="continue",
    )
    state["structured_data"] = {
        "project_name": "Server procurement project",
        "procurement_type": "goods",
        "budget_amount": None,
        "currency": "CNY",
        "method": "public_tender",
        "delivery_days": None,
        "warranty_months": None,
        "payment_terms": "",
        "delivery_batches": 1,
        "acceptance_standard": "",
        "qualification_requirements": [],
        "evaluation_method": "comprehensive_scoring",
        "technical_requirements": [],
        "special_terms": [],
        "missing_fields": [
            "budget_amount",
            "payment_terms",
            "acceptance_standard",
            "delivery_days",
            "warranty_months",
        ],
        "clarification_questions": [
            "Please provide budget.",
            "Please provide payment terms.",
            "Please provide acceptance standard.",
            "Please provide delivery days.",
            "Please provide warranty months.",
        ],
    }
    state["missing_fields"] = list(state["structured_data"]["missing_fields"])
    state["clarification_questions"] = list(state["structured_data"]["clarification_questions"])
    state["user_clarifications"] = {
        "budget_amount": "400",
        "payment_terms": "40/70/10",
        "acceptance_standard": "按测试报告验收",
        "delivery_days": "45",
        "warranty_months": "24",
    }

    deps = SimpleNamespace(
        clarification_review_service=_StubClarificationReviewService(),
    )

    result = merge_clarifications(state, deps)

    assert result["pending_human_confirmation"] is True
    assert result["missing_fields"] == ["budget_amount", "payment_terms"]
    assert result["structured_data"]["acceptance_standard"] == "acceptance by test report"
    assert result["structured_data"]["delivery_days"] == 45
    assert result["structured_data"]["warranty_months"] == 24
    assert [item["field"] for item in result["options"]] == [
        "budget_amount",
        "payment_terms",
    ]
    assert "Accepted fields were kept" in result["messages"][-1].content
