from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolBusinessError(Exception):
    """Base business exception for all tool-layer failures."""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class ToolNotFoundError(ToolBusinessError):
    """Raised when required entities are missing."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(code="tool_not_found", message=message, details=details or {})


class ToolInputError(ToolBusinessError):
    """Raised when tool input is invalid."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(code="tool_input_error", message=message, details=details or {})


class ToolExecutionError(ToolBusinessError):
    """Raised when unexpected runtime errors happen inside tool execution."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(code="tool_execution_error", message=message, details=details or {})


def raise_tool_error(exc: Exception, *, context: str) -> None:
    """Normalize arbitrary exceptions into unified tool business errors."""

    if isinstance(exc, ToolBusinessError):
        raise exc
    if isinstance(exc, KeyError):
        raise ToolNotFoundError(str(exc), {"context": context}) from exc
    if isinstance(exc, ValueError):
        raise ToolInputError(str(exc), {"context": context}) from exc
    raise ToolExecutionError(str(exc), {"context": context}) from exc

