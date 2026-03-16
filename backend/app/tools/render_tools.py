from __future__ import annotations

from app.agent.types import RenderPreviewToolInput, RenderToolResult
from app.renderers.template_renderer import TemplateRenderer
from app.services.clause_service import ClauseService
from app.tools.exceptions import raise_tool_error


def render_preview_tool(
    tool_input: RenderPreviewToolInput,
    clause_service: ClauseService,
    template_renderer: TemplateRenderer,
) -> RenderToolResult:
    """Render preview HTML/content from structured data and matched clauses."""

    try:
        selected_clauses, _ = clause_service.match(
            structured_data=tool_input.structured_data,
            selected_clause_ids=tool_input.selected_clause_ids,
        )
        rendered_content, preview_html, unresolved_placeholders, used_clause_ids = template_renderer.render(
            structured_data=tool_input.structured_data,
            selected_clauses=selected_clauses,
        )
        return RenderToolResult(
            rendered_content=rendered_content,
            preview_html=preview_html,
            unresolved_placeholders=unresolved_placeholders,
            used_clause_ids=used_clause_ids,
            message="preview rendered",
            trace=["render.render_preview"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="render_preview_tool")
        raise

