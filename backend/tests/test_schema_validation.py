from __future__ import annotations

from app.llm.deepseek_client import DeepSeekClient
from app.services.extraction_service import ExtractionService


def test_extraction_fallback_generates_valid_payload() -> None:
    service = ExtractionService(DeepSeekClient())
    text = "服务器采购项目，预算300万元，45天交付，付款30/60/10，验收按国家标准，质保24个月。"
    result = service.extract(text)

    assert result["project_name"]
    assert result["procurement_type"] == "goods"
    assert result["method"] == "public_tender"
    assert result["budget_amount"] == 3000000
    assert result["delivery_days"] == 45
    assert result["payment_terms"] == "30/60/10"
    assert "budget_amount" not in result["missing_fields"]


def test_extraction_missing_fields_are_reported() -> None:
    service = ExtractionService(DeepSeekClient())
    result = service.extract("采购一批设备，尽快上线。")

    assert "budget_amount" in result["missing_fields"]
    assert "payment_terms" in result["missing_fields"]
    assert len(result["clarification_questions"]) >= 1
