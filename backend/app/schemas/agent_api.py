from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, description="User message to start or continue chat flow")
    session_id: str | None = Field(default=None, description="Optional chat session id")
    project_id: str | None = Field(default=None, description="Optional existing project id")
    user_clarifications: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured clarification values",
    )


class AgentContinueRequest(BaseModel):
    message: str = Field(default="", description="Optional follow-up user text")
    user_clarifications: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured clarification/confirmation payload",
    )


class AgentChatResponse(BaseModel):
    assistant_message: str = ""
    project_id: str | None = None
    current_step: str = ""
    next_action: str = ""
    requires_user_input: bool = False
    options: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)


class AgentProjectStateResponse(BaseModel):
    project_id: str
    state: dict[str, Any]

