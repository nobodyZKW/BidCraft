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
from app.llm.deepseek_client import DeepSeekClient
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

    def __init__(self, llm_client: DeepSeekClient):
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
                if field == "budget_amount":
                    normalized[field] = float(raw_value)
                    if normalized[field] <= 0:
                        raise ValueError("must be > 0")
                elif field in {"delivery_days", "warranty_months"}:
                    normalized[field] = int(raw_value)
                    if normalized[field] < 0:
                        raise ValueError("must be >= 0")
                elif field == "payment_terms":
                    text = str(raw_value).strip()
                    if not self._payment_terms_valid(text):
                        raise ValueError("payment_terms must be like 30/60/10 and sum to 100")
                    normalized[field] = text.replace(" ", "")
                else:
                    normalized[field] = str(raw_value).strip()
                    if not normalized[field]:
                        raise ValueError("must be non-empty")
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
        return self.llm_client.generate_structured_json(
            task_prompt=task_prompt,
            schema=CLARIFICATION_REVIEW_SCHEMA,
            system_prompt=CLARIFICATION_REVIEW_SYSTEM_PROMPT,
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
                return ClarificationReviewResult(
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
            except ValidationError:
                pass

        return self._fallback_review(
            missing_fields=missing_fields,
            user_clarifications=user_clarifications,
        )
