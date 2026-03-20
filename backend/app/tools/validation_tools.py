from __future__ import annotations

from app.agent.types import (
    AutoRepairWithPeToolInput,
    AutoRepairWithPeToolResult,
    CheckFormalExportEligibilityToolInput,
    ExplainRiskSummaryToolInput,
    FormalExportEligibilityResult,
    RiskSummaryExplanationResult,
    SuggestFixPlanResult,
    SuggestFixPlanToolInput,
    ValidateDocumentToolInput,
    ValidationToolResult,
)
from app.models.domain import RiskSeverity
from app.renderers.template_renderer import TemplateRenderer
from app.rules.export_guard import FormalExportGuard
from app.rules.rule_engine import RuleEngine
from app.services.clause_service import ClauseService
from app.services.risk_repair_service import RiskRepairService
from app.tools.exceptions import raise_tool_error


def validate_document_tool(
    tool_input: ValidateDocumentToolInput,
    clause_service: ClauseService,
    template_renderer: TemplateRenderer,
    rule_engine: RuleEngine,
) -> ValidationToolResult:
    """Validate generated content with hard-coded rule engine risk checks."""

    try:
        selected_clauses, _ = clause_service.match(
            structured_data=tool_input.structured_data,
            selected_clause_ids=tool_input.selected_clause_ids,
        )

        rendered_content = tool_input.rendered_content
        unresolved_placeholders = tool_input.unresolved_placeholders
        if rendered_content is None:
            rendered_content, _, unresolved_placeholders, _ = template_renderer.render(
                structured_data=tool_input.structured_data,
                selected_clauses=selected_clauses,
            )

        validation = rule_engine.evaluate(
            structured_data=tool_input.structured_data,
            selected_clauses=selected_clauses,
            rendered_content=rendered_content,
            unresolved_placeholders=unresolved_placeholders,
        )
        high_risk_codes = [
            risk.code for risk in validation.risk_summary if risk.severity == RiskSeverity.high
        ]
        return ValidationToolResult(
            risk_summary=validation.risk_summary,
            can_export_formal=validation.can_export_formal,
            high_risk_codes=high_risk_codes,
            message="document validated",
            trace=["validation.validate_document"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="validate_document_tool")
        raise


def explain_risk_summary_tool(
    tool_input: ExplainRiskSummaryToolInput,
) -> RiskSummaryExplanationResult:
    """Summarize risk items into grouped severity buckets and plain-language text."""

    try:
        high = [risk.code for risk in tool_input.risk_summary if risk.severity == RiskSeverity.high]
        medium = [
            risk.code for risk in tool_input.risk_summary if risk.severity == RiskSeverity.medium
        ]
        low = [risk.code for risk in tool_input.risk_summary if risk.severity == RiskSeverity.low]
        summary_text = (
            f"high={len(high)}, medium={len(medium)}, low={len(low)}; "
            f"blocking={'yes' if len(high) > 0 else 'no'}"
        )
        return RiskSummaryExplanationResult(
            summary_text=summary_text,
            high_risk_codes=high,
            medium_risk_codes=medium,
            low_risk_codes=low,
            message="risk summary explained",
            trace=["validation.explain_risk_summary"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="explain_risk_summary_tool")
        raise


def suggest_fix_plan_tool(
    tool_input: SuggestFixPlanToolInput,
) -> SuggestFixPlanResult:
    """Suggest deterministic fix steps from blocking risk codes and missing fields."""

    try:
        blocking = list(tool_input.validation_result.high_risk_codes)
        fix_steps: list[str] = []
        if tool_input.missing_fields:
            fix_steps.append(f"补齐缺失字段: {', '.join(tool_input.missing_fields)}")
        for code in blocking:
            if code == "MISSING_PAYMENT_TERMS":
                fix_steps.append("补充付款条款并控制预付款比例")
            elif code == "ADVANCE_PAYMENT_OVER_LIMIT":
                fix_steps.append("将预付款比例调整到红线以内")
            elif code == "MISSING_ACCEPTANCE_STANDARD":
                fix_steps.append("补充明确的验收标准条款")
            elif code == "MISSING_LIABILITY":
                fix_steps.append("选择或补充违约责任条款")
            elif code == "MISSING_DISPUTE":
                fix_steps.append("选择或补充争议解决条款")
            else:
                fix_steps.append(f"处理风险项: {code}")

        if not fix_steps:
            fix_steps.append("无需修复，可继续下一步")

        return SuggestFixPlanResult(
            blocking_issues=blocking,
            fix_steps=fix_steps,
            can_downgrade_to_draft=len(blocking) > 0,
            message="fix plan suggested",
            trace=["validation.suggest_fix_plan"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="suggest_fix_plan_tool")
        raise


def check_formal_export_eligibility_tool(
    tool_input: CheckFormalExportEligibilityToolInput,
    guard: FormalExportGuard | None = None,
) -> FormalExportEligibilityResult:
    """Evaluate formal-export eligibility with guard policy instead of LLM judgement."""

    export_guard = guard or FormalExportGuard()
    try:
        can_export_formal = export_guard.can_export_formal(
            validation_result=tool_input.validation_result.to_validation_result()
        )
        reason = "eligible"
        if not can_export_formal:
            reason = "blocked_by_high_severity_risk"
        return FormalExportEligibilityResult(
            can_export_formal=can_export_formal,
            reason=reason,
            message="formal export eligibility checked",
            trace=["validation.check_formal_export_eligibility"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="check_formal_export_eligibility_tool")
        raise


def auto_repair_with_pe_tool(
    tool_input: AutoRepairWithPeToolInput,
    *,
    repair_service: RiskRepairService,
    clause_service: ClauseService,
) -> AutoRepairWithPeToolResult:
    """Apply a one-shot PE repair plan (single API call + deterministic fallback)."""

    try:
        applied = repair_service.apply_repair(
            raw_input_text=tool_input.raw_input_text,
            structured_data=tool_input.structured_data,
            selected_clause_ids=tool_input.selected_clause_ids,
            risk_summary=tool_input.risk_summary,
            clause_service=clause_service,
        )
        return AutoRepairWithPeToolResult(
            structured_data=applied.structured_data,
            selected_clause_ids=applied.selected_clause_ids,
            applied_actions=applied.applied_actions,
            used_llm=applied.used_llm,
            message="pe repair applied",
            trace=["validation.auto_repair_with_pe"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="auto_repair_with_pe_tool")
        raise
