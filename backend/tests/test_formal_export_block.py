from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_formal_export_is_blocked_when_high_risk_exists() -> None:
    client = TestClient(app)

    project_resp = client.post(
        "/api/projects",
        json={"project_name": "高风险采购", "department": "信息部"},
    )
    project_id = project_resp.json()["project_id"]

    client.post(
        f"/api/projects/{project_id}/extract",
        json={
            "raw_input_text": "采购服务器，预算300万元，交付30天，付款70/20/10，质保6个月。",
        },
    )

    export_resp = client.post(
        f"/api/projects/{project_id}/export",
        json={"format": "pdf", "mode": "formal"},
    )
    assert export_resp.status_code == 400
    assert "禁止导出正式版" in export_resp.json()["detail"]
