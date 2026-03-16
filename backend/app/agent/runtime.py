from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.agent.state import AgentGraphState, create_initial_state
from app.agent.types import AgentMessage, AgentResponsePayload
from app.repositories.agent_state_repository import AgentStateRepository


@dataclass(slots=True)
class AgentWorkflowRunner:
    """Runtime wrapper around compiled graph and persisted state."""

    workflow: Any
    state_repository: AgentStateRepository

    @staticmethod
    def _to_serializable_state(state: AgentGraphState) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        for message in state.get("messages", []):
            if isinstance(message, AgentMessage):
                messages.append(message.model_dump(mode="json"))
            elif isinstance(message, dict):
                messages.append(AgentMessage.model_validate(message).model_dump(mode="json"))
        serialized = dict(state)
        serialized["messages"] = messages
        return serialized

    @staticmethod
    def _from_stored_state(payload: dict[str, Any]) -> AgentGraphState:
        return AgentGraphState(**payload)

    @staticmethod
    def _build_response(state: AgentGraphState) -> AgentResponsePayload:
        assistant_message = ""
        messages = state.get("messages", [])
        if messages:
            last = messages[-1]
            if isinstance(last, AgentMessage):
                assistant_message = last.content
            elif isinstance(last, dict):
                assistant_message = str(last.get("content", ""))
        return AgentResponsePayload(
            assistant_message=assistant_message,
            project_id=state.get("project_id"),
            current_step=state.get("current_step", ""),
            next_action=state.get("next_action", ""),
            requires_user_input=bool(state.get("pending_human_confirmation", False)),
            options=state.get("options", []),
            tool_calls=state.get("tool_calls", []),
            artifacts={
                "missing_fields": state.get("missing_fields", []),
                "clarification_questions": state.get("clarification_questions", []),
                "matched_sections": state.get("matched_sections", []),
                "risk_summary": state.get("risk_summary", []),
                "can_export_formal": state.get("can_export_formal", False),
                "preview_html": state.get("preview_html", ""),
                "file_path": state.get("file_path", ""),
                "error": state.get("error"),
            },
        )

    def _run(self, state: AgentGraphState) -> AgentGraphState:
        result = self.workflow.invoke(state)
        return AgentGraphState(**result)

    def run_chat(
        self,
        *,
        message: str,
        session_id: str | None = None,
        project_id: str | None = None,
        user_clarifications: dict[str, Any] | None = None,
    ) -> AgentResponsePayload:
        loaded_state: AgentGraphState | None = None
        if project_id:
            stored = self.state_repository.get_state(project_id)
            if stored:
                loaded_state = self._from_stored_state(stored)

        state = loaded_state or create_initial_state(
            session_id=session_id or uuid4().hex,
            raw_input_text=message,
            project_id=project_id,
        )
        state["raw_input_text"] = message
        if user_clarifications:
            existing = dict(state.get("user_clarifications", {}))
            existing.update(user_clarifications)
            state["user_clarifications"] = existing

        next_state = self._run(state)
        if next_state.get("project_id"):
            self.state_repository.save_state(
                next_state["project_id"],
                self._to_serializable_state(next_state),
            )
        return self._build_response(next_state)

    def continue_project(
        self,
        *,
        project_id: str,
        message: str = "",
        user_clarifications: dict[str, Any] | None = None,
    ) -> AgentResponsePayload:
        stored = self.state_repository.get_state(project_id)
        if not stored:
            raise KeyError(f"Agent state not found for project: {project_id}")
        state = self._from_stored_state(stored)
        state["project_id"] = project_id
        if message:
            state["raw_input_text"] = message
        if user_clarifications:
            existing = dict(state.get("user_clarifications", {}))
            existing.update(user_clarifications)
            state["user_clarifications"] = existing
        next_state = self._run(state)
        self.state_repository.save_state(
            project_id,
            self._to_serializable_state(next_state),
        )
        return self._build_response(next_state)

    def get_project_state(self, project_id: str) -> dict[str, Any]:
        stored = self.state_repository.get_state(project_id)
        if not stored:
            raise KeyError(f"Agent state not found for project: {project_id}")
        return stored

