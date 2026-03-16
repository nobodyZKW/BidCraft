from __future__ import annotations

from app.agent.types import ExportDocumentToolInput, ExportToolResult
from app.services.export_service import ExportService
from app.tools.exceptions import raise_tool_error


def export_document_tool(
    tool_input: ExportDocumentToolInput,
    export_service: ExportService,
) -> ExportToolResult:
    """Export rendered content to docx/pdf with deterministic formal gate behavior."""

    try:
        if tool_input.mode == "formal" and not tool_input.can_export_formal:
            return ExportToolResult(
                success=False,
                blocked=True,
                format=tool_input.format,
                mode=tool_input.mode,
                message="formal export blocked by guard",
                trace=["export.export_document.blocked"],
            )

        file_path = export_service.export(
            project_name=tool_input.project_name,
            rendered_content=tool_input.rendered_content,
            doc_type=tool_input.doc_type,
            version=tool_input.version,
            fmt=tool_input.format,
            mode=tool_input.mode,
        )
        return ExportToolResult(
            file_path=str(file_path),
            format=tool_input.format,
            mode=tool_input.mode,
            blocked=False,
            message="document exported",
            trace=["export.export_document"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="export_document_tool")
        raise

