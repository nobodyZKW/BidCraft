from __future__ import annotations


INTENT_PARSE_PROMPT = (
    "Identify user intent and map it to one enum value: "
    "view_missing_fields / override_payment_clause / formal_export / draft_export / generate_document."
)

INTENT_DECISION_SYSTEM_PROMPT = (
    "You are an orchestration planner for a procurement document workflow. "
    "Classify user intent strictly into one allowed enum and return JSON only."
)

INTENT_DECISION_TASK_TEMPLATE = """
User text:
{user_text}

Allowed intents:
- view_missing_fields
- override_payment_clause
- formal_export
- draft_export
- generate_document

Return strict JSON with:
- intent
- confidence
- reason
"""

EXTRACTION_SYSTEM_PROMPT = (
    "You are a procurement analyst. Return JSON only, no markdown. "
    "Output must strictly conform to provided JSON schema."
)

EXTRACTION_TASK_TEMPLATE = (
    "Task A: Extract procurement requirements.\n"
    "Task B: Fill missing_fields and clarification_questions.\n"
    "Raw requirement text:\n{raw_input_text}\n"
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

CLARIFICATION_DECISION_SYSTEM_PROMPT = (
    "You are a workflow router for procurement clarification handling. "
    "Choose the next action conservatively and return JSON only."
)

CLARIFICATION_DECISION_TASK_TEMPLATE = """
Current intent: {intent}
Missing fields: {missing_fields}
Clarification questions: {clarification_questions}
User clarification payload keys: {clarification_keys}

Allowed next_action:
- respond
- merge_clarifications
- ask_for_clarification
- match_clauses

Routing policy:
1. If user only wants to view missing fields, respond.
2. If required fields are still missing and user supplied clarification values, merge_clarifications.
3. If required fields are still missing and user did not supply values, ask_for_clarification.
4. If no required fields are missing, continue to match_clauses.

Return strict JSON with:
- next_action
- confidence
- reason
"""

RISK_REPAIR_SYSTEM_PROMPT = (
    "You are a procurement policy engineer. "
    "Return strict JSON only and focus on reducing high-severity risks."
)

RISK_REPAIR_TASK_TEMPLATE = (
    "Generate one repair plan for procurement structured fields and clause enforcement.\n"
    "Current structured_data: {structured_data}\n"
    "Risk summary: {risk_summary}\n"
    "Return only fields in schema. Do not invent unsupported procurement methods.\n"
    "For goods + public_tender MVP, prefer compliant defaults and minimal edits.\n"
)

REPAIR_DECISION_SYSTEM_PROMPT = (
    "You are a workflow router for procurement risk handling. "
    "Choose the safest next action and return JSON only."
)

REPAIR_DECISION_TASK_TEMPLATE = """
Intent: {intent}
Can export formal: {can_export_formal}
Allow draft: {allow_draft}
Auto repair requested: {auto_repair}
High risk codes: {high_risk_codes}

Allowed next_action:
- respond
- auto_repair_with_pe
- build_fix_options
- render_preview

Routing policy:
1. If intent is override_payment_clause, respond.
2. If formal export is not allowed:
   - choose auto_repair_with_pe when auto repair is requested
   - choose render_preview when draft export is intended or draft downgrade is allowed
   - otherwise choose build_fix_options
3. If formal export is allowed:
   - choose render_preview for formal_export / draft_export / generate_document
   - otherwise choose respond

Return strict JSON with:
- next_action
- confidence
- reason
"""
