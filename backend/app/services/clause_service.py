from __future__ import annotations

from app.models.domain import Clause, MatchedSection
from app.repositories.clause_repository import ClauseRepository


class ClauseService:
    def __init__(self, clause_repository: ClauseRepository):
        self.clause_repository = clause_repository

    def _apply_overrides(
        self,
        selected: list[Clause],
        overrides: list[str],
        structured_data: dict,
    ) -> list[Clause]:
        if not overrides:
            return selected

        selected_by_type = {clause.clause_type: clause for clause in selected}
        override_clauses = self.clause_repository.get_by_ids(overrides)
        for clause in override_clauses:
            candidates = self.clause_repository.get_alternatives(
                clause_type=clause.clause_type,
                structured_data=structured_data,
            )
            if any(item.clause_id == clause.clause_id for item in candidates):
                selected_by_type[clause.clause_type] = clause
        return list(selected_by_type.values())

    def match(
        self,
        structured_data: dict,
        selected_clause_ids: list[str] | None = None,
    ) -> tuple[list[Clause], list[MatchedSection]]:
        selected = self.clause_repository.get_latest_applicable(structured_data)
        selected = self._apply_overrides(selected, selected_clause_ids or [], structured_data)

        sections: list[MatchedSection] = []
        for clause in selected:
            alternatives = self.clause_repository.get_alternatives(
                clause_type=clause.clause_type,
                structured_data=structured_data,
            )
            sections.append(
                MatchedSection(
                    section_id=clause.clause_type,
                    selected_clause_id=clause.clause_id,
                    alternatives=[item.clause_id for item in alternatives if item.clause_id != clause.clause_id],
                    reason=f"匹配 procurement_type={structured_data.get('procurement_type')} + method={structured_data.get('method')}",
                )
            )
        return selected, sections
