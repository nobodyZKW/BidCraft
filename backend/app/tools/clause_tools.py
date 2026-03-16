from __future__ import annotations

from app.agent.policies import DefaultOverridePolicy, OverridePolicy
from app.agent.types import (
    ClauseAlternativesResult,
    ClauseMatchResult,
    ClauseSelectionExplanationResult,
    ExplainClauseSelectionToolInput,
    ListClauseAlternativesToolInput,
    MatchClausesToolInput,
    OverrideClauseSelectionToolInput,
)
from app.services.clause_service import ClauseService
from app.tools.exceptions import ToolInputError, raise_tool_error


def match_clauses_tool(
    tool_input: MatchClausesToolInput,
    clause_service: ClauseService,
) -> ClauseMatchResult:
    """Match clauses by structured procurement data with optional overrides."""

    try:
        selected_clauses, sections = clause_service.match(
            structured_data=tool_input.structured_data,
            selected_clause_ids=tool_input.selected_clause_ids,
        )
        return ClauseMatchResult(
            selected_clause_ids=[item.clause_id for item in selected_clauses],
            matched_sections=sections,
            message="clauses matched",
            trace=["clause.match"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="match_clauses_tool")
        raise


def list_clause_alternatives_tool(
    tool_input: ListClauseAlternativesToolInput,
    clause_service: ClauseService,
) -> ClauseAlternativesResult:
    """List alternatives under one clause type for current structured data."""

    try:
        alternatives = clause_service.list_alternatives(
            clause_type=tool_input.clause_type,
            structured_data=tool_input.structured_data,
        )
        return ClauseAlternativesResult(
            clause_type=tool_input.clause_type,
            selected_clause_id=alternatives[0].clause_id if alternatives else None,
            alternatives=[item.clause_id for item in alternatives],
            message="clause alternatives loaded",
            trace=["clause.list_alternatives"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="list_clause_alternatives_tool")
        raise


def override_clause_selection_tool(
    tool_input: OverrideClauseSelectionToolInput,
    clause_service: ClauseService,
    override_policy: OverridePolicy | None = None,
) -> ClauseMatchResult:
    """Apply a clause override and return a normalized re-match result."""

    policy = override_policy or DefaultOverridePolicy()
    try:
        target_clause = clause_service.get_by_id(tool_input.override_clause_id)
        if target_clause is None:
            raise ToolInputError(
                "Override clause id does not exist",
                {"override_clause_id": tool_input.override_clause_id},
            )

        alternatives = clause_service.list_alternatives(
            clause_type=target_clause.clause_type,
            structured_data=tool_input.structured_data,
        )
        allowed_ids = [item.clause_id for item in alternatives]
        if not policy.can_override(
            target_clause_id=tool_input.override_clause_id,
            allowed_clause_ids=allowed_ids,
        ):
            raise ToolInputError(
                "Override clause id is not allowed for current context",
                {
                    "override_clause_id": tool_input.override_clause_id,
                    "allowed_clause_ids": allowed_ids,
                },
            )

        selected_clauses, _ = clause_service.match(
            structured_data=tool_input.structured_data,
            selected_clause_ids=tool_input.selected_clause_ids,
        )
        kept_ids: list[str] = []
        for clause in selected_clauses:
            if clause.clause_type != target_clause.clause_type:
                kept_ids.append(clause.clause_id)
        kept_ids.append(tool_input.override_clause_id)

        overridden = MatchClausesToolInput(
            session_id=tool_input.session_id,
            project_id=tool_input.project_id,
            operator_id=tool_input.operator_id,
            structured_data=tool_input.structured_data,
            selected_clause_ids=kept_ids,
        )
        return match_clauses_tool(overridden, clause_service)
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="override_clause_selection_tool")
        raise


def explain_clause_selection_tool(
    tool_input: ExplainClauseSelectionToolInput,
    clause_service: ClauseService,
) -> ClauseSelectionExplanationResult:
    """Explain why current clause IDs are selected for each clause type."""

    try:
        selected_clauses, sections = clause_service.match(
            structured_data=tool_input.structured_data,
            selected_clause_ids=tool_input.selected_clause_ids,
        )
        by_type = {item.clause_type: item for item in selected_clauses}
        filtered_sections = [
            section
            for section in sections
            if tool_input.clause_type is None or section.section_id == tool_input.clause_type
        ]
        explanations: list[str] = []
        for section in filtered_sections:
            selected_clause = by_type.get(section.section_id)
            clause_name = selected_clause.clause_name if selected_clause else section.selected_clause_id
            explanations.append(
                f"{section.section_id}: selected {section.selected_clause_id} ({clause_name}); {section.reason}"
            )

        return ClauseSelectionExplanationResult(
            explanations=explanations,
            matched_sections=filtered_sections,
            message="clause selection explained",
            trace=["clause.explain_selection"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="explain_clause_selection_tool")
        raise

