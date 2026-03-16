from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.agent.runtime import AgentWorkflowRunner
from app.api.dependencies import get_agent_workflow_runner
from app.schemas.agent_api import (
    AgentChatRequest,
    AgentChatResponse,
    AgentContinueRequest,
    AgentProjectStateResponse,
)


router_agent = APIRouter(prefix="/api/agent", tags=["Agent"])


@router_agent.post(
    "/chat",
    response_model=AgentChatResponse,
    summary="Run agent chat workflow",
)
def agent_chat(
    request: AgentChatRequest,
    runner: AgentWorkflowRunner = Depends(get_agent_workflow_runner),
) -> AgentChatResponse:
    try:
        payload = runner.run_chat(
            message=request.message,
            session_id=request.session_id,
            project_id=request.project_id,
            user_clarifications=request.user_clarifications,
        )
        return AgentChatResponse.model_validate(payload.model_dump(mode="json"))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router_agent.post(
    "/projects/{project_id}/continue",
    response_model=AgentChatResponse,
    summary="Continue a paused agent project workflow",
)
def continue_agent_project(
    project_id: str,
    request: AgentContinueRequest,
    runner: AgentWorkflowRunner = Depends(get_agent_workflow_runner),
) -> AgentChatResponse:
    try:
        payload = runner.continue_project(
            project_id=project_id,
            message=request.message,
            user_clarifications=request.user_clarifications,
        )
        return AgentChatResponse.model_validate(payload.model_dump(mode="json"))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router_agent.get(
    "/projects/{project_id}/state",
    response_model=AgentProjectStateResponse,
    summary="Get latest persisted agent graph state for project",
)
def get_agent_project_state(
    project_id: str,
    runner: AgentWorkflowRunner = Depends(get_agent_workflow_runner),
) -> AgentProjectStateResponse:
    try:
        state = runner.get_project_state(project_id)
        return AgentProjectStateResponse(project_id=project_id, state=state)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

