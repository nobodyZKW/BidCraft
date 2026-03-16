from __future__ import annotations

from dataclasses import dataclass

from app.models.domain import RiskSeverity, ValidationResult


FORMAL_EXPORT_BLOCK_MESSAGE = "存在高风险项，禁止导出正式版。"


@dataclass(slots=True, frozen=True)
class FormalExportGuard:
    """Single source of truth for formal export gate decisions."""

    def can_export_formal(self, validation_result: ValidationResult) -> bool:
        if not validation_result.can_export_formal:
            return False
        return not any(
            risk.severity == RiskSeverity.high for risk in validation_result.risk_summary
        )

    def assert_formal_export_allowed(self, validation_result: ValidationResult) -> None:
        if not self.can_export_formal(validation_result):
            raise ValueError(FORMAL_EXPORT_BLOCK_MESSAGE)
