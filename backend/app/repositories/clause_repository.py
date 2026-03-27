from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from app.core.settings import settings
from app.models.domain import Clause


class ClauseRepository:
    def __init__(self, clause_file: Path):
        self.clause_file = clause_file

    def _load_all(self) -> list[Clause]:
        if not self.clause_file.exists():
            return []
        payload = json.loads(self.clause_file.read_text(encoding="utf-8"))
        return [Clause.model_validate(item) for item in payload]

    def load_all(self) -> list[Clause]:
        return self._load_all()

    @staticmethod
    def _version_rank(version: str) -> tuple[int, ...]:
        nums = re.findall(r"\d+", version or "")
        if not nums:
            return (0,)
        return tuple(int(x) for x in nums)

    @staticmethod
    def _advance_payment_percent(payment_terms: str) -> int:
        terms = payment_terms.replace(" ", "")
        match = re.match(r"^(\d{1,3})/", terms)
        if not match:
            return 0
        return int(match.group(1))

    def _is_forbidden(self, clause: Clause, structured_data: dict) -> bool:
        payment_terms = str(structured_data.get("payment_terms", ""))
        for condition in clause.forbidden_conditions:
            if condition == "advance_payment_over_50":
                if (
                    self._advance_payment_percent(payment_terms)
                    > settings.max_advance_payment_percent
                ):
                    return True
        return False

    def get_by_ids(self, clause_ids: list[str]) -> list[Clause]:
        id_set = set(clause_ids)
        return [item for item in self._load_all() if item.clause_id in id_set]

    def get_latest_applicable(self, structured_data: dict) -> list[Clause]:
        procurement_type = structured_data.get("procurement_type")
        method = structured_data.get("method")
        today = date.today()

        candidates = [
            clause
            for clause in self._load_all()
            if procurement_type in clause.applicable_procurement_types
            and method in clause.applicable_methods
            and clause.status == "approved"
            and clause.effective_date <= today
            and (clause.expiry_date is None or clause.expiry_date >= today)
            and not self._is_forbidden(clause, structured_data)
        ]

        grouped: dict[str, list[Clause]] = {}
        for clause in candidates:
            if any(not structured_data.get(field) for field in clause.required_fields):
                continue
            grouped.setdefault(clause.clause_type, []).append(clause)

        selected: list[Clause] = []
        for clause_type, clauses in grouped.items():
            sorted_group = sorted(
                clauses,
                key=lambda item: (self._version_rank(item.version), item.effective_date),
                reverse=True,
            )
            selected.append(sorted_group[0])

        return selected

    def get_alternatives(self, clause_type: str, structured_data: dict) -> list[Clause]:
        procurement_type = structured_data.get("procurement_type")
        method = structured_data.get("method")
        today = date.today()
        candidates = [
            clause
            for clause in self._load_all()
            if clause.clause_type == clause_type
            and procurement_type in clause.applicable_procurement_types
            and method in clause.applicable_methods
            and clause.status == "approved"
            and clause.effective_date <= today
            and (clause.expiry_date is None or clause.expiry_date >= today)
            and not self._is_forbidden(clause, structured_data)
        ]
        return sorted(
            candidates,
            key=lambda item: (self._version_rank(item.version), item.effective_date),
            reverse=True,
        )
