# BidCraft AI (MVP)

BidCraft AI is an MVP for procurement document generation.
It takes free-form requirement text and turns it into a structured, validated, exportable procurement document.

The system is designed to reduce drafting time, improve consistency, and block high-risk outputs from being exported as formal documents.

## 1. What This Project Does

Input:
- Natural language procurement requirement text

Pipeline:
1. Structured extraction (LLM + schema validation + fallback parser)
2. Clause matching (versioned clause library)
3. Template assembly (section + clause block composition)
4. Rule validation (hard + semantic risk checks)
5. Document rendering and export

Output:
- Preview HTML
- Export file in `docx` or `pdf`
- Risk summary and formal-export gate flag

## 2. MVP Scope

In scope:
- Procurement type: `goods`
- Method: `public_tender`
- Exports: `docx`, `pdf`
- Endpoints for create/extract/match/validate/render/export
- One-shot endpoint for full pipeline generation

Out of scope (future iterations):
- Service/engineering procurement
- Multi-language document generation
- Approval workflow integration
- OCR for scanned historical contracts

## 3. Tech Stack

Backend:
- Python 3.12
- FastAPI
- Pydantic
- jsonschema
- reportlab (PDF rendering)

Frontend:
- Next.js
- React
- TypeScript

Testing:
- pytest

## 4. Repository Structure

```text
.
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ core/
│  │  ├─ llm/
│  │  ├─ models/
│  │  ├─ renderers/
│  │  ├─ repositories/
│  │  ├─ rules/
│  │  ├─ schemas/
│  │  └─ services/
│  └─ tests/
├─ config/
├─ data/
│  ├─ clauses/
│  ├─ templates/
│  ├─ seeds/
│  └─ runtime/
├─ docs/
├─ exports/
├─ frontend/
├─ .env.example
└─ requirements.txt
```

## 5. Configuration

### 5.1 API Key Priority

The backend loads DeepSeek API key in this order:
1. Environment variable `DEEPSEEK_API_KEY`
2. `config/config.py`:
   - `DEEPSEEK_API_KEY`, or
   - `API_KEY`

Main loader:
- `backend/app/core/settings.py`

### 5.2 Environment Variables

See `.env.example`:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
MAX_ADVANCE_PAYMENT_PERCENT=50
REQUEST_TIMEOUT_SECONDS=30
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## 6. Quick Start

### 6.1 Start Backend
安装环境
```bash
# 在项目根目录执行
#cd d:\zkw\study\工程实训
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

运行后端
```bash
#跳转到项目根目录
#cd d:\zkw\study\工程实训

cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend URLs:
- Home: `http://127.0.0.1:8000/`
- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health: `http://127.0.0.1:8000/health`

### 6.2 Start Frontend

运行前端
```bash
#跳转到项目根目录
#cd d:\zkw\study\工程实训\frontend

npm.cmd install
npm.cmd run dev
```

Frontend URL:
- `http://127.0.0.1:3000`

Note (Windows PowerShell):
- If `npm` script policy is blocked, use `npm.cmd`.

## 7. API Overview

Base URL:
- `http://127.0.0.1:8000`

Project:
- `POST /api/projects`
- `GET /api/projects/{project_id}`

Generation pipeline:
- `POST /api/projects/{project_id}/extract`
- `POST /api/projects/{project_id}/clauses/match`
- `POST /api/projects/{project_id}/validate`
- `POST /api/projects/{project_id}/render`
- `POST /api/projects/{project_id}/export`

One-shot generation:
- `POST /api/projects/generate`

## 8. One-Shot Endpoint Example

Request:

```json
{
  "project_name": "Server Procurement Project",
  "department": "IT Department",
  "raw_input_text": "Server procurement project, budget 3000000 CNY, delivery in 45 days, payment terms 30/60/10, acceptance by test report, warranty 24 months.",
  "format": "pdf",
  "mode": "formal"
}
```

Important response fields:
- `risk_summary`: validation findings
- `can_export_formal`: whether formal export is allowed
- `export_blocked`: whether formal export was blocked
- `delivered_mode`: actual output mode (`formal` or downgraded `draft`)
- `file_url`: downloadable output file URL

## 9. Export Behavior and Risk Gate

Rules:
- `draft`: allowed with medium/low risks
- `formal`: blocked when any high severity risk exists

Special behavior for one-shot endpoint:
- If user requests `formal` but high risk exists:
  - API does not fail with 400
  - API auto-generates a `draft` file
  - API returns draft download URL and explanatory message

Direct export endpoint behavior:
- `POST /api/projects/{project_id}/export` with `mode=formal` still returns `400` when blocked (strict mode).

## 10. Data and Persistence

Static data:
- Clause library: `data/clauses/clauses.json`
- Template rules: `data/templates/document_template.json`
- Seed examples: `data/seeds/`

Runtime data:
- Project snapshots, doc versions, audit logs:
  - `data/runtime/`

Export files:
- `exports/`

## 11. Testing

Run all backend tests:

```bash
cd d:\zkw\study\工程实训
pytest backend/tests -q
```

Covered areas:
- Extraction/schema validation
- Rule engine
- Template rendering
- Export services
- API end-to-end flow

## 12. Troubleshooting

### 12.1 `npm` Not Found in PowerShell

Use:

```bash
npm.cmd install
npm.cmd run dev
```

### 12.2 PowerShell `npm.ps1` Execution Policy Error

Temporary workaround:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 12.3 Formal Export Blocked

This is expected when high severity risk exists.
Check these fields in response:
- `risk_summary`
- `can_export_formal`
- `export_blocked`
- `delivered_mode`
- `file_url`

### 12.4 PDF Link Exists But You Cannot Open File

Check:
1. Backend is still running
2. URL host/port matches your backend instance
3. File is present in `exports/`

## 13. Related Docs

- `docs/prd.md`: MVP requirement summary
- `docs/api.md`: API summary
- `docs/rulebook.md`: validation rule list
- `plans.md`: milestone plan
- `implement.md`: implementation runbook
