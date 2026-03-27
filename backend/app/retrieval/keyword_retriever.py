from __future__ import annotations

import re

from app.retrieval.types import KnowledgeDocument, RetrievalHit


class KeywordRetriever:
    def __init__(self, documents: list[KnowledgeDocument]):
        self.documents = documents

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        ascii_tokens = {
            token.lower()
            for token in re.findall(r"[A-Za-z0-9_]+", text or "")
            if len(token) >= 2
        }
        han_tokens = {
            token for token in re.findall(r"[\u4e00-\u9fff]{2,}", text or "")
        }
        return ascii_tokens | han_tokens

    def search(self, query: str, *, top_k: int = 3) -> list[RetrievalHit]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        hits: list[RetrievalHit] = []
        for document in self.documents:
            doc_tokens = self._tokenize(
                " ".join(
                    [
                        document.title,
                        document.content,
                        " ".join(document.metadata.values()),
                    ]
                )
            )
            if not doc_tokens:
                continue
            overlap = query_tokens & doc_tokens
            if not overlap:
                continue
            score = len(overlap) / len(query_tokens)
            hits.append(RetrievalHit(document=document, score=score))

        return sorted(hits, key=lambda item: item.score, reverse=True)[:top_k]
