from __future__ import annotations

from urllib.parse import urlparse

from fastapi.testclient import TestClient

from app.main import app


def test_api_end_to_end_flow() -> None:
    client = TestClient(app)

    create_resp = client.post(
        "/api/projects",
        json={"project_name": "Server Procurement", "department": "IT"},
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["project_id"]

    extract_resp = client.post(
        f"/api/projects/{project_id}/extract",
        json={
            "raw_input_text": (
                "Server procurement project, budget 3000000 CNY, "
                "delivery 45 days, payment 30/60/10, "
                "acceptance by test report, warranty 24 months."
            ),
        },
    )
    assert extract_resp.status_code == 200
    assert extract_resp.json()["missing_fields"] == []

    match_resp = client.post(f"/api/projects/{project_id}/clauses/match", json={})
    assert match_resp.status_code == 200
    assert len(match_resp.json()["sections"]) >= 4

    validate_resp = client.post(f"/api/projects/{project_id}/validate", json={})
    assert validate_resp.status_code == 200
    assert validate_resp.json()["can_export_formal"] is True

    render_resp = client.post(f"/api/projects/{project_id}/render", json={})
    assert render_resp.status_code == 200
    assert render_resp.json()["preview_html"].startswith("<html>")

    export_resp = client.post(
        f"/api/projects/{project_id}/export",
        json={"format": "docx", "mode": "formal"},
    )
    assert export_resp.status_code == 200
    export_url = export_resp.json()["file_url"]
    parsed = urlparse(export_url)
    assert parsed.path.startswith("/exports/")

    file_resp = client.get(parsed.path)
    assert file_resp.status_code == 200
    assert len(file_resp.content) > 0


def test_generate_endpoint_runs_full_pipeline() -> None:
    client = TestClient(app)
    resp = client.post(
        "/api/projects/generate",
        json={
            "project_name": "Storage Procurement",
            "department": "IT",
            "raw_input_text": (
                "Storage procurement, budget 1800000 CNY, delivery 30 days, "
                "payment 20/70/10, acceptance by test report, warranty 24 months."
            ),
            "format": "pdf",
            "mode": "draft",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["project_id"]
    assert payload["file_url"]
    assert payload["preview_html"].startswith("<html>")
    assert payload["export_blocked"] is False
    assert payload["delivered_mode"] == "draft"


def test_generate_formal_auto_fallback_to_draft() -> None:
    client = TestClient(app)
    resp = client.post(
        "/api/projects/generate",
        json={
            "project_name": "High Risk Procurement",
            "department": "IT",
            "raw_input_text": (
                "Procure servers, budget 3000000 CNY, delivery 30 days, "
                "payment 70/20/10, warranty 6 months."
            ),
            "format": "docx",
            "mode": "formal",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["can_export_formal"] is False
    assert payload["export_blocked"] is True
    assert payload["delivered_mode"] == "draft"
    assert payload["file_url"]
    assert "已自动生成草稿版" in payload["message"]

    parsed = urlparse(payload["file_url"])
    file_resp = client.get(parsed.path)
    assert file_resp.status_code == 200


def test_agent_chat_response_includes_trace_summary() -> None:
    client = TestClient(app)
    resp = client.post(
        "/api/agent/chat",
        json={
            "message": (
                "Server procurement project, budget 3000000 CNY, delivery 45 days, "
                "payment 30/60/10, acceptance by test report, warranty 24 months."
            ),
            "session_id": "trace_summary_case",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "trace" in payload["artifacts"]
    assert "trace_summary" in payload["artifacts"]
    assert payload["artifacts"]["trace_summary"]["run_id"]
