from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    source_id: str
    title: str
    content: str
    source_type: Literal["clause", "rule"]
    metadata: dict[str, str]


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    document: KnowledgeDocument
    score: float
