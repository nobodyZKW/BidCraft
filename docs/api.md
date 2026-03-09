# API Summary (MVP)

Base URL: `http://127.0.0.1:8000`

## `POST /api/projects/generate`
One-shot pipeline for frontend:
create project -> extract -> match -> validate -> render -> export.

## `POST /api/projects`
Create project.

## `POST /api/projects/{project_id}/extract`
Submit requirement text and extract structured JSON.

## `POST /api/projects/{project_id}/clauses/match`
Get selected clauses and alternatives by section.

## `POST /api/projects/{project_id}/validate`
Run compliance validation and return risk summary.

## `POST /api/projects/{project_id}/render`
Render preview HTML and create a draft document version.

## `POST /api/projects/{project_id}/export`
Export in `docx` or `pdf`, mode `draft` or `formal`.

## Swagger
FastAPI auto-docs:
- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`
