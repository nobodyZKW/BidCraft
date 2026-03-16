# Migration Notes

## 1. Summary

BidCraft has been incrementally migrated from a fixed-order service orchestrator to:
- tool-based execution contracts
- LangGraph orchestration for agent/chat workflows
- backward-compatible legacy REST APIs

No big-bang rewrite was performed.

## 2. Key Changes

### Added
- `app/agent/`: state, types, policies, nodes, graph, runtime
- `app/tools/`: project/extraction/clause/validation/render/export/clarification tools
- `app/api/routes_agent.py`: agent/chat API surface
- `app/rules/export_guard.py`: centralized formal export gate
- `app/repositories/agent_state_repository.py`: persisted agent state

### Refactored
- `ProjectService` now acts as a legacy facade and delegates to tool/service units
- `_build_document` monolithic orchestration removed
- formal export gate moved to deterministic guard

### Preserved
- legacy REST endpoints and response contracts remain active
- MVP scope remains goods + public tender only

## 3. Compatibility Matrix

Legacy endpoints (unchanged):
- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/extract`
- `POST /api/projects/{project_id}/clauses/match`
- `POST /api/projects/{project_id}/validate`
- `POST /api/projects/{project_id}/render`
- `POST /api/projects/{project_id}/export`
- `POST /api/projects/generate`

New endpoints:
- `POST /api/agent/chat`
- `POST /api/agent/projects/{project_id}/continue`
- `GET /api/agent/projects/{project_id}/state`

## 4. Data and Runtime Impact

New runtime persistence:
- `data/runtime/agent_states.json`

Existing runtime stores are unchanged:
- projects, snapshots, documents, audit logs

No database migration is required for current JSON storage mode.

## 5. Guard and Risk Behavior

Formal export eligibility is now centralized in:
- `app/rules/export_guard.py`

This guard is reused by:
- legacy export flow
- legacy one-shot generation flow
- agent validation/export flow

Formal export is never delegated to free-form LLM decisions.

## 6. Rollback Strategy

If rollback is required:
1. stop registering `routes_agent.py` in `main.py`
2. switch `ProjectService` methods back to legacy inline implementation (if needed)
3. keep `export_guard.py` recommended even in rollback for deterministic gate behavior

## 7. Known Gaps / Follow-ups

- agent export format currently defaults to `docx`
- agent path does not yet persist all export metadata back to project document history
- intent parsing is deterministic rule-based (can be replaced later while keeping hard business guards in code)
