EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "project_name": {"type": "string"},
        "procurement_type": {"type": "string", "enum": ["goods"]},
        "budget_amount": {"type": "number", "minimum": 0},
        "currency": {"type": "string"},
        "method": {"type": "string", "enum": ["public_tender"]},
        "delivery_days": {"type": "integer", "minimum": 0},
        "warranty_months": {"type": "integer", "minimum": 0},
        "payment_terms": {"type": "string"},
        "delivery_batches": {"type": "integer", "minimum": 1},
        "acceptance_standard": {"type": "string"},
        "qualification_requirements": {
            "type": "array",
            "items": {"type": "string"},
        },
        "evaluation_method": {"type": "string"},
        "technical_requirements": {
            "type": "array",
            "items": {"type": "string"},
        },
        "special_terms": {
            "type": "array",
            "items": {"type": "string"},
        },
        "missing_fields": {
            "type": "array",
            "items": {"type": "string"},
        },
        "clarification_questions": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "project_name",
        "procurement_type",
        "budget_amount",
        "currency",
        "method",
        "delivery_days",
        "warranty_months",
        "payment_terms",
        "delivery_batches",
        "acceptance_standard",
        "qualification_requirements",
        "evaluation_method",
        "technical_requirements",
        "special_terms",
        "missing_fields",
        "clarification_questions",
    ],
    "additionalProperties": False,
}


RISK_REPAIR_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "structured_patch": {
            "type": "object",
            "properties": {
                "budget_amount": {"type": "number", "minimum": 0},
                "method": {"type": "string", "enum": ["public_tender"]},
                "payment_terms": {"type": "string"},
                "acceptance_standard": {"type": "string"},
                "delivery_days": {"type": "integer", "minimum": 0},
                "warranty_months": {"type": "integer", "minimum": 0},
                "delivery_batches": {"type": "integer", "minimum": 1},
                "evaluation_method": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "enforce_clause_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["liability", "dispute", "payment", "acceptance"],
            },
            "uniqueItems": True,
        },
        "reset_clause_overrides": {"type": "boolean"},
        "notes": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "structured_patch",
        "enforce_clause_types",
        "reset_clause_overrides",
        "notes",
    ],
    "additionalProperties": False,
}


CLARIFICATION_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "accepted": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "normalized_clarifications": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string"},
                "budget_amount": {"type": "number", "minimum": 0},
                "payment_terms": {"type": "string"},
                "acceptance_standard": {"type": "string"},
                "delivery_days": {"type": "integer", "minimum": 0},
                "warranty_months": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": False,
        },
        "errors": {
            "type": "array",
            "items": {"type": "string"},
        },
        "follow_up_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "question": {"type": "string"},
                },
                "required": ["field", "question"],
                "additionalProperties": False,
            },
        },
        "reasoning": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "accepted",
        "confidence",
        "normalized_clarifications",
        "errors",
        "follow_up_questions",
        "reasoning",
    ],
    "additionalProperties": False,
}
