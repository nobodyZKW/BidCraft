from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.agent.prompts import (
    CLARIFICATION_PROMPT_TEMPLATE,
    CONFIRM_EXPORT_PROMPT_TEMPLATE,
    DEFAULT_RESPONSE_TEMPLATE,
    FIX_PLAN_PROMPT_TEMPLATE,
)
from app.agent.state import AgentGraphState
from app.agent.types import (
    AgentMessage,
    AutoRepairWithPeToolInput,
    BuildUserOptionsToolInput,
    CheckFormalExportEligibilityToolInput,
    CheckMissingFieldsToolInput,
    ClarificationReviewToolInput,
    CreateProjectToolInput,
    ExportDocumentToolInput,
    ExtractRequirementsToolInput,
    FormalExportEligibilityResult,
    HumanConfirmationToolResult,
    ListClauseAlternativesToolInput,
    MatchClausesToolInput,
    MergeClarificationsToolInput,
    OverrideClauseSelectionToolInput,
    ProjectRefToolInput,
    RenderPreviewToolInput,
    RequestHumanConfirmationToolInput,
    SuggestFixPlanToolInput,
    ValidateDocumentToolInput,
    ValidationToolResult,
)
from app.rules.export_guard import FormalExportGuard
from app.services.clause_service import ClauseService
from app.services.agent_decision_service import AgentDecisionService
from app.services.clarification_review_service import ClarificationReviewService
from app.services.export_service import ExportService
from app.services.extraction_service import ExtractionService
from app.services.project_service import ProjectService
from app.services.risk_repair_service import RiskRepairService
from app.tools.clarification_tools import (
    build_user_options_tool,
    review_clarification_tool,
    request_human_confirmation_tool,
)
from app.tools.clause_tools import (
    list_clause_alternatives_tool,
    match_clauses_tool,
    override_clause_selection_tool,
)
from app.tools.exceptions import ToolBusinessError
from app.tools.export_tools import export_document_tool
from app.tools.extraction_tools import (
    check_missing_fields_tool,
    extract_requirements_tool,
    merge_clarifications_tool,
)
from app.tools.project_tools import (
    create_project_tool,
    get_latest_document_tool,
    get_latest_snapshot_tool,
    get_project_tool,
)
from app.tools.render_tools import render_preview_tool
from app.tools.validation_tools import (
    auto_repair_with_pe_tool,
    check_formal_export_eligibility_tool,
    suggest_fix_plan_tool,
    validate_document_tool,
)


CONTROL_CLARIFICATION_KEYS = {
    "allow_draft",
    "confirmed_export",
    "override_clause_id",
    "auto_repair_with_pe",
}


@dataclass(slots=True)
class AgentNodeDependencies:
    """Dependencies required by graph nodes."""

    project_service: ProjectService
    extraction_service: ExtractionService
    clarification_review_service: ClarificationReviewService
    clause_service: ClauseService
    export_service: ExportService
    export_guard: FormalExportGuard
    risk_repair_service: RiskRepairService
    agent_decision_service: AgentDecisionService


def _messages_from_state(state: AgentGraphState) -> list[AgentMessage]:
    messages = state.get("messages", [])
    normalized: list[AgentMessage] = []
    for message in messages:
        if isinstance(message, AgentMessage):
            normalized.append(message)
        else:
            normalized.append(AgentMessage.model_validate(message))
    return normalized


def _append_message(
    state: AgentGraphState,
    *,
    role: str,
    content: str,
) -> list[AgentMessage]:
    messages = _messages_from_state(state)
    messages.append(AgentMessage(role=role, content=content))
    return messages


def _append_trace(state: AgentGraphState, marker: str) -> list[str]:
    return [*state.get("trace", []), marker]


def _append_tool_call(state: AgentGraphState, tool_name: str) -> list[str]:
    return [*state.get("tool_calls", []), tool_name]


def _extract_text_for_intent(state: AgentGraphState) -> str:
    if state.get("raw_input_text"):
        return state["raw_input_text"]
    for message in reversed(_messages_from_state(state)):
        if message.role == "user":
            return message.content
    return ""


def _infer_intent(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["missing", "缺失", "缺字段"]):
        return "view_missing_fields"
    if (
        ("payment" in lowered or "付款" in text)
        and any(token in lowered for token in ["replace", "override", "替换", "更换"])
    ):
        return "override_payment_clause"
    if "formal" in lowered or "正式" in text:
        return "formal_export"
    if "draft" in lowered or "草稿" in text:
        return "draft_export"
    return "generate_document"


def _default_project_name(state: AgentGraphState) -> str:
    base = state.get("raw_input_text", "").strip()
    if base:
        first_line = base.splitlines()[0][:24].strip()
        if first_line:
            return f"Agent_{first_line}"
    session_id = state.get("session_id", "session")
    return f"Agent_{session_id}"


def _tool_failure(
    state: AgentGraphState,
    *,
    marker: str,
    exc: Exception,
) -> AgentGraphState:
    detail = str(exc)
    return AgentGraphState(
        error=detail,
        current_step=marker,
        next_action="respond",
        pending_human_confirmation=False,
        trace=_append_trace(state, f"{marker}.error"),
        messages=_append_message(state, role="assistant", content=f"Execution failed: {detail}"),
        tool_calls=_append_tool_call(state, f"{marker}.error"),
    )


def _control_allow_draft(state: AgentGraphState) -> bool:
    return bool(state.get("user_clarifications", {}).get("allow_draft"))


def _control_confirmed_export(state: AgentGraphState) -> bool | None:
    value = state.get("user_clarifications", {}).get("confirmed_export")
    if value is None:
        return None
    return bool(value)


def _control_auto_repair_with_pe(state: AgentGraphState) -> bool:
    return bool(state.get("user_clarifications", {}).get("auto_repair_with_pe"))


def understand_intent(
    state: AgentGraphState,
    deps: AgentNodeDependencies,
) -> AgentGraphState:
    """Determine user intent from the request text."""

    text = _extract_text_for_intent(state)
    decision = deps.agent_decision_service.decide_intent(text=text)
    trace_marker = "node.understand_intent.llm" if decision.used_llm else "node.understand_intent"
    tool_calls = state.get("tool_calls", [])
    if decision.used_llm:
        tool_calls = _append_tool_call(state, "agent_llm.decide_intent")
    return AgentGraphState(
        user_intent=decision.intent,
        error=None,
        current_step="understand_intent",
        next_action="ensure_project",
        messages=_append_message(state, role="user", content=text or "continue"),
        trace=_append_trace(state, trace_marker),
        tool_calls=tool_calls,
    )


def ensure_project(
    state: AgentGraphState,
    deps: AgentNodeDependencies,
) -> AgentGraphState:
    """Ensure project exists and hydrate latest structured snapshot when available."""

    try:
        project_id = state.get("project_id")
        if not project_id:
            project_result = create_project_tool(
                CreateProjectToolInput(
                    session_id=state.get("session_id"),
                    project_name=_default_project_name(state),
                    department="agent",
                    created_by="agent",
                    operator_id="agent",
                ),
                project_service=deps.project_service,
            )
            project_id = project_result.project.project_id if project_result.project else None
        else:
            get_project_tool(
                ProjectRefToolInput(
                    session_id=state.get("session_id"),
                    project_id=project_id,
                    operator_id="agent",
                ),
                project_service=deps.project_service,
            )

        next_action = "decide_need_clarification"
        structured_data = state.get("structured_data", {})
        missing_fields = state.get("missing_fields", [])
        clarification_questions = state.get("clarification_questions", [])
        if not structured_data and project_id:
            try:
                snapshot_result = get_latest_snapshot_tool(
                    ProjectRefToolInput(
                        session_id=state.get("session_id"),
                        project_id=project_id,
                        operator_id="agent",
                    ),
                    project_service=deps.project_service,
                )
                structured_data = snapshot_result.structured_data
                missing_fields = snapshot_result.missing_fields
                clarification_questions = (
                    structured_data.get("clarification_questions", [])
                    if structured_data
                    else []
                )
            except ToolBusinessError:
                if state.get("raw_input_text"):
                    next_action = "extract_requirements"
                else:
                    next_action = "respond"

        return AgentGraphState(
            project_id=project_id,
            structured_data=structured_data,
            missing_fields=missing_fields,
            clarification_questions=clarification_questions,
            current_step="ensure_project",
            next_action=next_action,
            trace=_append_trace(state, "node.ensure_project"),
            tool_calls=_append_tool_call(state, "project_tools.ensure_project"),
        )
    except Exception as exc:
        return _tool_failure(state, marker="ensure_project", exc=exc)


def extract_requirements(
    state: AgentGraphState,
    deps: AgentNodeDependencies,
) -> AgentGraphState:
    """Extract structured requirements from raw input text."""

    try:
        extraction_result = extract_requirements_tool(
            tool_input=ExtractRequirementsToolInput(
                session_id=state.get("session_id"),
                project_id=state.get("project_id"),
                operator_id="agent",
                raw_input_text=state.get("raw_input_text", ""),
            ),
            extraction_service=deps.extraction_service,
        )
        checked = check_missing_fields_tool(
            CheckMissingFieldsToolInput(
                session_id=state.get("session_id"),
                project_id=state.get("project_id"),
                operator_id="agent",
                structured_data=extraction_result.structured_data,
            )
        )
        return AgentGraphState(
            structured_data=checked.structured_data,
            missing_fields=checked.missing_fields,
            clarification_questions=checked.clarification_questions,
            current_step="extract_requirements",
            next_action="decide_need_clarification",
            trace=_append_trace(state, "node.extract_requirements"),
            tool_calls=_append_tool_call(state, "extraction_tools.extract_requirements"),
        )
    except Exception as exc:
        return _tool_failure(state, marker="extract_requirements", exc=exc)


def decide_need_clarification(
    state: AgentGraphState,
    deps: AgentNodeDependencies,
) -> AgentGraphState:
    """Route to ask/merge clarification or continue downstream."""

    decision = deps.agent_decision_service.decide_clarification(
        intent=state.get("user_intent", "generate_document"),
        missing_fields=state.get("missing_fields", []),
        clarification_questions=state.get("clarification_questions", []),
        user_clarifications=state.get("user_clarifications", {}),
    )
    trace_marker = (
        "node.decide_need_clarification.llm"
        if decision.used_llm
        else "node.decide_need_clarification"
    )
    tool_calls = state.get("tool_calls", [])
    if decision.used_llm:
        tool_calls = _append_tool_call(state, "agent_llm.decide_clarification")
    return AgentGraphState(
        current_step="decide_need_clarification",
        next_action=decision.next_action,
        trace=_append_trace(state, trace_marker),
        tool_calls=tool_calls,
    )


def ask_for_clarification(state: AgentGraphState) -> AgentGraphState:
    """Pause flow and request human clarification."""

    try:
        options_result = build_user_options_tool(
            BuildUserOptionsToolInput(
                session_id=state.get("session_id"),
                project_id=state.get("project_id"),
                operator_id="agent",
                missing_fields=state.get("missing_fields", []),
                clarification_questions=state.get("clarification_questions", []),
            )
        )
        confirmation: HumanConfirmationToolResult = request_human_confirmation_tool(
            RequestHumanConfirmationToolInput(
                session_id=state.get("session_id"),
                project_id=state.get("project_id"),
                operator_id="agent",
                action="ask_for_clarification",
                message=CLARIFICATION_PROMPT_TEMPLATE,
                options=options_result.options,
            )
        )
        return AgentGraphState(
            pending_human_confirmation=confirmation.pending_human_confirmation,
            options=options_result.options,
            current_step="ask_for_clarification",
            next_action="respond",
            trace=_append_trace(state, "node.ask_for_clarification"),
            messages=_append_message(state, role="assistant", content=confirmation.prompt),
            tool_calls=_append_tool_call(state, "clarification_tools.ask_for_clarification"),
        )
    except Exception as exc:
        return _tool_failure(state, marker="ask_for_clarification", exc=exc)


def merge_clarifications(
    state: AgentGraphState,
    deps: AgentNodeDependencies,
) -> AgentGraphState:
    """Merge user-supplied clarification values into structured payload."""

    try:
        control_payload = {
            key: value
            for key, value in state.get("user_clarifications", {}).items()
            if key in CONTROL_CLARIFICATION_KEYS
        }
        payload = {
            key: value
            for key, value in state.get("user_clarifications", {}).items()
            if key not in CONTROL_CLARIFICATION_KEYS
        }
        review_result = review_clarification_tool(
            ClarificationReviewToolInput(
                session_id=state.get("session_id"),
                project_id=state.get("project_id"),
                operator_id="agent",
                messages=_messages_from_state(state),
                raw_input_text=state.get("raw_input_text", ""),
                structured_data=state.get("structured_data", {}),
                missing_fields=state.get("missing_fields", []),
                clarification_questions=state.get("clarification_questions", []),
                user_clarifications=payload,
            ),
            review_service=deps.clarification_review_service,
        )
        if not review_result.accepted:
            merged_structured_data = {
                **state.get("structured_data", {}),
                **review_result.normalized_clarifications,
            }
            remaining_missing_fields = [
                field
                for field in state.get("missing_fields", [])
                if field not in review_result.normalized_clarifications
            ]
            follow_up_by_field: dict[str, str] = {}
            for item in review_result.follow_up_questions:
                field = ""
                question = ""
                if isinstance(item, dict):
                    field = str(item.get("field", "")).strip()
                    question = str(item.get("question", "")).strip()
                elif isinstance(item, list) and len(item) >= 2:
                    field = str(item[0]).strip()
                    question = str(item[1]).strip()
                if field:
                    follow_up_by_field[field] = question
            next_questions = [
                follow_up_by_field.get(field) or question
                for field, question in zip(
                    remaining_missing_fields,
                    state.get("clarification_questions", []),
                )
            ]
            while len(next_questions) < len(remaining_missing_fields):
                field = remaining_missing_fields[len(next_questions)]
                next_questions.append(
                    follow_up_by_field.get(field)
                    or f"Please clarify field: {field}"
                )
            options_result = build_user_options_tool(
                BuildUserOptionsToolInput(
                    session_id=state.get("session_id"),
                    project_id=state.get("project_id"),
                    operator_id="agent",
                    missing_fields=remaining_missing_fields,
                    clarification_questions=next_questions,
                )
            )
            error_text = "; ".join(review_result.errors) or "Clarification review rejected."
            kept_fields = sorted(review_result.normalized_clarifications.keys())
            kept_text = (
                f" Accepted fields were kept: {', '.join(kept_fields)}."
                if kept_fields
                else ""
            )
            return AgentGraphState(
                structured_data=merged_structured_data,
                missing_fields=remaining_missing_fields,
                clarification_questions=next_questions,
                user_clarifications=control_payload,
                pending_human_confirmation=True,
                options=options_result.options,
                current_step="ask_for_clarification",
                next_action="respond",
                trace=_append_trace(state, "node.merge_clarifications.review_rejected"),
                messages=_append_message(
                    state,
                    role="assistant",
                    content=(
                        "Clarification review failed. Please fix and resubmit. "
                        f"Reason: {error_text}{kept_text}"
                    ),
                ),
                tool_calls=_append_tool_call(
                    state, "clarification_tools.review_clarification.reject"
                ),
            )

        reviewed_payload = {**payload, **review_result.normalized_clarifications}
        merge_result = merge_clarifications_tool(
            MergeClarificationsToolInput(
                session_id=state.get("session_id"),
                project_id=state.get("project_id"),
                operator_id="agent",
                structured_data=state.get("structured_data", {}),
                user_clarifications=reviewed_payload,
            )
        )
        return AgentGraphState(
            structured_data=merge_result.structured_data,
            missing_fields=merge_result.missing_fields,
            clarification_questions=merge_result.clarification_questions,
            user_clarifications=control_payload,
            pending_human_confirmation=False,
            options=[],
            current_step="merge_clarifications",
            next_action="decide_need_clarification",
            trace=_append_trace(state, "node.merge_clarifications"),
            tool_calls=[
                *state.get("tool_calls", []),
                "clarification_tools.review_clarification.accept",
                "extraction_tools.merge_clarifications",
            ],
        )
    except Exception as exc:
        return _tool_failure(state, marker="merge_clarifications", exc=exc)


def match_clauses(
    state: AgentGraphState,
    deps: AgentNodeDependencies,
) -> AgentGraphState:
    """Match clauses or perform payment override then re-match."""

    try:
        structured_data = state.get("structured_data", {})
        selected_clause_ids = state.get("selected_clause_ids", [])
        if state.get("user_intent") == "override_payment_clause":
            override_clause_id = state.get("user_clarifications", {}).get("override_clause_id")
            if not override_clause_id:
                alternatives = list_clause_alternatives_tool(
                    ListClauseAlternativesToolInput(
                        session_id=state.get("session_id"),
                        project_id=state.get("project_id"),
                        operator_id="agent",
                        structured_data=structured_data,
                        clause_type="payment",
                    ),
                    clause_service=deps.clause_service,
                )
                prompt = "Provide override_clause_id for payment terms and continue."
                if alternatives.alternatives:
                    prompt = (
                        "Provide override_clause_id for payment terms and continue. "
                        f"Candidates: {', '.join(alternatives.alternatives)}"
                    )
                return AgentGraphState(
                    pending_human_confirmation=True,
                    options=[{"id": item, "text": item} for item in alternatives.alternatives],
                    current_step="match_clauses",
                    next_action="respond",
                    trace=_append_trace(state, "node.match_clauses.await_override"),
                    messages=_append_message(state, role="assistant", content=prompt),
                    tool_calls=_append_tool_call(state, "clause_tools.list_clause_alternatives"),
                )
            match_result = override_clause_selection_tool(
                OverrideClauseSelectionToolInput(
                    session_id=state.get("session_id"),
                    project_id=state.get("project_id"),
                    operator_id="agent",
                    structured_data=structured_data,
                    selected_clause_ids=selected_clause_ids,
                    override_clause_id=str(override_clause_id),
                ),
                clause_service=deps.clause_service,
            )
        else:
            match_result = match_clauses_tool(
                MatchClausesToolInput(
                    session_id=state.get("session_id"),
                    project_id=state.get("project_id"),
                    operator_id="agent",
                    structured_data=structured_data,
                    selected_clause_ids=selected_clause_ids,
                ),
                clause_service=deps.clause_service,
            )
        return AgentGraphState(
            selected_clause_ids=match_result.selected_clause_ids,
            matched_sections=[item.model_dump(mode="json") for item in match_result.matched_sections],
            pending_human_confirmation=False,
            options=[],
            current_step="match_clauses",
            next_action="validate_document",
            trace=_append_trace(state, "node.match_clauses"),
            tool_calls=_append_tool_call(state, "clause_tools.match_or_override"),
        )
    except Exception as exc:
        return _tool_failure(state, marker="match_clauses", exc=exc)


def validate_document(
    state: AgentGraphState,
    deps: AgentNodeDependencies,
) -> AgentGraphState:
    """Run hard-rule validation and formal-export guard evaluation."""

    try:
        validation_result = validate_document_tool(
            ValidateDocumentToolInput(
                session_id=state.get("session_id"),
                project_id=state.get("project_id"),
                operator_id="agent",
                structured_data=state.get("structured_data", {}),
                selected_clause_ids=state.get("selected_clause_ids", []),
            ),
            clause_service=deps.clause_service,
            template_renderer=deps.project_service.template_renderer,
            rule_engine=deps.project_service.rule_engine,
        )
        eligibility: FormalExportEligibilityResult = check_formal_export_eligibility_tool(
            CheckFormalExportEligibilityToolInput(
                session_id=state.get("session_id"),
                project_id=state.get("project_id"),
                operator_id="agent",
                validation_result=validation_result,
            ),
            guard=deps.export_guard,
        )
        return AgentGraphState(
            validation_result=validation_result.model_dump(mode="json"),
            risk_summary=[item.model_dump(mode="json") for item in validation_result.risk_summary],
            can_export_formal=eligibility.can_export_formal,
            current_step="validate_document",
            next_action="decide_repair_or_continue",
            trace=_append_trace(state, "node.validate_document"),
            tool_calls=_append_tool_call(state, "validation_tools.validate_document"),
        )
    except Exception as exc:
        return _tool_failure(state, marker="validate_document", exc=exc)


def decide_repair_or_continue(
    state: AgentGraphState,
    deps: AgentNodeDependencies,
) -> AgentGraphState:
    """Branch based on risks, intent, and draft downgrade preference."""

    decision = deps.agent_decision_service.decide_repair(
        intent=state.get("user_intent", "generate_document"),
        can_export_formal=bool(state.get("can_export_formal", False)),
        allow_draft=_control_allow_draft(state),
        auto_repair=_control_auto_repair_with_pe(state),
        risk_summary=state.get("risk_summary", []),
    )
    trace_marker = (
        "node.decide_repair_or_continue.llm"
        if decision.used_llm
        else "node.decide_repair_or_continue"
    )
    tool_calls = state.get("tool_calls", [])
    if decision.used_llm:
        tool_calls = _append_tool_call(state, "agent_llm.decide_repair")
    return AgentGraphState(
        current_step="decide_repair_or_continue",
        next_action=decision.next_action,
        trace=_append_trace(state, trace_marker),
        tool_calls=tool_calls,
    )


def auto_repair_with_pe(
    state: AgentGraphState,
    deps: AgentNodeDependencies,
) -> AgentGraphState:
    """Run one-shot PE repair plan and feed patched payload back into matching/validation."""

    try:
        validation_result = ValidationToolResult.model_validate(state.get("validation_result", {}))
        repaired = auto_repair_with_pe_tool(
            AutoRepairWithPeToolInput(
                session_id=state.get("session_id"),
                project_id=state.get("project_id"),
                operator_id="agent",
                raw_input_text=state.get("raw_input_text", ""),
                structured_data=state.get("structured_data", {}),
                selected_clause_ids=state.get("selected_clause_ids", []),
                risk_summary=validation_result.risk_summary,
            ),
            repair_service=deps.risk_repair_service,
            clause_service=deps.clause_service,
        )
        user_clarifications = dict(state.get("user_clarifications", {}))
        user_clarifications["auto_repair_with_pe"] = False
        summary = (
            "PE repair applied via API key once."
            if repaired.used_llm
            else "PE repair fallback applied (no API response)."
        )
        detail = "; ".join(repaired.applied_actions[:3])
        if detail:
            summary = f"{summary} {detail}"
        return AgentGraphState(
            structured_data=repaired.structured_data,
            selected_clause_ids=repaired.selected_clause_ids,
            user_clarifications=user_clarifications,
            pending_human_confirmation=False,
            options=[],
            current_step="auto_repair_with_pe",
            next_action="match_clauses",
            trace=_append_trace(state, "node.auto_repair_with_pe"),
            messages=_append_message(state, role="assistant", content=summary),
            tool_calls=_append_tool_call(state, "validation_tools.auto_repair_with_pe"),
        )
    except Exception as exc:
        return _tool_failure(state, marker="auto_repair_with_pe", exc=exc)


def build_fix_options(state: AgentGraphState) -> AgentGraphState:
    """Build high-risk fix plan and pause for user choice."""

    try:
        validation_result = ValidationToolResult.model_validate(state.get("validation_result", {}))
        plan = suggest_fix_plan_tool(
            SuggestFixPlanToolInput(
                session_id=state.get("session_id"),
                project_id=state.get("project_id"),
                operator_id="agent",
                validation_result=validation_result,
                missing_fields=state.get("missing_fields", []),
            )
        )
        options = [
            {"id": "auto_repair_with_pe", "text": "PE自动修复一次（调用一次API Key）"},
            {"id": "allow_draft", "text": "允许降级草稿继续导出"},
        ]
        options.extend({"id": idx + 1, "text": step} for idx, step in enumerate(plan.fix_steps))
        confirmation = request_human_confirmation_tool(
            RequestHumanConfirmationToolInput(
                session_id=state.get("session_id"),
                project_id=state.get("project_id"),
                operator_id="agent",
                action="choose_fix_plan",
                message=FIX_PLAN_PROMPT_TEMPLATE,
                options=options,
            )
        )
        return AgentGraphState(
            pending_human_confirmation=confirmation.pending_human_confirmation,
            options=options,
            current_step="build_fix_options",
            next_action="respond",
            trace=_append_trace(state, "node.build_fix_options"),
            messages=_append_message(state, role="assistant", content=confirmation.prompt),
            tool_calls=_append_tool_call(state, "validation_tools.build_fix_options"),
        )
    except Exception as exc:
        return _tool_failure(state, marker="build_fix_options", exc=exc)


def render_preview(
    state: AgentGraphState,
    deps: AgentNodeDependencies,
) -> AgentGraphState:
    """Render preview before response or export."""

    try:
        render_result = render_preview_tool(
            RenderPreviewToolInput(
                session_id=state.get("session_id"),
                project_id=state.get("project_id"),
                operator_id="agent",
                structured_data=state.get("structured_data", {}),
                selected_clause_ids=state.get("selected_clause_ids", []),
            ),
            clause_service=deps.clause_service,
            template_renderer=deps.project_service.template_renderer,
        )
        intent = state.get("user_intent", "generate_document")
        if intent == "formal_export":
            next_action = "confirm_export"
        elif intent == "draft_export" or (
            not state.get("can_export_formal", False) and _control_allow_draft(state)
        ):
            next_action = "export_document"
        else:
            next_action = "respond"
        return AgentGraphState(
            rendered_content=render_result.rendered_content,
            preview_html=render_result.preview_html,
            current_step="render_preview",
            next_action=next_action,
            trace=_append_trace(state, "node.render_preview"),
            tool_calls=_append_tool_call(state, "render_tools.render_preview"),
        )
    except Exception as exc:
        return _tool_failure(state, marker="render_preview", exc=exc)


def confirm_export(state: AgentGraphState) -> AgentGraphState:
    """Pause for explicit formal-export confirmation."""

    try:
        confirmed = _control_confirmed_export(state)
        if confirmed is True:
            return AgentGraphState(
                pending_human_confirmation=False,
                options=[],
                current_step="confirm_export",
                next_action="export_document",
                trace=_append_trace(state, "node.confirm_export.accepted"),
                tool_calls=_append_tool_call(state, "clarification_tools.confirm_export.accept"),
            )
        if confirmed is False:
            return AgentGraphState(
                pending_human_confirmation=False,
                options=[],
                current_step="confirm_export",
                next_action="respond",
                trace=_append_trace(state, "node.confirm_export.rejected"),
                messages=_append_message(state, role="assistant", content="Formal export canceled."),
                tool_calls=_append_tool_call(state, "clarification_tools.confirm_export.reject"),
            )
        confirmation = request_human_confirmation_tool(
            RequestHumanConfirmationToolInput(
                session_id=state.get("session_id"),
                project_id=state.get("project_id"),
                operator_id="agent",
                action="confirm_export",
                message=CONFIRM_EXPORT_PROMPT_TEMPLATE,
                options=[
                    {"id": "confirm", "text": "Confirm formal export"},
                    {"id": "cancel", "text": "Cancel export"},
                ],
            )
        )
        return AgentGraphState(
            pending_human_confirmation=confirmation.pending_human_confirmation,
            options=[
                {"id": "confirm", "text": "Confirm formal export"},
                {"id": "cancel", "text": "Cancel export"},
            ],
            current_step="confirm_export",
            next_action="respond",
            trace=_append_trace(state, "node.confirm_export.pending"),
            messages=_append_message(state, role="assistant", content=confirmation.prompt),
            tool_calls=_append_tool_call(state, "clarification_tools.confirm_export.pending"),
        )
    except Exception as exc:
        return _tool_failure(state, marker="confirm_export", exc=exc)


def export_document(
    state: AgentGraphState,
    deps: AgentNodeDependencies,
) -> AgentGraphState:
    """Export with guard-aware mode selection and optional draft downgrade."""

    try:
        project_id = state.get("project_id")
        if not project_id:
            return _tool_failure(
                state,
                marker="export_document",
                exc=ValueError("project_id is required"),
            )
        project = get_project_tool(
            ProjectRefToolInput(
                session_id=state.get("session_id"),
                project_id=project_id,
                operator_id="agent",
            ),
            project_service=deps.project_service,
        ).project
        if project is None:
            return _tool_failure(
                state,
                marker="export_document",
                exc=ValueError("project not found"),
            )

        mode = "draft"
        intent = state.get("user_intent", "")
        if intent == "formal_export" and state.get("can_export_formal", False):
            mode = "formal"
        elif intent == "formal_export" and not state.get("can_export_formal", False):
            if _control_allow_draft(state):
                mode = "draft"
            else:
                return AgentGraphState(
                    current_step="export_document",
                    next_action="build_fix_options",
                    trace=_append_trace(state, "node.export_document.blocked"),
                    tool_calls=_append_tool_call(state, "export_tools.blocked"),
                )
        elif intent == "draft_export":
            mode = "draft"

        version = 1
        try:
            latest_document = get_latest_document_tool(
                ProjectRefToolInput(
                    session_id=state.get("session_id"),
                    project_id=project_id,
                    operator_id="agent",
                ),
                project_service=deps.project_service,
            ).document
            if latest_document is not None:
                version = 2
        except ToolBusinessError:
            version = 1

        export_result = export_document_tool(
            ExportDocumentToolInput(
                session_id=state.get("session_id"),
                project_id=project_id,
                operator_id="agent",
                project_name=project.project_name,
                rendered_content=state.get("rendered_content", ""),
                format="docx",
                mode=mode,
                version=version,
                doc_type="tender",
                can_export_formal=bool(state.get("can_export_formal", False)),
            ),
            export_service=deps.export_service,
        )
        if export_result.blocked and _control_allow_draft(state):
            export_result = export_document_tool(
                ExportDocumentToolInput(
                    session_id=state.get("session_id"),
                    project_id=project_id,
                    operator_id="agent",
                    project_name=project.project_name,
                    rendered_content=state.get("rendered_content", ""),
                    format="docx",
                    mode="draft",
                    version=version,
                    doc_type="tender",
                    can_export_formal=False,
                ),
                export_service=deps.export_service,
            )
        return AgentGraphState(
            file_path=export_result.file_path or "",
            options=[],
            current_step="export_document",
            next_action="respond",
            trace=_append_trace(state, "node.export_document"),
            tool_calls=_append_tool_call(state, "export_tools.export_document"),
        )
    except Exception as exc:
        return _tool_failure(state, marker="export_document", exc=exc)


def respond(state: AgentGraphState) -> AgentGraphState:
    """Build final assistant message for this graph turn."""

    if state.get("error"):
        content = f"Failed: {state['error']}"
    elif state.get("pending_human_confirmation"):
        if _messages_from_state(state):
            content = _messages_from_state(state)[-1].content
        else:
            content = "Paused for your confirmation."
    elif state.get("user_intent") == "view_missing_fields":
        missing_fields = state.get("missing_fields", [])
        content = f"Missing fields: {', '.join(missing_fields) if missing_fields else 'none'}."
    elif state.get("user_intent") == "override_payment_clause":
        content = "Payment clause override finished and validation refreshed."
    elif state.get("file_path"):
        content = f"Export completed: {state['file_path']}"
    elif state.get("preview_html"):
        content = "Preview generated."
    else:
        content = DEFAULT_RESPONSE_TEMPLATE.format(
            current_step=state.get("current_step", "unknown"),
            next_action=state.get("next_action", "respond"),
        )
    return AgentGraphState(
        messages=_append_message(state, role="assistant", content=content),
        current_step="respond",
        next_action="done",
        trace=_append_trace(state, f"node.respond.{datetime.now(timezone.utc).isoformat()}"),
        tool_calls=state.get("tool_calls", []),
    )
