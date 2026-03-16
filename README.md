# BidCraft AI (MVP)

BidCraft AI is an MVP for procurement document generation.
It converts free-form requirement text into structured, validated, exportable bidding documents.

## 1. MVP Scope

In scope:
- procurement type: `goods`
- method: `public_tender`
- export format: `docx`, `pdf`
- deterministic formal export gate (high risk blocks formal export)

Out of scope:
- service/engineering procurement
- approval workflow integration
- OCR ingestion for scanned documents

## 2. Core Pipeline

1. structured extraction (`ExtractionService` + schema validation + fallback)
2. clause matching (`ClauseService` + clause repository)
3. template rendering (`TemplateRenderer`)
4. rule validation (`RuleEngine`)
5. export (`ExportService`)

## 3. Refactored Architecture

Backend layers:
- `app/api`: REST routes only
- `app/agent`: LangGraph state/nodes/graph/runtime
- `app/tools`: typed wrappers around services/guards
- `app/services`: business capabilities + legacy `ProjectService` facade
- `app/repositories`: persistence only
- `app/rules`: deterministic rules and export guard

Hard boundaries:
- services do not depend on graph
- repositories do not depend on services
- graph nodes call tools only
- API routes do not perform complex orchestration
- formal export gate is code-level deterministic logic (`rules/export_guard.py`)

## 4. API Surfaces

### 4.1 Legacy REST (Backward Compatible)

- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/extract`
- `POST /api/projects/{project_id}/clauses/match`
- `POST /api/projects/{project_id}/validate`
- `POST /api/projects/{project_id}/render`
- `POST /api/projects/{project_id}/export`
- `POST /api/projects/generate`

Compatibility note:
- legacy routes remain callable with previous request/response shapes
- internals now delegate to tools/guards where applicable

### 4.2 Agent Routes (New)

- `POST /api/agent/chat`
- `POST /api/agent/projects/{project_id}/continue`
- `GET /api/agent/projects/{project_id}/state`

`/api/agent/chat` response includes:
- `assistant_message`
- `project_id`
- `current_step`
- `next_action`
- `requires_user_input`
- `options`
- `tool_calls`
- `artifacts`

## 5. LangGraph Workflow

Main nodes:
- `understand_intent`
- `ensure_project`
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

Interrupt points:
- clarification request
- high-risk fix choice
- formal export confirmation

## 6. Local Setup

### 6.1 Backend

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend URLs:
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

### 6.2 Frontend

```bash
cd frontend
npm.cmd install
npm.cmd run dev
```

Frontend URL:
- `http://127.0.0.1:3000`

## 7. LangGraph Dependency Installation

LangGraph dependencies are already listed in `requirements.txt`.
If you need manual install:

```bash
pip install "langgraph>=0.3.0,<2.0.0" "langchain-core>=0.3.0,<1.0.0"
```

## 8. Agent/Chat Invocation Examples

### 8.1 Start chat

```bash
curl -X POST "http://127.0.0.1:8000/api/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Server procurement, budget 3000000 CNY, delivery 45 days, payment 30/60/10, acceptance by test report, warranty 24 months, formal export"
  }'
```

### 8.2 Continue paused project

```bash
curl -X POST "http://127.0.0.1:8000/api/agent/projects/{project_id}/continue" \
  -H "Content-Type: application/json" \
  -d '{
    "user_clarifications": {
      "confirmed_export": true,
      "allow_draft": false
    }
  }'
```

### 8.3 Get persisted graph state

```bash
curl "http://127.0.0.1:8000/api/agent/projects/{project_id}/state"
```

## 9. Formal Export Gate Behavior

Rules:
- `draft` export: allowed (even if medium/high risks exist)
- `formal` export: blocked when any high-severity risk exists

Enforcement:
- gate logic lives in `backend/app/rules/export_guard.py`
- the gate is reused by legacy and agent flows

## 10. Testing and Verification

Backend tests:

```bash
pytest backend/tests -q
```

Frontend quality checks:

```bash
cd frontend
npm.cmd run lint
npm.cmd run build
```

## 11. Key Docs

- `docs/agent_refactor.md`
- `docs/tool_contracts.md`
- `docs/migration_notes.md`
- `docs/prd.md`
- `docs/rulebook.md`
