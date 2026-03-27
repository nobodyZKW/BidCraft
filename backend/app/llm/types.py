from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class StructuredLLMRequest:
    task_name: str
    system_prompt: str
    task_prompt: str
    schema: dict[str, Any]
    max_retries: int = 2
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TextLLMRequest:
    task_name: str
    system_prompt: str
    user_prompt: str
    max_retries: int = 2
    metadata: dict[str, Any] = field(default_factory=dict)


class StructuredLLMClient(Protocol):
    def invoke_structured(self, request: StructuredLLMRequest) -> dict[str, Any] | None:
        ...

    def invoke_text(self, request: TextLLMRequest) -> str | None:
        ...
