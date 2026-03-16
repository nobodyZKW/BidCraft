from __future__ import annotations

from copy import deepcopy
from typing import Any

from jsonschema import ValidationError, validate

from app.agent.types import (
    CheckMissingFieldsToolInput,
    ExtractionResult,
    ExtractRequirementsToolInput,
    MergeClarificationsToolInput,
    ProposeClarificationQuestionsToolInput,
)
from app.schemas.json_schemas import EXTRACTION_SCHEMA
from app.services.extraction_service import (
    CLARIFY_QUESTIONS,
    MVP_REQUIRED_FIELDS,
    ExtractionService,
)
from app.tools.exceptions import ToolInputError, raise_tool_error


def _validate_extraction_payload(payload: dict[str, Any]) -> None:
    validate(instance=payload, schema=EXTRACTION_SCHEMA)


def _compute_missing_fields(payload: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in MVP_REQUIRED_FIELDS:
        value = payload.get(field)
        if value in (None, "", 0, []):
            missing.append(field)
    return missing


def extract_requirements_tool(
    tool_input: ExtractRequirementsToolInput,
    extraction_service: ExtractionService,
) -> ExtractionResult:
    """Extract structured requirements from raw text using ExtractionService."""

    try:
        structured_data = extraction_service.extract(tool_input.raw_input_text)
        _validate_extraction_payload(structured_data)
        return ExtractionResult(
            structured_data=structured_data,
            missing_fields=structured_data.get("missing_fields", []),
            clarification_questions=structured_data.get("clarification_questions", []),
            message="requirements extracted",
            trace=["extraction.extract_requirements"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="extract_requirements_tool")
        raise


def merge_clarifications_tool(
    tool_input: MergeClarificationsToolInput,
) -> ExtractionResult:
    """Merge user clarifications into structured data and re-evaluate missing fields."""

    try:
        merged = deepcopy(tool_input.structured_data)
        for key, value in tool_input.user_clarifications.items():
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            merged[key] = value

        missing_fields = _compute_missing_fields(merged)
        clarification_questions = [
            CLARIFY_QUESTIONS[field]
            for field in missing_fields
            if field in CLARIFY_QUESTIONS
        ]
        merged["missing_fields"] = missing_fields
        merged["clarification_questions"] = clarification_questions
        _validate_extraction_payload(merged)
        return ExtractionResult(
            structured_data=merged,
            missing_fields=missing_fields,
            clarification_questions=clarification_questions,
            message="clarifications merged",
            trace=["extraction.merge_clarifications"],
        )
    except ValidationError as exc:
        raise ToolInputError(
            "Merged clarification data failed extraction schema validation",
            {"errors": str(exc)},
        ) from exc
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="merge_clarifications_tool")
        raise


def check_missing_fields_tool(
    tool_input: CheckMissingFieldsToolInput,
) -> ExtractionResult:
    """Calculate missing MVP fields and clarification questions from structured data."""

    try:
        structured_data = deepcopy(tool_input.structured_data)
        missing_fields = _compute_missing_fields(structured_data)
        clarification_questions = [
            CLARIFY_QUESTIONS[field]
            for field in missing_fields
            if field in CLARIFY_QUESTIONS
        ]
        structured_data["missing_fields"] = missing_fields
        structured_data["clarification_questions"] = clarification_questions
        _validate_extraction_payload(structured_data)
        return ExtractionResult(
            structured_data=structured_data,
            missing_fields=missing_fields,
            clarification_questions=clarification_questions,
            message="missing fields checked",
            trace=["extraction.check_missing_fields"],
        )
    except ValidationError as exc:
        raise ToolInputError(
            "Structured data failed extraction schema validation",
            {"errors": str(exc)},
        ) from exc
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="check_missing_fields_tool")
        raise


def propose_clarification_questions_tool(
    tool_input: ProposeClarificationQuestionsToolInput,
) -> ExtractionResult:
    """Generate clarification questions from missing field names."""

    try:
        questions = [
            CLARIFY_QUESTIONS[field]
            for field in tool_input.missing_fields
            if field in CLARIFY_QUESTIONS
        ]
        return ExtractionResult(
            structured_data={},
            missing_fields=tool_input.missing_fields,
            clarification_questions=questions,
            message="clarification questions proposed",
            trace=["extraction.propose_clarification_questions"],
        )
    except Exception as exc:  # pragma: no cover - normalized below
        raise_tool_error(exc, context="propose_clarification_questions_tool")
        raise

