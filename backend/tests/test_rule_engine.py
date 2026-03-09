from __future__ import annotations

from datetime import date

from app.models.domain import Clause
from app.rules.rule_engine import RuleEngine


def _build_clause(clause_type: str, clause_id: str = "C1") -> Clause:
    return Clause(
        clause_id=clause_id,
        clause_name=clause_type,
        clause_type=clause_type,
        content_template="text",
        applicable_procurement_types=["goods"],
        applicable_methods=["public_tender"],
        required_fields=[],
        forbidden_conditions=[],
        risk_level="low",
        version="v1",
        effective_date=date(2024, 1, 1),
        expiry_date=None,
        status="approved",
    )


def test_rule_engine_blocks_formal_export_on_high_risks() -> None:
    engine = RuleEngine()
    structured_data = {
        "project_name": "测试项目",
        "procurement_type": "goods",
        "budget_amount": 0,
        "method": "public_tender",
        "payment_terms": "70/20/10",
        "acceptance_standard": "",
        "delivery_days": 20,
        "delivery_batches": 2,
        "warranty_months": 6,
        "qualification_requirements": ["供应商仅限本地企业"],
    }
    clauses = [_build_clause("payment")]
    result = engine.evaluate(
        structured_data=structured_data,
        selected_clauses=clauses,
        rendered_content="交付20天，交付30天",
        unresolved_placeholders=["budget_amount"],
    )

    risk_codes = {item.code for item in result.risk_summary}
    assert "MISSING_BUDGET" in risk_codes
    assert "MISSING_ACCEPTANCE_STANDARD" in risk_codes
    assert "ADVANCE_PAYMENT_OVER_LIMIT" in risk_codes
    assert "MISSING_LIABILITY" in risk_codes
    assert "MISSING_DISPUTE" in risk_codes
    assert "UNRESOLVED_PLACEHOLDER" in risk_codes
    assert result.can_export_formal is False
