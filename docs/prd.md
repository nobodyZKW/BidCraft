# BidCraft AI PRD (MVP)

## Scope
- Procurement type: `goods`
- Method: `public_tender`
- Outputs: tender body, contract special clauses, requirement attachments
- Capabilities: extraction, clause matching, template assembly, compliance validation, docx/pdf export

## Core Flow
1. Input requirement text
2. LLM structured extraction (JSON schema validation + retry)
3. Missing-field check
4. Clause matching (version-aware)
5. Template assembly
6. Rule validation
7. Preview/edit
8. Export draft/formal

## Hard Rules
- Required fields must exist: budget/method/payment/acceptance.
- Liability and dispute clauses must exist.
- Advance payment ratio must not exceed configured threshold.
- Expired/invalid clause versions are forbidden.
- Unresolved placeholders block formal export.

## Semantic Risk Checks
- Potentially discriminatory qualification terms
- Delivery and acceptance conflict
- Inconsistent delivery days in the full document

## Acceptance
- Endpoints run end-to-end.
- Missing fields and risks are surfaced.
- Formal export is blocked on high-severity risks.
