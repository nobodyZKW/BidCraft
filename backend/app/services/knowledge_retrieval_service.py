from __future__ import annotations

from app.models.domain import Clause, KnowledgeCitation, RiskItem
from app.retrieval.keyword_retriever import KeywordRetriever
from app.retrieval.types import KnowledgeDocument


class KnowledgeRetrievalService:
    def __init__(self, documents: list[KnowledgeDocument]):
        self.retriever = KeywordRetriever(documents)

    @staticmethod
    def _to_citations(documents: list[KnowledgeDocument]) -> list[KnowledgeCitation]:
        citations: list[KnowledgeCitation] = []
        for document in documents:
            citations.append(
                KnowledgeCitation(
                    source_id=document.source_id,
                    title=document.title,
                    excerpt=document.content[:180],
                )
            )
        return citations

    def cite_clause(
        self,
        *,
        clause: Clause,
        structured_data: dict,
        top_k: int = 2,
    ) -> list[KnowledgeCitation]:
        query = " ".join(
            [
                clause.clause_type,
                clause.clause_name,
                str(structured_data.get("procurement_type", "")),
                str(structured_data.get("method", "")),
                " ".join(clause.required_fields),
            ]
        )
        hits = self.retriever.search(query, top_k=top_k)
        clause_hits = [
            item.document
            for item in hits
            if item.document.source_type == "clause"
            and (
                item.document.metadata.get("clause_id") == clause.clause_id
                or item.document.metadata.get("clause_type") == clause.clause_type
            )
        ]
        return self._to_citations(clause_hits)

    def cite_risk(self, risk: RiskItem, *, top_k: int = 2) -> list[KnowledgeCitation]:
        query = f"{risk.code} {risk.message} {risk.location}"
        hits = self.retriever.search(query, top_k=top_k)
        rule_hits = [item.document for item in hits if item.document.source_type == "rule"]
        return self._to_citations(rule_hits)
