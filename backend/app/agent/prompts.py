from __future__ import annotations


INTENT_PARSE_PROMPT = (
    "Identify user intent and map it to one enum value: "
    "view_missing_fields / override_payment_clause / formal_export / draft_export / generate_document."
)

CLARIFICATION_PROMPT_TEMPLATE = (
    "Detected missing required fields. Please provide clarification values, "
    "then continue to proceed with generation."
)

FIX_PLAN_PROMPT_TEMPLATE = (
    "High-severity risks were detected. Choose a repair option to continue, "
    "or allow draft downgrade when acceptable."
)

CONFIRM_EXPORT_PROMPT_TEMPLATE = (
    "Formal export is ready to run. Please confirm whether to continue."
)

DEFAULT_RESPONSE_TEMPLATE = (
    "Workflow reached {current_step}. Suggested next action: {next_action}."
)

CLARIFICATION_REVIEW_SYSTEM_PROMPT = (
    "You are a procurement clarification verifier (policy engineer). "
    "Your task is to verify whether user clarifications are sufficient, "
    "consistent, and actionable for the goods + public_tender workflow. "
    "Return strict JSON only."
)

CLARIFICATION_REVIEW_TASK_TEMPLATE = """
Context:
- Scope is MVP-only: goods procurement + public tender.
- Hard-risk gate remains in code; your output is review signal only.
- If accepted, workflow continues to clause matching and validation.

Conversation history (chronological):
{chat_history}

Current user input:
{raw_input_text}

Current structured_data before merge:
{structured_data}

Current missing_fields:
{missing_fields}

Current clarification_questions:
{clarification_questions}

User clarification payload:
{user_clarifications}

Validation requirements:
1. Check each clarification for field-level correctness and consistency with prior context.
2. Normalize values when safe (e.g. payment_terms format, numeric conversion).
3. Reject if still ambiguous/invalid/conflicting.
4. On reject, provide explicit errors and concise follow-up questions.
5. Keep output machine-actionable.

Output requirements:
- Strictly follow the provided JSON schema.
- No markdown, no extra keys.
"""
