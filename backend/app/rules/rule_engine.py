from __future__ import annotations

import re
from datetime import date

from app.core.settings import settings
from app.models.domain import Clause, RiskItem, RiskSeverity, ValidationResult
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService


class RuleEngine:
    def __init__(
        self,
        knowledge_retrieval_service: KnowledgeRetrievalService | None = None,
    ):
        self.knowledge_retrieval_service = knowledge_retrieval_service

    @staticmethod
    def _extract_advance_payment_percent(payment_terms: str) -> int:
        terms = (payment_terms or "").replace(" ", "")
        match = re.match(r"^(\d{1,3})/", terms)
        if not match:
            return 0
        return int(match.group(1))

    @staticmethod
    def _has_clause_type(clauses: list[Clause], clause_type: str) -> bool:
        return any(clause.clause_type == clause_type for clause in clauses)

    def _build_risk(
        self,
        *,
        code: str,
        message: str,
        severity: RiskSeverity,
        location: str,
    ) -> RiskItem:
        risk = RiskItem(
            code=code,
            message=message,
            severity=severity,
            location=location,
        )
        if self.knowledge_retrieval_service is not None:
            risk.citations = self.knowledge_retrieval_service.cite_risk(risk)
        return risk

    def evaluate(
        self,
        structured_data: dict,
        selected_clauses: list[Clause],
        rendered_content: str,
        unresolved_placeholders: list[str],
    ) -> ValidationResult:
        risks: list[RiskItem] = []
        today = date.today()

        if not structured_data.get("budget_amount"):
            risks.append(
                self._build_risk(
                    code="MISSING_BUDGET",
                    message="预算金额不能为空",
                    severity=RiskSeverity.high,
                    location="结构化参数 > budget_amount",
                )
            )
        if not structured_data.get("method"):
            risks.append(
                self._build_risk(
                    code="MISSING_METHOD",
                    message="采购方式不能为空",
                    severity=RiskSeverity.high,
                    location="结构化参数 > method",
                )
            )
        if not structured_data.get("payment_terms"):
            risks.append(
                self._build_risk(
                    code="MISSING_PAYMENT_TERMS",
                    message="付款条款不能为空",
                    severity=RiskSeverity.high,
                    location="合同专用条款 > 付款条款",
                )
            )
        if not structured_data.get("acceptance_standard"):
            risks.append(
                self._build_risk(
                    code="MISSING_ACCEPTANCE_STANDARD",
                    message="缺少验收标准",
                    severity=RiskSeverity.high,
                    location="合同专用条款 > 验收条款",
                )
            )
        if not self._has_clause_type(selected_clauses, "liability"):
            risks.append(
                self._build_risk(
                    code="MISSING_LIABILITY",
                    message="缺少违约责任条款",
                    severity=RiskSeverity.high,
                    location="合同专用条款 > 违约责任",
                )
            )
        if not self._has_clause_type(selected_clauses, "dispute"):
            risks.append(
                self._build_risk(
                    code="MISSING_DISPUTE",
                    message="缺少争议解决条款",
                    severity=RiskSeverity.high,
                    location="合同专用条款 > 争议解决",
                )
            )

        advance_percent = self._extract_advance_payment_percent(
            str(structured_data.get("payment_terms", ""))
        )
        if advance_percent > settings.max_advance_payment_percent:
            risks.append(
                self._build_risk(
                    code="ADVANCE_PAYMENT_OVER_LIMIT",
                    message=(
                        f"预付款比例 {advance_percent}% 超过红线 "
                        f"{settings.max_advance_payment_percent}%"
                    ),
                    severity=RiskSeverity.high,
                    location="合同专用条款 > 付款条款",
                )
            )

        for clause in selected_clauses:
            if clause.status != "approved":
                risks.append(
                    self._build_risk(
                        code="CLAUSE_NOT_APPROVED",
                        message=f"条款 {clause.clause_id} 不是 approved 状态",
                        severity=RiskSeverity.high,
                        location=f"条款库 > {clause.clause_id}",
                    )
                )
            if clause.expiry_date and clause.expiry_date < today:
                risks.append(
                    self._build_risk(
                        code="CLAUSE_VERSION_EXPIRED",
                        message=f"条款 {clause.clause_id} 版本已过期",
                        severity=RiskSeverity.high,
                        location=f"条款库 > {clause.clause_id}",
                    )
                )

        if unresolved_placeholders:
            risks.append(
                self._build_risk(
                    code="UNRESOLVED_PLACEHOLDER",
                    message=f"存在未填充占位符: {', '.join(unresolved_placeholders)}",
                    severity=RiskSeverity.high,
                    location="文档渲染结果",
                )
            )

        warranty_months = int(structured_data.get("warranty_months") or 0)
        if structured_data.get("procurement_type") == "goods" and warranty_months < 12:
            risks.append(
                self._build_risk(
                    code="WARRANTY_MISMATCH",
                    message="货物采购建议质保期不少于12个月",
                    severity=RiskSeverity.medium,
                    location="结构化参数 > warranty_months",
                )
            )

        delivery_days = int(structured_data.get("delivery_days") or 0)
        acceptance_text = str(structured_data.get("acceptance_standard", ""))
        if (
            delivery_days > 0
            and "一次性验收" in acceptance_text
            and int(structured_data.get("delivery_batches") or 1) > 1
        ):
            risks.append(
                self._build_risk(
                    code="DELIVERY_ACCEPTANCE_CONFLICT",
                    message="分批交付与一次性验收存在冲突",
                    severity=RiskSeverity.medium,
                    location="验收条款",
                )
            )

        discriminatory_keywords = ["仅限", "指定品牌", "本地企业", "排他", "唯一供应商"]
        qualification_lines = structured_data.get("qualification_requirements", []) or []
        if any(
            any(keyword in line for keyword in discriminatory_keywords)
            for line in qualification_lines
        ):
            risks.append(
                self._build_risk(
                    code="POTENTIAL_DISCRIMINATION",
                    message="资格条件存在疑似歧视性表述",
                    severity=RiskSeverity.medium,
                    location="资格要求",
                )
            )

        day_values = {
            int(value) for value in re.findall(r"(\d+)\s*天", rendered_content or "")
        }
        if len(day_values) > 1:
            risks.append(
                self._build_risk(
                    code="DELIVERY_DATE_INCONSISTENT",
                    message="文档中交付期限存在多个不同值",
                    severity=RiskSeverity.medium,
                    location="全文一致性",
                )
            )

        can_export_formal = not any(risk.severity == RiskSeverity.high for risk in risks)
        return ValidationResult(risk_summary=risks, can_export_formal=can_export_formal)
