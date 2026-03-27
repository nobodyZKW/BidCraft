from __future__ import annotations

from app.services.agent_decision_service import AgentDecisionService


class StubLLMClient:
    def __init__(self, payload: dict | None):
        self.payload = payload

    def invoke_structured(self, request):  # noqa: ANN001
        return self.payload

    def invoke_text(self, request):  # noqa: ANN001
        return None


def test_decide_intent_uses_llm_payload_when_valid() -> None:
    service = AgentDecisionService(
        StubLLMClient(
            {
                "intent": "formal_export",
                "confidence": 0.91,
                "reason": "user explicitly asked for formal export",
            }
        )
    )

    result = service.decide_intent(text="Please formal export this procurement document.")

    assert result.intent == "formal_export"
    assert result.used_llm is True


def test_decide_intent_falls_back_when_llm_missing() -> None:
    service = AgentDecisionService(StubLLMClient(None))

    result = service.decide_intent(text="Replace payment clause and continue.")

    assert result.intent == "override_payment_clause"
    assert result.used_llm is False


def test_decide_intent_fast_path_detects_edit_document() -> None:
    service = AgentDecisionService(StubLLMClient(None))

    result = service.decide_intent(text="帮我把项目名称改为xxxx测试")

    assert result.intent == "edit_document"
    assert result.used_llm is False


def test_decide_clarification_rejects_invalid_llm_action_and_falls_back() -> None:
    service = AgentDecisionService(
        StubLLMClient(
            {
                "next_action": "render_preview",
                "confidence": 0.8,
                "reason": "invalid for clarification router",
            }
        )
    )

    result = service.decide_clarification(
        intent="generate_document",
        missing_fields=["payment_terms"],
        clarification_questions=["Please provide payment terms."],
        user_clarifications={},
    )

    assert result.next_action == "ask_for_clarification"
    assert result.used_llm is False


def test_decide_repair_uses_fallback_branching() -> None:
    service = AgentDecisionService(StubLLMClient(None))

    result = service.decide_repair(
        intent="generate_document",
        can_export_formal=False,
        allow_draft=False,
        auto_repair=True,
        risk_summary=[{"code": "MISSING_PAYMENT_TERMS", "severity": "high"}],
    )

    assert result.next_action == "auto_repair_with_pe"
    assert result.used_llm is False
