from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_api_end_to_end_flow() -> None:
    client = TestClient(app)

    create_resp = client.post(
        "/api/projects",
        json={"project_name": "服务器采购项目", "department": "信息部"},
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["project_id"]

    extract_resp = client.post(
        f"/api/projects/{project_id}/extract",
        json={
            "raw_input_text": "服务器采购项目，预算300万元，45天交付，付款30/60/10，验收按国家标准，质保24个月，供应商需具备相关资质。",
        },
    )
    assert extract_resp.status_code == 200
    extract_data = extract_resp.json()
    assert extract_data["missing_fields"] == []

    match_resp = client.post(
        f"/api/projects/{project_id}/clauses/match",
        json={},
    )
    assert match_resp.status_code == 200
    sections = match_resp.json()["sections"]
    assert len(sections) >= 4

    validate_resp = client.post(
        f"/api/projects/{project_id}/validate",
        json={},
    )
    assert validate_resp.status_code == 200
    validate_data = validate_resp.json()
    assert validate_data["can_export_formal"] is True

    render_resp = client.post(
        f"/api/projects/{project_id}/render",
        json={},
    )
    assert render_resp.status_code == 200
    assert render_resp.json()["preview_html"].startswith("<html>")

    export_resp = client.post(
        f"/api/projects/{project_id}/export",
        json={"format": "docx", "mode": "formal"},
    )
    assert export_resp.status_code == 200
    path = Path(export_resp.json()["file_url"])
    assert path.exists()
