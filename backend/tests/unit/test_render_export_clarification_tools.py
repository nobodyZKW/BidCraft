from __future__ import annotations

from app.agent.types import (
    BuildUserOptionsToolInput,
    ExportDocumentToolInput,
    RenderPreviewToolInput,
    RequestHumanConfirmationToolInput,
)
from app.api.dependencies import get_project_service
from app.tools.clarification_tools import (
    build_user_options_tool,
    request_human_confirmation_tool,
)
from app.tools.export_tools import export_document_tool
from app.tools.render_tools import render_preview_tool


def _structured() -> dict:
    return {
        "project_name": "Server procurement project",
        "procurement_type": "goods",
        "budget_amount": 3000000,
        "currency": "CNY",
        "method": "public_tender",
        "delivery_days": 45,
        "warranty_months": 24,
        "payment_terms": "30/60/10",
        "delivery_batches": 1,
        "acceptance_standard": "acceptance by test report",
        "qualification_requirements": [],
        "evaluation_method": "comprehensive_scoring",
        "technical_requirements": [],
        "special_terms": [],
        "missing_fields": [],
        "clarification_questions": [],
    }


def test_render_export_and_clarification_tools() -> None:
    service = get_project_service()
    render_result = render_preview_tool(
        RenderPreviewToolInput(structured_data=_structured(), selected_clause_ids=[]),
        clause_service=service.clause_service,
        template_renderer=service.template_renderer,
    )
    assert render_result.preview_html.startswith("<html>")

    blocked = export_document_tool(
        ExportDocumentToolInput(
            project_name="Tool Export",
            rendered_content=render_result.rendered_content,
            format="docx",
            mode="formal",
            version=1,
            can_export_formal=False,
        ),
        export_service=service.export_service,
    )
    assert blocked.blocked is True

    exported = export_document_tool(
        ExportDocumentToolInput(
            project_name="Tool Export",
            rendered_content=render_result.rendered_content,
            format="docx",
            mode="draft",
            version=1,
            can_export_formal=False,
        ),
        export_service=service.export_service,
    )
    assert exported.file_path

    options = build_user_options_tool(
        BuildUserOptionsToolInput(
            missing_fields=["payment_terms"],
            clarification_questions=["please provide payment terms"],
        )
    )
    assert options.requires_user_input is True
    assert options.options

    confirmation = request_human_confirmation_tool(
        RequestHumanConfirmationToolInput(
            action="confirm_export",
            message="confirm?",
            options=[{"id": 1, "text": "yes"}],
        )
    )
    assert confirmation.pending_human_confirmation is True

