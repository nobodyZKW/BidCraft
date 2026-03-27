from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from app.api.dependencies import get_evaluation_service
from app.schemas.eval_api import EvalRunRequest, EvalRunResponse
from app.services.evaluation_service import EvaluationService


router_eval = APIRouter(prefix="/api/evals", tags=["Evaluations"])


@router_eval.post(
    "/run",
    response_model=EvalRunResponse,
    summary="Run offline evaluation suite",
)
def run_evaluation(
    request: EvalRunRequest = Body(default_factory=EvalRunRequest),
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvalRunResponse:
    report = service.run(mode=request.mode)
    return EvalRunResponse.model_validate(report)


@router_eval.get(
    "/latest",
    response_model=EvalRunResponse,
    summary="Get latest evaluation report",
)
def get_latest_evaluation(
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvalRunResponse:
    report = service.load_latest()
    if report is None:
        raise HTTPException(status_code=404, detail="No evaluation report available yet.")
    return EvalRunResponse.model_validate(report)
