from __future__ import annotations

from app.models.domain import Clause, MatchedSection
from app.repositories.clause_repository import ClauseRepository
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService


class ClauseService:
    def __init__(
        self,
        clause_repository: ClauseRepository,
        knowledge_retrieval_service: KnowledgeRetrievalService | None = None,
    ):
        self.clause_repository = clause_repository
        self.knowledge_retrieval_service = knowledge_retrieval_service

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
                    alternatives=[
                        item.clause_id
                        for item in alternatives
                        if item.clause_id != clause.clause_id
                    ],
                    reason=(
                        f"匹配 procurement_type={structured_data.get('procurement_type')} "
                        f"+ method={structured_data.get('method')}"
                    ),
                    citations=(
                        self.knowledge_retrieval_service.cite_clause(
                            clause=clause,
                            structured_data=structured_data,
                        )
                        if self.knowledge_retrieval_service is not None
                        else []
                    ),
                )
            )
        return selected, sections

    def list_alternatives(
        self,
        *,
        clause_type: str,
        structured_data: dict,
    ) -> list[Clause]:
        return self.clause_repository.get_alternatives(
            clause_type=clause_type,
            structured_data=structured_data,
        )

    def get_by_ids(self, clause_ids: list[str]) -> list[Clause]:
        return self.clause_repository.get_by_ids(clause_ids)

    def get_by_id(self, clause_id: str) -> Clause | None:
        clauses = self.clause_repository.get_by_ids([clause_id])
        return clauses[0] if clauses else None
