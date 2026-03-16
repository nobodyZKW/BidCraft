# Agent Refactor Guide

## 1. Scope

This refactor evolves BidCraft from a fixed pipeline orchestrator into a tool-based architecture with a LangGraph orchestration layer while preserving all legacy REST APIs.

MVP scope remains unchanged:
- procurement type: `goods`
- method: `public_tender`
- export formats: `docx`, `pdf`
- formal export must be blocked when high-severity risks exist

## 2. Layered Architecture

Current backend layering:
- `api/`: request/response handling only
- `agent/`: graph state, nodes, prompts, runtime orchestration
- `tools/`: normalized wrappers around services and guards
- `services/`: business capabilities, legacy facade compatibility
- `repositories/`: persistence/data access only
- `rules/`: deterministic rule evaluation and formal export guard

Primary execution paths:
- legacy REST path: `routes.py -> ProjectService facade -> tools/services/rules`
- agent path: `routes_agent.py -> AgentWorkflowRunner -> LangGraph nodes -> tools`

## 3. Hard Module Boundaries

Enforced boundaries in this refactor:
- services do not depend on graph
- repositories do not depend on services
- tools wrap services/guards and normalize I/O
- graph nodes call tools only (no direct repository access)
- API routes do not implement process orchestration
- prompts do not store business rule constants
- formal export gate is deterministic code logic (`rules/export_guard.py`)

## 4. LangGraph Workflow

Graph entry:
- `START -> understand_intent -> ensure_project`

Main nodes:
- `extract_requirements`
- `decide_need_clarification`
- `ask_for_clarification`
- `merge_clarifications`
- `match_clauses`
- `validate_document`
- `decide_repair_or_continue`
- `build_fix_options`
- `render_preview`
- `confirm_export`
- `export_document`
- `respond`

Interrupt checkpoints:
- `ask_for_clarification`
- `build_fix_options`
- `confirm_export`

## 5. State Contract

Graph state fields are centralized in `agent/state.py` and include:
- context: `session_id`, `project_id`, `messages`, `user_intent`
- extraction: `raw_input_text`, `structured_data`, `missing_fields`, `clarification_questions`, `user_clarifications`
- clauses/validation: `selected_clause_ids`, `matched_sections`, `validation_result`, `risk_summary`, `can_export_formal`
- rendering/export: `preview_html`, `rendered_content`, `file_path`
- control: `pending_human_confirmation`, `options`, `tool_calls`, `current_step`, `next_action`, `error`, `trace`

## 6. Formal Export Gate

Single source of truth:
- `rules/export_guard.py`

Rules:
- formal export allowed only when `ValidationResult` has no high-severity risks
- both one-shot generation and explicit export share the same guard
- agent export path also uses the same guard via validation tools

## 7. Extension Guide

To add a new capability:
1. Add/extend service logic (if needed) with deterministic behavior.
2. Add a tool wrapper with typed input/output in `agent/types.py`.
3. Add node logic in `agent/nodes.py` that calls the tool.
4. Add graph edges/branching in `agent/graph.py`.
5. Add tests in `tests/unit`, `tests/integration`, and `tests/graph`.

Avoid:
- embedding business rules in prompts
- bypassing tool schemas with ad-hoc dicts
- placing repository queries directly inside graph nodes
