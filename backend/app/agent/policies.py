from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.agent.types import ValidationToolResult
from app.models.domain import RiskSeverity


class FormalExportGuardPolicy(Protocol):
    """Policy interface used to gate formal export."""

    def can_export_formal(self, validation_result: ValidationToolResult) -> bool:
        """Return whether formal export is allowed."""


class HumanConfirmationPolicy(Protocol):
    """Policy interface for user confirmation checkpoints."""

    def requires_confirmation(self, action: str) -> bool:
        """Return whether the next action requires human confirmation."""


class OverridePolicy(Protocol):
    """Policy interface for clause override checks."""

    def can_override(
        self,
        *,
        target_clause_id: str,
        allowed_clause_ids: list[str],
    ) -> bool:
        """Return whether a clause override can be applied."""


@dataclass(slots=True, frozen=True)
class StrictFormalExportGuard:
    """Default guard that blocks formal export on any high-severity risk."""

    def can_export_formal(self, validation_result: ValidationToolResult) -> bool:
        if not validation_result.can_export_formal:
            return False
        return not any(
            risk.severity == RiskSeverity.high for risk in validation_result.risk_summary
        )


@dataclass(slots=True, frozen=True)
class DefaultHumanConfirmationPolicy:
    """Default policy for interruptible high-risk actions."""

    confirm_actions: set[str] = field(
        default_factory=lambda: {"ask_for_clarification", "confirm_export", "choose_fix_plan"}
    )

    def requires_confirmation(self, action: str) -> bool:
        return action in self.confirm_actions


@dataclass(slots=True, frozen=True)
class DefaultOverridePolicy:
    """Default policy allowing only override candidates from curated alternatives."""

    def can_override(
        self,
        *,
        target_clause_id: str,
        allowed_clause_ids: list[str],
    ) -> bool:
        return target_clause_id in set(allowed_clause_ids)

