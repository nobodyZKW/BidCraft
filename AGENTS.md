# AGENTS.md

## Objective
Build an MVP for procurement document generation:
input requirement text -> structured extraction -> clause matching -> rule validation -> doc export.

## Constraints
- MVP only supports goods procurement + public tender.
- Do not implement non-MVP features.
- All model outputs must pass JSON schema validation.
- Formal export must be blocked when high-severity risks exist.

## Engineering requirements
- Backend: Python + FastAPI
- Frontend: React/Next.js
- Add tests for rules, renderers, schemas, and API endpoints.
- Keep functions small and typed where practical.
- Never hardcode clause content in business logic; load from data files or DB.

## Verification
Before marking task complete:
- Run backend tests
- Run frontend build/lint
- Verify demo flow end-to-end
