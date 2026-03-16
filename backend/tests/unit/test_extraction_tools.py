from __future__ import annotations

from app.agent.types import (
    CheckMissingFieldsToolInput,
    ExtractRequirementsToolInput,
    MergeClarificationsToolInput,
    ProposeClarificationQuestionsToolInput,
)
from app.api.dependencies import get_project_service
from app.tools.extraction_tools import (
    check_missing_fields_tool,
    extract_requirements_tool,
    merge_clarifications_tool,
    propose_clarification_questions_tool,
)


def test_extract_requirements_tool() -> None:
    service = get_project_service()
    result = extract_requirements_tool(
        ExtractRequirementsToolInput(
            raw_input_text=(
                "Server procurement project, budget 3000000 CNY, delivery 45 days, "
                "payment 30/60/10, acceptance by test report, warranty 24 months."
            )
        ),
        extraction_service=service.extraction_service,
    )
    assert result.structured_data["method"] == "public_tender"
    assert result.missing_fields == []


def test_merge_and_missing_and_question_tools() -> None:
    payload = {
        "project_name": "Server procurement project",
        "procurement_type": "goods",
        "budget_amount": 0,
        "currency": "CNY",
        "method": "public_tender",
        "delivery_days": 0,
        "warranty_months": 0,
        "payment_terms": "",
        "delivery_batches": 1,
        "acceptance_standard": "",
        "qualification_requirements": [],
        "evaluation_method": "comprehensive_scoring",
        "technical_requirements": [],
        "special_terms": [],
        "missing_fields": [],
        "clarification_questions": [],
    }

    missing = check_missing_fields_tool(
        CheckMissingFieldsToolInput(structured_data=payload)
    )
    assert "budget_amount" in missing.missing_fields

    merged = merge_clarifications_tool(
        MergeClarificationsToolInput(
            structured_data=payload,
            user_clarifications={
                "budget_amount": 2000000,
                "payment_terms": "20/70/10",
                "acceptance_standard": "acceptance by report",
                "delivery_days": 30,
                "warranty_months": 24,
            },
        )
    )
    assert merged.missing_fields == []

    questions = propose_clarification_questions_tool(
        ProposeClarificationQuestionsToolInput(
            missing_fields=["budget_amount", "payment_terms"]
        )
    )
    assert len(questions.clarification_questions) == 2

