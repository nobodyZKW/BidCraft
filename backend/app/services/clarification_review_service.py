from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError, validate

from app.agent.prompts import (
    CLARIFICATION_REVIEW_SYSTEM_PROMPT,
    CLARIFICATION_REVIEW_TASK_TEMPLATE,
)
from app.agent.types import AgentMessage
from app.llm.types import StructuredLLMClient, StructuredLLMRequest
from app.schemas.json_schemas import CLARIFICATION_REVIEW_SCHEMA
from app.services.extraction_service import CLARIFY_QUESTIONS


@dataclass(slots=True)
class ClarificationReviewResult:
    accepted: bool
    confidence: float
    normalized_clarifications: dict[str, Any]
    errors: list[str]
    follow_up_questions: list[dict[str, str]]
    reasoning: list[str]
    used_llm: bool


class ClarificationReviewService:
    """Review clarification payload quality before merge (LLM + deterministic fallback)."""

    def __init__(self, llm_client: StructuredLLMClient):
        self.llm_client = llm_client

    @staticmethod
    def _format_chat_history(messages: list[AgentMessage]) -> str:
        if not messages:
            return "(empty)"
        rows: list[str] = []
        for idx, message in enumerate(messages, start=1):
            rows.append(f"{idx}. [{message.role}] {message.content}")
        return "\n".join(rows)

    @staticmethod
    def _payment_terms_valid(value: str) -> bool:
        text = value.replace(" ", "")
        matched = re.match(r"^(\d{1,3})/(\d{1,3})/(\d{1,3})$", text)
        if not matched:
            return False
        first = int(matched.group(1))
        second = int(matched.group(2))
        third = int(matched.group(3))
        return first + second + third == 100

    @staticmethod
    def _normalize_budget_amount(raw_value: Any) -> float:
        text = str(raw_value).strip().replace(",", "")
        matched = re.match(r"^(\d+(?:\.\d+)?)\s*(万)?\s*(元|cny)?$", text, re.IGNORECASE)
        if not matched:
            raise ValueError("must be a valid amount such as 300万元 or 3000000")
        amount = float(matched.group(1))
        if matched.group(2):
            amount *= 10000
        if amount <= 0:
            raise ValueError("must be > 0")
        return amount

    @staticmethod
    def _normalize_int_field(raw_value: Any, *, unit_words: tuple[str, ...]) -> int:
        text = str(raw_value).strip().replace(" ", "")
        for unit in unit_words:
            text = text.replace(unit, "")
        matched = re.match(r"^\d+$", text)
        if not matched:
            raise ValueError("must be a non-negative integer")
        value = int(text)
        if value < 0:
            raise ValueError("must be >= 0")
        return value

    @staticmethod
    def _normalize_payment_terms(raw_value: Any) -> str:
        text = (
            str(raw_value)
            .strip()
            .replace("／", "/")
            .replace(" ", "")
            .replace("%", "")
        )
        if not ClarificationReviewService._payment_terms_valid(text):
            raise ValueError("payment_terms must be like 30/60/10 and sum to 100")
        return text

    @staticmethod
    def _normalize_acceptance_standard(raw_value: Any) -> str:
        text = str(raw_value).strip()
        if not text:
            raise ValueError("must be non-empty")
        aliases = {
            "国家标准": "按国家标准验收",
            "按国家标准": "按国家标准验收",
            "测试报告": "按测试报告验收",
            "按测试报告": "按测试报告验收",
        }
        return aliases.get(text, text)

    def _normalize_field_value(self, field: str, raw_value: Any) -> Any:
        if field == "budget_amount":
            return self._normalize_budget_amount(raw_value)
        if field == "delivery_days":
            return self._normalize_int_field(raw_value, unit_words=("天", "日"))
        if field == "warranty_months":
            return self._normalize_int_field(raw_value, unit_words=("个月", "月"))
        if field == "payment_terms":
            return self._normalize_payment_terms(raw_value)
        if field == "acceptance_standard":
            return self._normalize_acceptance_standard(raw_value)
        text = str(raw_value).strip()
        if not text:
            raise ValueError("must be non-empty")
        return text

    def _fallback_review(
        self,
        *,
        missing_fields: list[str],
        user_clarifications: dict[str, Any],
    ) -> ClarificationReviewResult:
        normalized: dict[str, Any] = {}
        errors: list[str] = []
        follow_up: list[dict[str, str]] = []

        for field in missing_fields:
            raw_value = user_clarifications.get(field)
            if raw_value in (None, "", []):
                errors.append(f"{field} is still empty.")
                follow_up.append(
                    {
                        "field": field,
                        "question": CLARIFY_QUESTIONS.get(field, f"Please provide {field}."),
                    }
                )
                continue

            try:
                normalized[field] = self._normalize_field_value(field, raw_value)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{field} invalid: {exc}")
                follow_up.append(
                    {
                        "field": field,
                        "question": CLARIFY_QUESTIONS.get(field, f"Please provide valid {field}."),
                    }
                )

        accepted = len(errors) == 0
        reasoning = (
            ["Fallback review accepted clarifications."]
            if accepted
            else ["Fallback review rejected clarifications; user must retry."]
        )
        return ClarificationReviewResult(
            accepted=accepted,
            confidence=0.75 if accepted else 0.5,
            normalized_clarifications=normalized,
            errors=errors,
            follow_up_questions=follow_up,
            reasoning=reasoning,
            used_llm=False,
        )

    def _llm_review(
        self,
        *,
        messages: list[AgentMessage],
        raw_input_text: str,
        structured_data: dict[str, Any],
        missing_fields: list[str],
        clarification_questions: list[str],
        user_clarifications: dict[str, Any],
    ) -> dict[str, Any] | None:
        task_prompt = CLARIFICATION_REVIEW_TASK_TEMPLATE.format(
            chat_history=self._format_chat_history(messages),
            raw_input_text=raw_input_text,
            structured_data=json.dumps(structured_data, ensure_ascii=False),
            missing_fields=json.dumps(missing_fields, ensure_ascii=False),
            clarification_questions=json.dumps(clarification_questions, ensure_ascii=False),
            user_clarifications=json.dumps(user_clarifications, ensure_ascii=False),
        )
        return self.llm_client.invoke_structured(
            StructuredLLMRequest(
                task_name="clarification.review",
                task_prompt=task_prompt,
                schema=CLARIFICATION_REVIEW_SCHEMA,
                system_prompt=CLARIFICATION_REVIEW_SYSTEM_PROMPT,
                metadata={
                    "missing_fields": missing_fields,
                    "clarification_count": len(user_clarifications),
                },
            )
        )

    def review(
        self,
        *,
        messages: list[AgentMessage],
        raw_input_text: str,
        structured_data: dict[str, Any],
        missing_fields: list[str],
        clarification_questions: list[str],
        user_clarifications: dict[str, Any],
    ) -> ClarificationReviewResult:
        fallback_result = self._fallback_review(
            missing_fields=missing_fields,
            user_clarifications=user_clarifications,
        )
        llm_payload = self._llm_review(
            messages=messages,
            raw_input_text=raw_input_text,
            structured_data=structured_data,
            missing_fields=missing_fields,
            clarification_questions=clarification_questions,
            user_clarifications=user_clarifications,
        )

        if llm_payload is not None:
            try:
                validate(instance=llm_payload, schema=CLARIFICATION_REVIEW_SCHEMA)
                llm_result = ClarificationReviewResult(
                    accepted=bool(llm_payload["accepted"]),
                    confidence=float(llm_payload["confidence"]),
                    normalized_clarifications=dict(llm_payload["normalized_clarifications"]),
                    errors=[str(item) for item in llm_payload["errors"]],
                    follow_up_questions=[
                        {"field": str(item["field"]), "question": str(item["question"])}
                        for item in llm_payload["follow_up_questions"]
                    ],
                    reasoning=[str(item) for item in llm_payload["reasoning"]],
                    used_llm=True,
                )
                if fallback_result.accepted and not llm_result.accepted:
                    return fallback_result
                if (
                    len(fallback_result.normalized_clarifications)
                    > len(llm_result.normalized_clarifications)
                ):
                    return ClarificationReviewResult(
                        accepted=llm_result.accepted and fallback_result.accepted,
                        confidence=max(llm_result.confidence, fallback_result.confidence),
                        normalized_clarifications={
                            **llm_result.normalized_clarifications,
                            **fallback_result.normalized_clarifications,
                        },
                        errors=(
                            fallback_result.errors
                            if len(fallback_result.errors) <= len(llm_result.errors)
                            else llm_result.errors
                        ),
                        follow_up_questions=(
                            fallback_result.follow_up_questions
                            if len(fallback_result.follow_up_questions)
                            >= len(llm_result.follow_up_questions)
                            else llm_result.follow_up_questions
                        ),
                        reasoning=[*llm_result.reasoning, *fallback_result.reasoning],
                        used_llm=True,
                    )
                return llm_result
            except ValidationError:
                pass

        return fallback_result
