from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError, validate

from app.agent.prompts import (
    CLARIFICATION_DECISION_SYSTEM_PROMPT,
    CLARIFICATION_DECISION_TASK_TEMPLATE,
    INTENT_DECISION_SYSTEM_PROMPT,
    INTENT_DECISION_TASK_TEMPLATE,
    REPAIR_DECISION_SYSTEM_PROMPT,
    REPAIR_DECISION_TASK_TEMPLATE,
)
from app.llm.types import StructuredLLMClient, StructuredLLMRequest
from app.models.domain import RiskSeverity
from app.schemas.json_schemas import INTENT_DECISION_SCHEMA, NEXT_ACTION_DECISION_SCHEMA


@dataclass(slots=True)
class IntentDecisionResult:
    intent: str
    confidence: float
    reason: str
    used_llm: bool


@dataclass(slots=True)
class NextActionDecisionResult:
    next_action: str
    confidence: float
    reason: str
    used_llm: bool


class AgentDecisionService:
    """LLM-assisted routing decisions with deterministic fallback."""

    def __init__(self, llm_client: StructuredLLMClient):
        self.llm_client = llm_client

    @staticmethod
    def infer_intent_fallback(text: str) -> IntentDecisionResult:
        lowered = text.lower()
        if any(token in lowered for token in ["missing", "缺失", "字段"]):
            intent = "view_missing_fields"
        elif (
            ("payment" in lowered or "付款" in text)
            and any(token in lowered for token in ["replace", "override", "替换", "覆盖"])
        ):
            intent = "override_payment_clause"
        elif "formal" in lowered or "正式" in text:
            intent = "formal_export"
        elif "draft" in lowered or "草稿" in text:
            intent = "draft_export"
        else:
            intent = "generate_document"
        return IntentDecisionResult(
            intent=intent,
            confidence=0.6,
            reason="deterministic_fallback",
            used_llm=False,
        )

    @staticmethod
    def decide_clarification_fallback(
        *,
        intent: str,
        missing_fields: list[str],
        user_clarifications: dict[str, Any],
    ) -> NextActionDecisionResult:
        if intent == "view_missing_fields":
            next_action = "respond"
        elif missing_fields and user_clarifications:
            next_action = "merge_clarifications"
        elif missing_fields:
            next_action = "ask_for_clarification"
        else:
            next_action = "match_clauses"
        return NextActionDecisionResult(
            next_action=next_action,
            confidence=0.7,
            reason="deterministic_fallback",
            used_llm=False,
        )

    @staticmethod
    def decide_repair_fallback(
        *,
        intent: str,
        can_export_formal: bool,
        allow_draft: bool,
        auto_repair: bool,
    ) -> NextActionDecisionResult:
        if intent == "override_payment_clause":
            next_action = "respond"
        elif not can_export_formal:
            if auto_repair:
                next_action = "auto_repair_with_pe"
            elif intent == "draft_export" or allow_draft:
                next_action = "render_preview"
            else:
                next_action = "build_fix_options"
        else:
            if intent in {"formal_export", "draft_export", "generate_document", "edit_document"}:
                next_action = "render_preview"
            else:
                next_action = "respond"
        return NextActionDecisionResult(
            next_action=next_action,
            confidence=0.7,
            reason="deterministic_fallback",
            used_llm=False,
        )

    def decide_intent(self, *, text: str) -> IntentDecisionResult:
        if (
            any(token in text for token in ["修改", "改为", "改成", "变更", "更新"])
            or re.search(
                r"(project_name|budget_amount|payment_terms|acceptance_standard|delivery_days|warranty_months)\s*[:=：]",
                text,
            )
        ):
            return IntentDecisionResult(
                intent="edit_document",
                confidence=0.85,
                reason="edit_intent_fast_path",
                used_llm=False,
            )
        payload = self.llm_client.invoke_structured(
            StructuredLLMRequest(
                task_name="agent.decide_intent",
                system_prompt=INTENT_DECISION_SYSTEM_PROMPT,
                task_prompt=INTENT_DECISION_TASK_TEMPLATE.format(user_text=text),
                schema=INTENT_DECISION_SCHEMA,
                metadata={"text_length": len(text)},
            )
        )
        if payload is not None:
            try:
                validate(instance=payload, schema=INTENT_DECISION_SCHEMA)
                return IntentDecisionResult(
                    intent=str(payload["intent"]),
                    confidence=float(payload["confidence"]),
                    reason=str(payload["reason"]),
                    used_llm=True,
                )
            except ValidationError:
                pass
        return self.infer_intent_fallback(text)

    def decide_clarification(
        self,
        *,
        intent: str,
        missing_fields: list[str],
        clarification_questions: list[str],
        user_clarifications: dict[str, Any],
    ) -> NextActionDecisionResult:
        payload = self.llm_client.invoke_structured(
            StructuredLLMRequest(
                task_name="agent.decide_clarification",
                system_prompt=CLARIFICATION_DECISION_SYSTEM_PROMPT,
                task_prompt=CLARIFICATION_DECISION_TASK_TEMPLATE.format(
                    intent=intent,
                    missing_fields=json.dumps(missing_fields, ensure_ascii=False),
                    clarification_questions=json.dumps(
                        clarification_questions,
                        ensure_ascii=False,
                    ),
                    clarification_keys=json.dumps(
                        sorted(user_clarifications.keys()),
                        ensure_ascii=False,
                    ),
                ),
                schema=NEXT_ACTION_DECISION_SCHEMA,
                metadata={
                    "intent": intent,
                    "missing_fields": missing_fields,
                    "clarification_count": len(user_clarifications),
                },
            )
        )
        if payload is not None:
            try:
                validate(instance=payload, schema=NEXT_ACTION_DECISION_SCHEMA)
                next_action = str(payload["next_action"])
                if next_action in {
                    "respond",
                    "merge_clarifications",
                    "ask_for_clarification",
                    "match_clauses",
                }:
                    return NextActionDecisionResult(
                        next_action=next_action,
                        confidence=float(payload["confidence"]),
                        reason=str(payload["reason"]),
                        used_llm=True,
                    )
            except ValidationError:
                pass
        return self.decide_clarification_fallback(
            intent=intent,
            missing_fields=missing_fields,
            user_clarifications=user_clarifications,
        )

    def decide_repair(
        self,
        *,
        intent: str,
        can_export_formal: bool,
        allow_draft: bool,
        auto_repair: bool,
        risk_summary: list[dict[str, Any]],
    ) -> NextActionDecisionResult:
        high_risk_codes = [
            str(item.get("code", ""))
            for item in risk_summary
            if str(item.get("severity", "")).lower() == RiskSeverity.high.value
        ]
        payload = self.llm_client.invoke_structured(
            StructuredLLMRequest(
                task_name="agent.decide_repair",
                system_prompt=REPAIR_DECISION_SYSTEM_PROMPT,
                task_prompt=REPAIR_DECISION_TASK_TEMPLATE.format(
                    intent=intent,
                    can_export_formal=can_export_formal,
                    allow_draft=allow_draft,
                    auto_repair=auto_repair,
                    high_risk_codes=json.dumps(high_risk_codes, ensure_ascii=False),
                ),
                schema=NEXT_ACTION_DECISION_SCHEMA,
                metadata={
                    "intent": intent,
                    "can_export_formal": can_export_formal,
                    "allow_draft": allow_draft,
                    "auto_repair": auto_repair,
                    "high_risk_codes": high_risk_codes,
                },
            )
        )
        if payload is not None:
            try:
                validate(instance=payload, schema=NEXT_ACTION_DECISION_SCHEMA)
                next_action = str(payload["next_action"])
                if next_action in {
                    "respond",
                    "auto_repair_with_pe",
                    "build_fix_options",
                    "render_preview",
                }:
                    return NextActionDecisionResult(
                        next_action=next_action,
                        confidence=float(payload["confidence"]),
                        reason=str(payload["reason"]),
                        used_llm=True,
                    )
            except ValidationError:
                pass
        return self.decide_repair_fallback(
            intent=intent,
            can_export_formal=can_export_formal,
            allow_draft=allow_draft,
            auto_repair=auto_repair,
        )
