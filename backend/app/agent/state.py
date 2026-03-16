from __future__ import annotations

from typing import Any, TypedDict

from app.agent.types import AgentMessage


class AgentGraphState(TypedDict, total=False):
    """State object shared across graph nodes."""

    session_id: str
    project_id: str | None
    messages: list[AgentMessage]
    user_intent: str
    raw_input_text: str
    structured_data: dict[str, Any]
    missing_fields: list[str]
    clarification_questions: list[str]
    user_clarifications: dict[str, Any]
    selected_clause_ids: list[str]
    matched_sections: list[dict[str, Any]]
    validation_result: dict[str, Any]
    risk_summary: list[dict[str, Any]]
    can_export_formal: bool
    preview_html: str
    rendered_content: str
    file_path: str
    pending_human_confirmation: bool
    options: list[dict[str, Any]]
    tool_calls: list[str]
    current_step: str
    next_action: str
    error: str | None
    trace: list[str]


def create_initial_state(
    *,
    session_id: str,
    raw_input_text: str = "",
    project_id: str | None = None,
) -> AgentGraphState:
    """Create a fully initialized graph state with safe defaults."""

    return AgentGraphState(
        session_id=session_id,
        project_id=project_id,
        messages=[],
        user_intent="",
        raw_input_text=raw_input_text,
        structured_data={},
        missing_fields=[],
        clarification_questions=[],
        user_clarifications={},
        selected_clause_ids=[],
        matched_sections=[],
        validation_result={},
        risk_summary=[],
        can_export_formal=False,
        preview_html="",
        rendered_content="",
        file_path="",
        pending_human_confirmation=False,
        options=[],
        tool_calls=[],
        current_step="init",
        next_action="understand_intent",
        error=None,
        trace=[],
    )
