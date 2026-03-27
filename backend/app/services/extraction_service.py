from __future__ import annotations

import re
from typing import Any

from jsonschema import ValidationError, validate

from app.agent.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_TASK_TEMPLATE
from app.schemas.json_schemas import EXTRACTION_SCHEMA
from app.llm.types import StructuredLLMClient, StructuredLLMRequest


MVP_REQUIRED_FIELDS = [
    "project_name",
    "budget_amount",
    "payment_terms",
    "acceptance_standard",
    "delivery_days",
    "warranty_months",
]


CLARIFY_QUESTIONS = {
    "project_name": "请补充项目名称。",
    "budget_amount": "请补充预算金额（例如 3000000 CNY）。",
    "payment_terms": "请补充付款条款（例如 30/60/10）。",
    "acceptance_standard": "请补充验收标准。",
    "delivery_days": "请补充交付周期（天）。",
    "warranty_months": "请补充质保期限（月）。",
}


class ExtractionService:
    def __init__(self, llm_client: StructuredLLMClient):
        self.llm_client = llm_client

    @staticmethod
    def _budget_from_text(text: str) -> float:
        lower = text.lower()

        match = re.search(r"(\d+(?:\.\d+)?)\s*(万|万元|元|cny|rmb)", lower)
        if match:
            amount = float(match.group(1))
            unit = match.group(2)
            if unit in {"万", "万元"}:
                return amount * 10000
            return amount

        match = re.search(r"(?:预算|budget)\D{0,6}(\d+(?:\.\d+)?)", lower)
        if match:
            return float(match.group(1))

        return 0

    @staticmethod
    def _delivery_days(text: str) -> int:
        match = re.search(r"(\d{1,4})\s*(?:天|day|days)", text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 0

    @staticmethod
    def _warranty_months(text: str) -> int:
        year_match = re.search(
            r"(?:质保|warranty)?\s*(\d{1,2})\s*(?:年|years?)",
            text,
            flags=re.IGNORECASE,
        )
        if year_match:
            return int(year_match.group(1)) * 12

        month_match = re.search(
            r"(?:质保|warranty)?\s*(\d{1,3})\s*(?:个月|月|months?)",
            text,
            flags=re.IGNORECASE,
        )
        if month_match:
            return int(month_match.group(1))

        return 0

    @staticmethod
    def _payment_terms(text: str) -> str:
        match = re.search(r"(\d{1,3}\s*/\s*\d{1,3}\s*/\s*\d{1,3})", text)
        if not match:
            return ""
        return match.group(1).replace(" ", "")

    @staticmethod
    def _acceptance_standard(text: str) -> str:
        lines = re.split(r"[。；;\n]", text)
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "验收" in line or "acceptance" in line.lower():
                return line
        return ""

    @staticmethod
    def _project_name(text: str) -> str:
        match = re.search(r"([A-Za-z0-9\u4e00-\u9fff]{2,50}项目)", text)
        if match:
            return match.group(1)

        first_clause = re.split(r"[，,。；;\n]", text)[0].strip()
        if first_clause and len(first_clause) <= 40:
            return first_clause

        return "未命名采购项目"

    @staticmethod
    def _collect_list_by_keywords(text: str, keywords: list[str]) -> list[str]:
        items: list[str] = []
        for fragment in re.split(r"[。；;\n]", text):
            line = fragment.strip()
            if not line:
                continue
            lowered = line.lower()
            if any(keyword.lower() in lowered for keyword in keywords):
                items.append(line)
        return items

    def _fallback_extract(self, raw_input_text: str) -> dict[str, Any]:
        technical_requirements = self._collect_list_by_keywords(
            raw_input_text,
            ["技术", "参数", "规格", "性能", "technical", "spec", "cpu", "memory", "storage"],
        )
        qualification = self._collect_list_by_keywords(
            raw_input_text,
            ["资格", "供应商", "资质", "业绩", "qualification", "supplier", "experience"],
        )

        payload = {
            "project_name": self._project_name(raw_input_text),
            "procurement_type": "goods",
            "budget_amount": self._budget_from_text(raw_input_text),
            "currency": "CNY",
            "method": "public_tender",
            "delivery_days": self._delivery_days(raw_input_text),
            "warranty_months": self._warranty_months(raw_input_text),
            "payment_terms": self._payment_terms(raw_input_text),
            "delivery_batches": 1,
            "acceptance_standard": self._acceptance_standard(raw_input_text),
            "qualification_requirements": qualification,
            "evaluation_method": "comprehensive_scoring",
            "technical_requirements": technical_requirements,
            "special_terms": [],
            "missing_fields": [],
            "clarification_questions": [],
        }
        self._fill_missing(payload)
        return payload

    @staticmethod
    def _fill_missing(payload: dict[str, Any]) -> None:
        missing = []
        for field in MVP_REQUIRED_FIELDS:
            value = payload.get(field)
            if value in (None, "", 0, []):
                missing.append(field)
        payload["missing_fields"] = missing
        payload["clarification_questions"] = [
            CLARIFY_QUESTIONS[field] for field in missing if field in CLARIFY_QUESTIONS
        ]

    @staticmethod
    def _validate_payload(payload: dict[str, Any]) -> None:
        validate(instance=payload, schema=EXTRACTION_SCHEMA)

    def extract(self, raw_input_text: str) -> dict[str, Any]:
        last_error: str = ""
        for _ in range(2):
            llm_result = self.llm_client.invoke_structured(
                StructuredLLMRequest(
                    task_name="extraction.requirements",
                    task_prompt=EXTRACTION_TASK_TEMPLATE.format(
                        raw_input_text=raw_input_text
                    ),
                    schema=EXTRACTION_SCHEMA,
                    system_prompt=EXTRACTION_SYSTEM_PROMPT,
                    metadata={"raw_input_preview": raw_input_text[:120]},
                )
            )
            if llm_result is None:
                last_error = "LLM unavailable or returned invalid response."
                continue

            self._fill_missing(llm_result)
            try:
                self._validate_payload(llm_result)
                return llm_result
            except ValidationError as exc:
                last_error = str(exc)

        fallback = self._fallback_extract(raw_input_text)
        try:
            self._validate_payload(fallback)
            return fallback
        except ValidationError as exc:
            raise ValueError(f"抽取失败，请人工录入。原因: {last_error or str(exc)}") from exc
