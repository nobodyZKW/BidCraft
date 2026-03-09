# Rulebook (MVP)

## High Severity (Block formal export)
- `MISSING_BUDGET`
- `MISSING_METHOD`
- `MISSING_PAYMENT_TERMS`
- `MISSING_ACCEPTANCE_STANDARD`
- `MISSING_LIABILITY`
- `MISSING_DISPUTE`
- `ADVANCE_PAYMENT_OVER_LIMIT`
- `CLAUSE_NOT_APPROVED`
- `CLAUSE_VERSION_EXPIRED`
- `UNRESOLVED_PLACEHOLDER`

## Medium Severity (Warn + allow draft)
- `WARRANTY_MISMATCH`
- `DELIVERY_ACCEPTANCE_CONFLICT`
- `POTENTIAL_DISCRIMINATION`
- `DELIVERY_DATE_INCONSISTENT`

## Output Structure
```json
{
  "risk_summary": [
    {
      "code": "MISSING_ACCEPTANCE_STANDARD",
      "message": "缺少验收标准",
      "severity": "high",
      "location": "合同专用条款 > 验收条款"
    }
  ],
  "can_export_formal": false
}
```
