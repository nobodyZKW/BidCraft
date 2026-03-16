from __future__ import annotations

from app.agent.policies import DefaultHumanConfirmationPolicy, HumanConfirmationPolicy
from app.agent.types import (
    BuildUserOptionsToolInput,
    HumanConfirmationToolResult,
    RequestHumanConfirmationToolInput,
    UserOptionsToolResult,
)
from app.tools.exceptions import raise_tool_error


def build_user_options_tool(
    tool_input: BuildUserOptionsToolInput,
) -> UserOptionsToolResult:
    """Build structured clarification options from missing fields and question prompts."""

    try:
        options: list[dict[str, str]] = []
        for index, field in enumerate(tool_input.missing_fields):
            question = (
                tool_input.clarification_questions[index]
                if index < len(tool_input.clarification_questions)
                else f"请补充字段 {field}"
            )
            options.append(
                {
                    "field": field,
                    "question": question,
                }
            )
        return UserOptionsToolResult(
            requires_user_input=len(options) > 0,
            prompt="请先补充缺失信息，再继续生成流程。",
            options=options,
            message="clarification options built",
            trace=["clarification.build_user_options"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="build_user_options_tool")
        raise


def request_human_confirmation_tool(
    tool_input: RequestHumanConfirmationToolInput,
    policy: HumanConfirmationPolicy | None = None,
) -> HumanConfirmationToolResult:
    """Check whether a step must pause for explicit human confirmation."""

    confirmation_policy = policy or DefaultHumanConfirmationPolicy()
    try:
        pending_confirmation = confirmation_policy.requires_confirmation(tool_input.action)
        prompt = tool_input.message or f"请确认是否继续执行动作: {tool_input.action}"
        return HumanConfirmationToolResult(
            pending_human_confirmation=pending_confirmation,
            action=tool_input.action,
            prompt=prompt,
            options=tool_input.options,
            message="human confirmation evaluated",
            trace=["clarification.request_human_confirmation"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="request_human_confirmation_tool")
        raise

