from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_run_and_get_latest_evaluation_report() -> None:
    client = TestClient(app)

    run_resp = client.post("/api/evals/run")
    assert run_resp.status_code == 200
    payload = run_resp.json()
    assert payload["total_cases"] > 0
    assert payload["passed_cases"] >= 0
    assert payload["categories"]
    assert any(category["category"] == "normal_cases" for category in payload["categories"])

    latest_resp = client.get("/api/evals/latest")
    assert latest_resp.status_code == 200
    latest = latest_resp.json()
    assert latest["generated_at"]
    assert latest["total_cases"] == payload["total_cases"]
