# Implementation Runbook

## 1. Initialize
1. Install dependencies: `pip install -r requirements.txt`
2. Configure environment: copy `.env.example` to `.env` if needed.
3. Put DeepSeek key in `config/config.py` (already wired by backend settings).

## 2. Run Backend
1. `cd backend`
2. `python -m uvicorn app.main:app --reload --port 8000`
3. Open Swagger: `http://127.0.0.1:8000/docs`

## 3. Run Frontend (scaffold)
1. `cd frontend`
2. `npm install`
3. `npm run dev`
4. Visit `http://127.0.0.1:3000`

## 4. MVP API Sequence
1. `POST /api/projects`
2. `POST /api/projects/{project_id}/extract`
3. `POST /api/projects/{project_id}/clauses/match`
4. `POST /api/projects/{project_id}/validate`
5. `POST /api/projects/{project_id}/render`
6. `POST /api/projects/{project_id}/export`

## 5. Tests
1. `pytest backend/tests -q`

## 6. Notes
- Formal export is blocked when any high-severity risk exists.
- Clause/template/rule data are stored under `data/`.
- Audit and runtime snapshots are persisted to `data/runtime/`.
