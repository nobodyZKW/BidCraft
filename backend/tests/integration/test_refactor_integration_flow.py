from __future__ import annotations

from fastapi.testclient import TestClient

from app.agent.types import (
    MatchClausesToolInput,
    MergeClarificationsToolInput,
    OverrideClauseSelectionToolInput,
    ValidateDocumentToolInput,
)
from app.api.dependencies import get_project_service
from app.main import app
from app.tools.clause_tools import match_clauses_tool, override_clause_selection_tool
from app.tools.extraction_tools import merge_clarifications_tool
from app.tools.validation_tools import validate_document_tool


def test_create_extract_match_validate_render_export_draft() -> None:
    client = TestClient(app)
    created = client.post(
        "/api/projects",
        json={"project_name": "Integration Flow", "department": "IT"},
    )
    assert created.status_code == 201
    project_id = created.json()["project_id"]

    extracted = client.post(
        f"/api/projects/{project_id}/extract",
        json={
            "raw_input_text": (
                "Server procurement project, budget 2800000 CNY, delivery 40 days, "
                "payment 30/60/10, acceptance by test report, warranty 24 months."
            )
        },
    )
    assert extracted.status_code == 200

    matched = client.post(f"/api/projects/{project_id}/clauses/match", json={})
    assert matched.status_code == 200
    assert matched.json()["sections"]
    assert matched.json()["sections"][0]["citations"]

    validated = client.post(f"/api/projects/{project_id}/validate", json={})
    assert validated.status_code == 200
    assert all("citations" in item for item in validated.json()["risk_summary"])

    rendered = client.post(f"/api/projects/{project_id}/render", json={})
    assert rendered.status_code == 200
    assert rendered.json()["preview_html"].startswith("<html>")

    exported = client.post(
        f"/api/projects/{project_id}/export",
        json={"format": "docx", "mode": "draft"},
    )
    assert exported.status_code == 200
    assert "/exports/" in exported.json()["file_url"]


def test_create_extract_missing_then_merge_clarification_then_validate() -> None:
    service = get_project_service()
    project = service.create_project("Clarify Flow", "IT", "tester")
    structured = service.extract(
        project_id=project.project_id,
        raw_input_text="Procure servers for data center.",
        operator_id="tester",
    )
    assert structured["missing_fields"]

    merged = merge_clarifications_tool(
        MergeClarificationsToolInput(
            project_id=project.project_id,
            structured_data=structured,
            user_clarifications={
                "budget_amount": 3000000,
                "payment_terms": "20/70/10",
                "acceptance_standard": "acceptance by test report",
                "delivery_days": 30,
                "warranty_months": 24,
                "method": "public_tender",
                "procurement_type": "goods",
            },
        )
    )
    assert merged.missing_fields == []
    validation = validate_document_tool(
        ValidateDocumentToolInput(
            project_id=project.project_id,
            structured_data=merged.structured_data,
            selected_clause_ids=[],
        ),
        clause_service=service.clause_service,
        template_renderer=service.template_renderer,
        rule_engine=service.rule_engine,
    )
    assert validation.risk_summary is not None


def test_formal_export_blocked_when_high_risk() -> None:
    client = TestClient(app)
    created = client.post(
        "/api/projects",
        json={"project_name": "High Risk Export", "department": "IT"},
    )
    project_id = created.json()["project_id"]
    client.post(
        f"/api/projects/{project_id}/extract",
        json={
            "raw_input_text": (
                "Procure servers, budget 3000000 CNY, delivery 30 days, "
                "payment 70/20/10, warranty 6 months."
            )
        },
    )
    exported = client.post(
        f"/api/projects/{project_id}/export",
        json={"format": "pdf", "mode": "formal"},
    )
    assert exported.status_code == 400


def test_override_clause_then_revalidate() -> None:
    service = get_project_service()
    project = service.create_project("Override Flow", "IT", "tester")
    structured = service.extract(
        project_id=project.project_id,
        raw_input_text=(
            "Server procurement project, budget 2800000 CNY, delivery 35 days, "
            "payment 30/60/10, acceptance by test report, warranty 24 months."
        ),
        operator_id="tester",
    )
    matched = match_clauses_tool(
        tool_input=MatchClausesToolInput(
            project_id=project.project_id,
            structured_data=structured,
            selected_clause_ids=[],
        ),
        clause_service=service.clause_service,
    )
    assert matched.selected_clause_ids

    payment_type_sections = [s for s in matched.matched_sections if s.section_id == "payment"]
    assert payment_type_sections
    alternatives = payment_type_sections[0].alternatives
    assert alternatives
    assert payment_type_sections[0].citations

    overridden = override_clause_selection_tool(
        OverrideClauseSelectionToolInput(
            project_id=project.project_id,
            structured_data=structured,
            selected_clause_ids=matched.selected_clause_ids,
            override_clause_id=alternatives[0],
        ),
        clause_service=service.clause_service,
    )
    assert alternatives[0] in overridden.selected_clause_ids

    validation = validate_document_tool(
        ValidateDocumentToolInput(
            project_id=project.project_id,
            structured_data=structured,
            selected_clause_ids=overridden.selected_clause_ids,
        ),
        clause_service=service.clause_service,
        template_renderer=service.template_renderer,
        rule_engine=service.rule_engine,
    )
    assert validation.risk_summary is not None
