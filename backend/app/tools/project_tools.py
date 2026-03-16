from __future__ import annotations

from app.agent.types import (
    CreateProjectToolInput,
    ProjectDocumentToolResult,
    ProjectRefToolInput,
    ProjectSnapshotToolResult,
    ProjectStatusToolResult,
    ProjectToolResult,
)
from app.services.project_service import ProjectService
from app.tools.exceptions import ToolNotFoundError, raise_tool_error


def create_project_tool(
    tool_input: CreateProjectToolInput,
    project_service: ProjectService,
) -> ProjectToolResult:
    """Create a project and return normalized project payload."""

    try:
        project = project_service.create_project(
            project_name=tool_input.project_name,
            department=tool_input.department,
            created_by=tool_input.created_by or tool_input.operator_id,
        )
        return ProjectToolResult(
            project=project,
            message="project created",
            trace=["project.create"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="create_project_tool")
        raise


def get_project_tool(
    tool_input: ProjectRefToolInput,
    project_service: ProjectService,
) -> ProjectToolResult:
    """Fetch a project by id."""

    try:
        project = project_service.get_project(tool_input.project_id)
        return ProjectToolResult(
            project=project,
            message="project loaded",
            trace=["project.get"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="get_project_tool")
        raise


def get_latest_snapshot_tool(
    tool_input: ProjectRefToolInput,
    project_service: ProjectService,
) -> ProjectSnapshotToolResult:
    """Fetch latest requirement snapshot for the project."""

    try:
        snapshot = project_service.get_latest_snapshot(tool_input.project_id)
        if snapshot is None:
            raise ToolNotFoundError(
                "Requirement snapshot not found",
                {"project_id": tool_input.project_id},
            )
        return ProjectSnapshotToolResult(
            snapshot=snapshot,
            structured_data=snapshot.structured_data,
            missing_fields=snapshot.missing_fields,
            message="latest snapshot loaded",
            trace=["project.get_latest_snapshot"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="get_latest_snapshot_tool")
        raise


def get_latest_document_tool(
    tool_input: ProjectRefToolInput,
    project_service: ProjectService,
) -> ProjectDocumentToolResult:
    """Fetch latest rendered/exported document version for the project."""

    try:
        document = project_service.get_latest_document(tool_input.project_id)
        if document is None:
            raise ToolNotFoundError(
                "Document version not found",
                {"project_id": tool_input.project_id},
            )
        return ProjectDocumentToolResult(
            document=document,
            message="latest document loaded",
            trace=["project.get_latest_document"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="get_latest_document_tool")
        raise


def get_project_status_tool(
    tool_input: ProjectRefToolInput,
    project_service: ProjectService,
) -> ProjectStatusToolResult:
    """Fetch current project status for route/graph branching."""

    try:
        status = project_service.get_project_status(tool_input.project_id)
        return ProjectStatusToolResult(
            status=status,
            message="project status loaded",
            trace=["project.get_status"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="get_project_status_tool")
        raise

