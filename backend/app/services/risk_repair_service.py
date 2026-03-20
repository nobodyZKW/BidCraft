from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError, validate

from app.core.settings import settings
from app.llm.deepseek_client import DeepSeekClient
from app.models.domain import Clause, RiskItem
from app.schemas.json_schemas import RISK_REPAIR_PLAN_SCHEMA
from app.services.clause_service import ClauseService


@dataclass(slots=True)
class RiskRepairApplyResult:
    structured_data: dict[str, Any]
    selected_clause_ids: list[str]
    applied_actions: list[str]
    used_llm: bool


class RiskRepairService:
    """Generate and apply one-shot PE repair plans for high-risk issues."""

    def __init__(self, llm_client: DeepSeekClient):
        self.llm_client = llm_client

    @staticmethod
    def _parse_budget_from_text(raw_input_text: str) -> float | None:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:万|万元|cny|rmb|元)", raw_input_text, re.IGNORECASE)
        if not match:
            return None
        value = float(match.group(1))
        if "万" in raw_input_text:
            return value * 10000
        return value

    @staticmethod
    def _normalize_payment_terms(payment_terms: str) -> str:
        terms = payment_terms.replace(" ", "")
        match = re.match(r"^(\d{1,3})/(\d{1,3})/(\d{1,3})$", terms)
        if not match:
            return "30/60/10"
        first = min(int(match.group(1)), settings.max_advance_payment_percent)
        third = int(match.group(3))
        second = 100 - first - third
        if second < 0:
            second = 0
            third = 100 - first
        return f"{first}/{second}/{third}"

    def _fallback_plan(
        self,
        *,
        raw_input_text: str,
        structured_data: dict[str, Any],
        risk_summary: list[RiskItem],
    ) -> dict[str, Any]:
        risk_codes = {item.code for item in risk_summary}
        patch: dict[str, Any] = {}
        enforce_clause_types: list[str] = []
        reset_clause_overrides = False
        notes: list[str] = []

        if "MISSING_METHOD" in risk_codes:
            patch["method"] = "public_tender"
            notes.append("Set missing method to public_tender.")
        if "MISSING_PAYMENT_TERMS" in risk_codes:
            patch["payment_terms"] = "30/60/10"
            notes.append("Filled default payment terms 30/60/10.")
        if "ADVANCE_PAYMENT_OVER_LIMIT" in risk_codes:
            patch["payment_terms"] = self._normalize_payment_terms(
                str(structured_data.get("payment_terms", ""))
            )
            notes.append("Reduced advance payment ratio to configured threshold.")
        if "MISSING_ACCEPTANCE_STANDARD" in risk_codes:
            patch["acceptance_standard"] = "按国家标准、技术规格与测试报告联合验收。"
            notes.append("Filled acceptance standard with compliant baseline.")
        if "MISSING_BUDGET" in risk_codes:
            budget = self._parse_budget_from_text(raw_input_text)
            if budget is not None:
                patch["budget_amount"] = budget
                notes.append("Recovered budget_amount from raw text.")
            else:
                notes.append("Unable to infer budget_amount from raw text; requires human input.")
        if "MISSING_LIABILITY" in risk_codes:
            enforce_clause_types.append("liability")
            notes.append("Will force-match liability clause.")
        if "MISSING_DISPUTE" in risk_codes:
            enforce_clause_types.append("dispute")
            notes.append("Will force-match dispute clause.")
        if "CLAUSE_NOT_APPROVED" in risk_codes or "CLAUSE_VERSION_EXPIRED" in risk_codes:
            reset_clause_overrides = True
            notes.append("Will reset manual overrides to latest approved clauses.")

        if not notes:
            notes.append("No deterministic fix generated; keep current state.")

        return {
            "structured_patch": patch,
            "enforce_clause_types": list(dict.fromkeys(enforce_clause_types)),
            "reset_clause_overrides": reset_clause_overrides,
            "notes": notes,
        }

    def build_repair_plan(
        self,
        *,
        raw_input_text: str,
        structured_data: dict[str, Any],
        risk_summary: list[RiskItem],
    ) -> tuple[dict[str, Any], bool]:
        risk_payload = [
            {
                "code": item.code,
                "severity": item.severity.value,
                "message": item.message,
                "location": item.location,
            }
            for item in risk_summary
        ]
        task_prompt = (
            "Generate one repair plan for procurement structured fields and clause enforcement.\n"
            f"Current structured_data: {structured_data}\n"
            f"Risk summary: {risk_payload}\n"
            "Return only fields in schema. Do not invent unsupported procurement methods.\n"
            "For goods + public_tender MVP, prefer compliant defaults and minimal edits.\n"
        )

        llm_plan = self.llm_client.generate_structured_json(
            task_prompt=task_prompt,
            schema=RISK_REPAIR_PLAN_SCHEMA,
            system_prompt=(
                "You are a procurement policy engineer. "
                "Return strict JSON only and focus on reducing high-severity risks."
            ),
        )
        if llm_plan is not None:
            try:
                validate(instance=llm_plan, schema=RISK_REPAIR_PLAN_SCHEMA)
                return llm_plan, True
            except ValidationError:
                pass

        fallback = self._fallback_plan(
            raw_input_text=raw_input_text,
            structured_data=structured_data,
            risk_summary=risk_summary,
        )
        validate(instance=fallback, schema=RISK_REPAIR_PLAN_SCHEMA)
        return fallback, False

    def _pick_clause_id(
        self,
        *,
        clause_service: ClauseService,
        clause_type: str,
        structured_data: dict[str, Any],
    ) -> str | None:
        candidates: list[Clause] = clause_service.list_alternatives(
            clause_type=clause_type,
            structured_data=structured_data,
        )
        if not candidates:
            return None
        return candidates[0].clause_id

    def apply_repair(
        self,
        *,
        raw_input_text: str,
        structured_data: dict[str, Any],
        selected_clause_ids: list[str],
        risk_summary: list[RiskItem],
        clause_service: ClauseService,
    ) -> RiskRepairApplyResult:
        plan, used_llm = self.build_repair_plan(
            raw_input_text=raw_input_text,
            structured_data=structured_data,
            risk_summary=risk_summary,
        )

        merged_structured = dict(structured_data)
        applied_actions: list[str] = []
        patch = plan.get("structured_patch", {})
        for key, value in patch.items():
            if value in ("", None):
                continue
            merged_structured[key] = value
            applied_actions.append(f"updated structured_data.{key}")

        merged_selected = list(selected_clause_ids)
        if bool(plan.get("reset_clause_overrides", False)):
            merged_selected = []
            applied_actions.append("reset selected_clause_ids")

        for clause_type in plan.get("enforce_clause_types", []):
            clause_id = self._pick_clause_id(
                clause_service=clause_service,
                clause_type=clause_type,
                structured_data=merged_structured,
            )
            if clause_id is None:
                applied_actions.append(f"no clause found for type={clause_type}")
                continue
            if clause_id not in merged_selected:
                merged_selected.append(clause_id)
                applied_actions.append(f"enforced clause {clause_type} -> {clause_id}")

        if not applied_actions:
            applied_actions = list(plan.get("notes", [])) or ["no changes applied"]

        return RiskRepairApplyResult(
            structured_data=merged_structured,
            selected_clause_ids=list(dict.fromkeys(merged_selected)),
            applied_actions=applied_actions,
            used_llm=used_llm,
        )
