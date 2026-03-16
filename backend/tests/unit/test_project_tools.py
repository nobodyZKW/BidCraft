from __future__ import annotations

from app.agent.types import (
    CreateProjectToolInput,
    ProjectRefToolInput,
)
from app.api.dependencies import get_project_service
from app.tools.project_tools import (
    create_project_tool,
    get_latest_document_tool,
    get_latest_snapshot_tool,
    get_project_status_tool,
    get_project_tool,
)


def test_project_tools_end_to_end() -> None:
    service = get_project_service()

    created = create_project_tool(
        CreateProjectToolInput(
            project_name="Tool Project",
            department="IT",
            created_by="tester",
            operator_id="tester",
        ),
        project_service=service,
    )
    assert created.project is not None

    project_id = created.project.project_id
    loaded = get_project_tool(
        ProjectRefToolInput(project_id=project_id, operator_id="tester"),
        project_service=service,
    )
    assert loaded.project is not None
    assert loaded.project.project_id == project_id

    structured = service.extract(
        project_id=project_id,
        raw_input_text=(
            "Server procurement project, budget 3000000 CNY, delivery 45 days, "
            "payment 30/60/10, acceptance by test report, warranty 24 months."
        ),
        operator_id="tester",
    )
    assert structured["missing_fields"] == []

    snapshot = get_latest_snapshot_tool(
        ProjectRefToolInput(project_id=project_id, operator_id="tester"),
        project_service=service,
    )
    assert snapshot.snapshot is not None
    assert snapshot.structured_data["project_name"]

    service.render(
        project_id=project_id,
        selected_clause_ids=[],
        operator_id="tester",
    )
    latest_document = get_latest_document_tool(
        ProjectRefToolInput(project_id=project_id, operator_id="tester"),
        project_service=service,
    )
    assert latest_document.document is not None

    status = get_project_status_tool(
        ProjectRefToolInput(project_id=project_id, operator_id="tester"),
        project_service=service,
    )
    assert status.status is not None

