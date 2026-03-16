# Tool Contracts

## 1. Contract Principles

All tools must:
- use typed input/output models from `agent/types.py`
- return structured outputs (no ad-hoc dict contracts)
- normalize failures via `tools/exceptions.py`
- keep repository access inside services/repositories, not graph nodes

## 2. Project Tools (`tools/project_tools.py`)

- `create_project_tool`
  - input: `CreateProjectToolInput`
  - output: `ProjectToolResult`
  - depends on: `ProjectService.create_project`

- `get_project_tool`
  - input: `ProjectRefToolInput`
  - output: `ProjectToolResult`
  - depends on: `ProjectService.get_project`

- `get_latest_snapshot_tool`
  - input: `ProjectRefToolInput`
  - output: `ProjectSnapshotToolResult`
  - depends on: `ProjectService.get_latest_snapshot`

- `get_latest_document_tool`
  - input: `ProjectRefToolInput`
  - output: `ProjectDocumentToolResult`
  - depends on: `ProjectService.get_latest_document`

- `get_project_status_tool`
  - input: `ProjectRefToolInput`
  - output: `ProjectStatusToolResult`
  - depends on: `ProjectService.get_project_status`

## 3. Extraction Tools (`tools/extraction_tools.py`)

- `extract_requirements_tool`
  - input: `ExtractRequirementsToolInput`
  - output: `ExtractionResult`
  - depends on: `ExtractionService.extract`
  - includes extraction schema validation

- `merge_clarifications_tool`
  - input: `MergeClarificationsToolInput`
  - output: `ExtractionResult`
  - deterministic merge + missing field recalculation

- `check_missing_fields_tool`
  - input: `CheckMissingFieldsToolInput`
  - output: `ExtractionResult`
  - deterministic missing field check

- `propose_clarification_questions_tool`
  - input: `ProposeClarificationQuestionsToolInput`
  - output: `ExtractionResult`
  - maps missing fields to clarification prompts

## 4. Clause Tools (`tools/clause_tools.py`)

- `match_clauses_tool`
  - input: `MatchClausesToolInput`
  - output: `ClauseMatchResult`
  - depends on: `ClauseService.match`

- `list_clause_alternatives_tool`
  - input: `ListClauseAlternativesToolInput`
  - output: `ClauseAlternativesResult`
  - depends on: `ClauseService.list_alternatives`

- `override_clause_selection_tool`
  - input: `OverrideClauseSelectionToolInput`
  - output: `ClauseMatchResult`
  - depends on: `ClauseService.match`, `ClauseService.list_alternatives`
  - uses override policy validation

- `explain_clause_selection_tool`
  - input: `ExplainClauseSelectionToolInput`
  - output: `ClauseSelectionExplanationResult`
  - depends on: `ClauseService.match`

## 5. Validation Tools (`tools/validation_tools.py`)

- `validate_document_tool`
  - input: `ValidateDocumentToolInput`
  - output: `ValidationToolResult`
  - depends on: `ClauseService.match`, `TemplateRenderer.render`, `RuleEngine.evaluate`

- `explain_risk_summary_tool`
  - input: `ExplainRiskSummaryToolInput`
  - output: `RiskSummaryExplanationResult`

- `suggest_fix_plan_tool`
  - input: `SuggestFixPlanToolInput`
  - output: `SuggestFixPlanResult`

- `check_formal_export_eligibility_tool`
  - input: `CheckFormalExportEligibilityToolInput`
  - output: `FormalExportEligibilityResult`
  - depends on: `FormalExportGuard`

## 6. Render/Export/Clarification Tools

### Render (`tools/render_tools.py`)
- `render_preview_tool`
  - input: `RenderPreviewToolInput`
  - output: `RenderToolResult`
  - depends on: `ClauseService.match`, `TemplateRenderer.render`

### Export (`tools/export_tools.py`)
- `export_document_tool`
  - input: `ExportDocumentToolInput`
  - output: `ExportToolResult`
  - depends on: `ExportService.export`
  - blocks formal export when `can_export_formal=False`

### Clarification (`tools/clarification_tools.py`)
- `build_user_options_tool`
  - input: `BuildUserOptionsToolInput`
  - output: `UserOptionsToolResult`

- `request_human_confirmation_tool`
  - input: `RequestHumanConfirmationToolInput`
  - output: `HumanConfirmationToolResult`
  - depends on: `HumanConfirmationPolicy`

## 7. Exception Contract

Unified exceptions in `tools/exceptions.py`:
- `ToolBusinessError` (base)
- `ToolNotFoundError`
- `ToolInputError`
- `ToolExecutionError`

All tool errors should be normalized through `raise_tool_error(...)`.
