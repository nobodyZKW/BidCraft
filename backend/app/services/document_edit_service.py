from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


EDITABLE_FIELDS = {
    "project_name",
    "budget_amount",
    "payment_terms",
    "acceptance_standard",
    "delivery_days",
    "warranty_months",
}


@dataclass(slots=True)
class DocumentEditResult:
    structured_data: dict[str, Any]
    updated_fields: list[str]


class DocumentEditService:
    """Parse user edit instructions into structured-data patches."""

    @staticmethod
    def _normalize_budget_amount(raw_value: str) -> float:
        text = raw_value.strip().replace(",", "").replace(" ", "")
        matched = re.match(r"^(\d+(?:\.\d+)?)\s*(万)?\s*(元|cny|rmb)?$", text, re.IGNORECASE)
        if not matched:
            raise ValueError("invalid budget amount")
        amount = float(matched.group(1))
        if matched.group(2):
            amount *= 10000
        return amount

    @staticmethod
    def _normalize_int_value(raw_value: str, *, units: tuple[str, ...]) -> int:
        text = raw_value.strip().replace(" ", "")
        for unit in units:
            text = text.replace(unit, "")
        if not re.match(r"^\d+$", text):
            raise ValueError("invalid integer value")
        return int(text)

    @staticmethod
    def _normalize_payment_terms(raw_value: str) -> str:
        text = raw_value.strip().replace(" ", "").replace("／", "/").replace("%", "")
        matched = re.match(r"^(\d{1,3})/(\d{1,3})/(\d{1,3})$", text)
        if not matched:
            raise ValueError("invalid payment terms")
        if sum(int(item) for item in matched.groups()) != 100:
            raise ValueError("payment terms must sum to 100")
        return text

    @staticmethod
    def _normalize_acceptance_standard(raw_value: str) -> str:
        text = raw_value.strip()
        aliases = {
            "国家标准": "按国家标准验收",
            "按国家标准": "按国家标准验收",
            "测试报告": "按测试报告验收",
            "按测试报告": "按测试报告验收",
        }
        return aliases.get(text, text)

    def _normalize_value(self, field: str, raw_value: str) -> Any:
        if field == "budget_amount":
            return self._normalize_budget_amount(raw_value)
        if field == "delivery_days":
            return self._normalize_int_value(raw_value, units=("天", "日"))
        if field == "warranty_months":
            return self._normalize_int_value(raw_value, units=("个月", "月"))
        if field == "payment_terms":
            return self._normalize_payment_terms(raw_value)
        if field == "acceptance_standard":
            return self._normalize_acceptance_standard(raw_value)
        return raw_value.strip()

    def _extract_inline_assignments(self, text: str) -> dict[str, Any]:
        patch: dict[str, Any] = {}
        entries = [item.strip() for item in re.split(r"[;\n；]+", text) if item.strip()]
        for entry in entries:
            matched = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*[:=：]\s*(.+)$", entry)
            if not matched:
                continue
            field = matched.group(1).strip()
            value = matched.group(2).strip()
            if field not in EDITABLE_FIELDS or not value:
                continue
            try:
                patch[field] = self._normalize_value(field, value)
            except ValueError:
                continue
        return patch

    def _extract_project_name(self, text: str) -> str | None:
        patterns = [
            r"(?:把|将)?项目名称(?:修改|改)(?:为|成)?[：:\s]*[\"“]?(.+?)[\"”]?(?:[。；;，,\n]|$)",
            r"(?:把|将)?项目名(?:修改|改)(?:为|成)?[：:\s]*[\"“]?(.+?)[\"”]?(?:[。；;，,\n]|$)",
        ]
        for pattern in patterns:
            matched = re.search(pattern, text)
            if matched:
                value = matched.group(1).strip()
                if value:
                    return value
        return None

    def _extract_budget_amount(self, text: str) -> float | None:
        matched = re.search(r"(?:预算(?:金额)?)(?:修改|改为|改成|调整为)?[：:\s]*([0-9]+(?:\.[0-9]+)?\s*(?:万)?\s*(?:元|CNY|RMB)?)", text, re.IGNORECASE)
        if not matched:
            return None
        return self._normalize_budget_amount(matched.group(1))

    def _extract_payment_terms(self, text: str) -> str | None:
        matched = re.search(r"(?:付款(?:条款|方式)?)(?:修改|改为|改成|调整为)?[：:\s]*([0-9]{1,3}\s*[/／]\s*[0-9]{1,3}\s*[/／]\s*[0-9]{1,3})", text)
        if not matched:
            return None
        return self._normalize_payment_terms(matched.group(1))

    def _extract_acceptance_standard(self, text: str) -> str | None:
        matched = re.search(r"(?:验收(?:方式|标准)?)(?:修改|改为|改成|调整为)?[：:\s]*([^。；;\n]+)", text)
        if not matched:
            return None
        return self._normalize_acceptance_standard(matched.group(1))

    def _extract_delivery_days(self, text: str) -> int | None:
        matched = re.search(r"(?:交付(?:周期|期限)?|交货(?:周期|期限)?)(?:修改|改为|改成|调整为)?[：:\s]*([0-9]+\s*(?:天|日)?)", text)
        if not matched:
            return None
        return self._normalize_int_value(matched.group(1), units=("天", "日"))

    def _extract_warranty_months(self, text: str) -> int | None:
        matched = re.search(r"(?:质保(?:期|期限)?)(?:修改|改为|改成|调整为)?[：:\s]*([0-9]+\s*(?:个月|月)?)", text)
        if not matched:
            return None
        return self._normalize_int_value(matched.group(1), units=("个月", "月"))

    def extract_patch(self, text: str) -> dict[str, Any]:
        patch = self._extract_inline_assignments(text)

        project_name = self._extract_project_name(text)
        if project_name:
            patch["project_name"] = project_name

        budget_amount = self._extract_budget_amount(text)
        if budget_amount is not None:
            patch["budget_amount"] = budget_amount

        payment_terms = self._extract_payment_terms(text)
        if payment_terms is not None:
            patch["payment_terms"] = payment_terms

        acceptance_standard = self._extract_acceptance_standard(text)
        if acceptance_standard is not None:
            patch["acceptance_standard"] = acceptance_standard

        delivery_days = self._extract_delivery_days(text)
        if delivery_days is not None:
            patch["delivery_days"] = delivery_days

        warranty_months = self._extract_warranty_months(text)
        if warranty_months is not None:
            patch["warranty_months"] = warranty_months

        return patch

    def apply_edits(self, *, text: str, structured_data: dict[str, Any]) -> DocumentEditResult:
        patch = self.extract_patch(text)
        if not patch:
            return DocumentEditResult(structured_data=dict(structured_data), updated_fields=[])
        merged = {**structured_data, **patch}
        return DocumentEditResult(
            structured_data=merged,
            updated_fields=sorted(patch.keys()),
        )
