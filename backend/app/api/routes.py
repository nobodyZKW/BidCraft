from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_project_service
from app.schemas.api import (
    CreateProjectRequest,
    CreateProjectResponse,
    ExportRequest,
    ExportResponse,
    ExtractRequest,
    ExtractResponse,
    MatchClausesRequest,
    MatchClausesResponse,
    ProjectResponse,
    RenderRequest,
    RenderResponse,
    ValidateRequest,
    ValidateResponse,
)
from app.services.project_service import ProjectService


router = APIRouter(prefix="/api", tags=["bidcraft-mvp"])


@router.post("/projects", response_model=CreateProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    request: CreateProjectRequest,
    service: ProjectService = Depends(get_project_service),
) -> CreateProjectResponse:
    project = service.create_project(
        project_name=request.project_name,
        department=request.department,
        created_by=request.created_by,
    )
    return CreateProjectResponse(project_id=project.project_id)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    try:
        project = service.get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProjectResponse(project=project)


@router.post("/projects/{project_id}/extract", response_model=ExtractResponse)
def extract(
    project_id: str,
    request: ExtractRequest,
    service: ProjectService = Depends(get_project_service),
) -> ExtractResponse:
    try:
        structured = service.extract(
            project_id=project_id,
            raw_input_text=request.raw_input_text,
            operator_id=request.operator_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ExtractResponse(
        structured_data=structured,
        missing_fields=structured.get("missing_fields", []),
        clarification_questions=structured.get("clarification_questions", []),
    )


@router.post("/projects/{project_id}/clauses/match", response_model=MatchClausesResponse)
def match_clauses(
    project_id: str,
    request: MatchClausesRequest,
    service: ProjectService = Depends(get_project_service),
) -> MatchClausesResponse:
    try:
        _, sections = service.match_clauses(
            project_id=project_id,
            selected_clause_ids=request.selected_clause_ids,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MatchClausesResponse(sections=sections)


@router.post("/projects/{project_id}/validate", response_model=ValidateResponse)
def validate(
    project_id: str,
    request: ValidateRequest,
    service: ProjectService = Depends(get_project_service),
) -> ValidateResponse:
    try:
        result = service.validate(
            project_id=project_id,
            selected_clause_ids=request.selected_clause_ids,
            operator_id=request.operator_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ValidateResponse(
        risk_summary=result.risk_summary,
        can_export_formal=result.can_export_formal,
    )


@router.post("/projects/{project_id}/render", response_model=RenderResponse)
def render(
    project_id: str,
    request: RenderRequest,
    service: ProjectService = Depends(get_project_service),
) -> RenderResponse:
    try:
        result = service.render(
            project_id=project_id,
            selected_clause_ids=request.selected_clause_ids,
            operator_id=request.operator_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RenderResponse(doc_version_id=result.doc_version_id, preview_html=result.preview_html)


@router.post("/projects/{project_id}/export", response_model=ExportResponse)
def export(
    project_id: str,
    request: ExportRequest,
    service: ProjectService = Depends(get_project_service),
) -> ExportResponse:
    try:
        file_path = service.export(
            project_id=project_id,
            fmt=request.format,
            mode=request.mode,
            selected_clause_ids=request.selected_clause_ids,
            operator_id=request.operator_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExportResponse(file_url=file_path)
