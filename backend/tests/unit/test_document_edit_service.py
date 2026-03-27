from __future__ import annotations

from app.services.document_edit_service import DocumentEditService


def test_document_edit_service_applies_project_name_change() -> None:
    service = DocumentEditService()
    result = service.apply_edits(
        text="帮我把项目名称改为xxxx测试",
        structured_data={
            "project_name": "原项目名称",
            "budget_amount": 3000000,
        },
    )

    assert result.structured_data["project_name"] == "xxxx测试"
    assert result.updated_fields == ["project_name"]


def test_document_edit_service_normalizes_inline_edits() -> None:
    service = DocumentEditService()
    result = service.apply_edits(
        text=(
            "budget_amount=300万元; payment_terms=30/60/10; "
            "delivery_days=30天; warranty_months=12个月"
        ),
        structured_data={},
    )

    assert result.structured_data["budget_amount"] == 3000000
    assert result.structured_data["payment_terms"] == "30/60/10"
    assert result.structured_data["delivery_days"] == 30
    assert result.structured_data["warranty_months"] == 12
