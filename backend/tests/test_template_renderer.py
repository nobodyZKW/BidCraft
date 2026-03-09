from __future__ import annotations

from datetime import date
from pathlib import Path

from app.models.domain import Clause
from app.renderers.template_renderer import TemplateRenderer
from app.repositories.template_repository import TemplateRepository


def test_template_renderer_replaces_placeholders() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    renderer = TemplateRenderer(
        TemplateRepository(root_dir / "data" / "templates" / "document_template.json")
    )
    clause = Clause(
        clause_id="DELIVERY_ACCEPTANCE_V2",
        clause_name="交付与验收条款",
        clause_type="delivery",
        content_template="应在{{delivery_days}}天内完成交付。",
        applicable_procurement_types=["goods"],
        applicable_methods=["public_tender"],
        required_fields=[],
        forbidden_conditions=[],
        risk_level="low",
        version="v2",
        effective_date=date(2024, 1, 1),
        status="approved",
    )
    structured_data = {
        "project_name": "服务器采购项目",
        "procurement_type": "goods",
        "method": "public_tender",
        "budget_amount": 3000000,
        "currency": "CNY",
        "delivery_days": 45,
        "evaluation_method": "comprehensive_scoring",
        "qualification_requirements": ["具备相关资质"],
        "technical_requirements": ["CPU >= 32核"],
    }

    rendered, html, unresolved, used_clause_ids = renderer.render(
        structured_data=structured_data,
        selected_clauses=[clause],
    )

    assert "45天" in rendered
    assert "服务器采购项目" in rendered
    assert "DELIVERY_ACCEPTANCE_V2" in rendered
    assert unresolved == []
    assert used_clause_ids == ["DELIVERY_ACCEPTANCE_V2"]
    assert "<html>" in html
