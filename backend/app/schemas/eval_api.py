from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvalCaseResult(BaseModel):
    case_id: str
    category: str
    input_text: str
    missing_fields: list[str] = Field(default_factory=list)
    risk_count: int = 0
    high_risk_count: int = 0
    can_export_formal: bool = False
    passed: bool = False
    expectation: str = ""


class EvalCategoryResult(BaseModel):
    category: str
    total_cases: int
    passed_cases: int
    pass_rate: float
    cases: list[EvalCaseResult] = Field(default_factory=list)


class EvalRunRequest(BaseModel):
    mode: str = Field(default="quick", pattern="^(quick|full)$")


class EvalRunResponse(BaseModel):
    generated_at: str
    mode: str = "quick"
    total_cases: int
    passed_cases: int
    pass_rate: float
    categories: list[EvalCategoryResult] = Field(default_factory=list)
