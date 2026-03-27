from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.project_service import ProjectService


@dataclass(slots=True)
class EvaluationService:
    """Run offline evaluation suites for MVP pipeline quality."""

    project_service: ProjectService
    cases_path: Path
    report_path: Path

    def _load_cases(self) -> dict[str, list[str]]:
        with self.cases_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return {
            str(category): [str(item) for item in items]
            for category, items in payload.items()
            if isinstance(items, list)
        }

    @staticmethod
    def _evaluate_expectation(
        *,
        category: str,
        missing_fields: list[str],
        risk_summary: list[dict[str, Any]],
        can_export_formal: bool,
    ) -> tuple[bool, str]:
        risk_count = len(risk_summary)
        high_risk_count = sum(1 for item in risk_summary if item.get("severity") == "high")

        if category == "normal_cases":
            passed = not missing_fields and can_export_formal
            return passed, "expect no missing fields and allow formal export"
        if category == "missing_field_cases":
            passed = bool(missing_fields)
            return passed, "expect at least one missing field"
        if category == "high_risk_cases":
            passed = high_risk_count > 0 or not can_export_formal
            return passed, "expect high risk detection or blocked formal export"
        if category == "clause_conflict_cases":
            passed = risk_count > 0 or not can_export_formal
            return passed, "expect validation to surface clause or rule conflicts"
        if category == "abnormal_cases":
            passed = bool(missing_fields) or risk_count > 0 or not can_export_formal
            return passed, "expect abnormal input to avoid clean formal-export path"
        return False, "unknown evaluation category"

    def _run_single_case(self, *, category: str, case_text: str, index: int) -> dict[str, Any]:
        project = self.project_service.create_project(
            project_name=f"Eval {category} #{index + 1}",
            department="eval",
            created_by="eval",
        )
        effective_input = case_text if case_text.strip() else " "
        structured = self.project_service.extract(
            project_id=project.project_id,
            raw_input_text=effective_input,
            operator_id="eval",
        )
        validation = self.project_service.validate(
            project_id=project.project_id,
            selected_clause_ids=[],
            operator_id="eval",
        )
        passed, expectation = self._evaluate_expectation(
            category=category,
            missing_fields=structured.get("missing_fields", []),
            risk_summary=[item.model_dump(mode="json") for item in validation.risk_summary],
            can_export_formal=validation.can_export_formal,
        )
        return {
            "case_id": f"{category}_{index + 1}",
            "category": category,
            "input_text": case_text,
            "missing_fields": structured.get("missing_fields", []),
            "risk_count": len(validation.risk_summary),
            "high_risk_count": sum(1 for item in validation.risk_summary if item.severity.value == "high"),
            "can_export_formal": validation.can_export_formal,
            "passed": passed,
            "expectation": expectation,
        }

    def run(self, *, mode: str = "quick") -> dict[str, Any]:
        cases_by_category = self._load_cases()
        category_reports: list[dict[str, Any]] = []
        all_results: list[dict[str, Any]] = []
        max_cases_per_category = 2 if mode == "quick" else None

        for category, cases in cases_by_category.items():
            selected_cases = cases[:max_cases_per_category] if max_cases_per_category else cases
            results = [
                self._run_single_case(category=category, case_text=case_text, index=index)
                for index, case_text in enumerate(selected_cases)
            ]
            passed = sum(1 for item in results if item["passed"])
            category_reports.append(
                {
                    "category": category,
                    "total_cases": len(results),
                    "passed_cases": passed,
                    "pass_rate": round(passed / len(results), 4) if results else 0.0,
                    "cases": results,
                }
            )
            all_results.extend(results)

        total_cases = len(all_results)
        passed_cases = sum(1 for item in all_results if item["passed"])
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "pass_rate": round(passed_cases / total_cases, 4) if total_cases else 0.0,
            "categories": category_reports,
        }

        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        with self.report_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        return report

    def load_latest(self) -> dict[str, Any] | None:
        if not self.report_path.exists():
            return None
        with self.report_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
