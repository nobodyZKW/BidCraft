from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_project_service
from app.schemas.api import (
    CreateProjectRequest,
    CreateProjectResponse,
    ExportRequest,
    ExportResponse,
    ExtractRequest,
    ExtractResponse,
    GenerateDocumentRequest,
    GenerateDocumentResponse,
    MatchClausesRequest,
    MatchClausesResponse,
    ProjectResponse,
    RenderRequest,
    RenderResponse,
    ValidateRequest,
    ValidateResponse,
)
from app.services.project_service import ProjectService


router = APIRouter(prefix="/api")


def _to_public_file_url(request: Request, file_path: str) -> str:
    filename = Path(file_path).name
    return str(request.base_url).rstrip("/") + f"/exports/{filename}"


@router.post(
    "/projects",
    response_model=CreateProjectResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["项目管理"],
    summary="创建项目",
    description="创建一个采购项目，返回项目 ID。",
)
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


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    tags=["项目管理"],
    summary="获取项目详情",
    description="根据项目 ID 查询项目当前状态与元信息。",
)
def get_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    try:
        project = service.get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProjectResponse(project=project)


@router.post(
    "/projects/{project_id}/extract",
    response_model=ExtractResponse,
    tags=["抽取与生成"],
    summary="抽取结构化需求",
    description="提交自然语言采购需求，返回结构化数据、缺失字段和澄清问题。",
)
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


@router.post(
    "/projects/{project_id}/clauses/match",
    response_model=MatchClausesResponse,
    tags=["抽取与生成"],
    summary="匹配候选条款",
    description="根据结构化参数匹配章节条款，并返回备选条款。",
)
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


@router.post(
    "/projects/{project_id}/validate",
    response_model=ValidateResponse,
    tags=["校验与导出"],
    summary="运行合规校验",
    description="执行硬规则与语义规则，返回风险列表和正式版导出许可标记。",
)
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


@router.post(
    "/projects/{project_id}/render",
    response_model=RenderResponse,
    tags=["校验与导出"],
    summary="渲染文档预览",
    description="按模板与条款渲染文档，返回 HTML 预览与文档版本号。",
)
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


@router.post(
    "/projects/{project_id}/export",
    response_model=ExportResponse,
    tags=["校验与导出"],
    summary="导出文档",
    description="导出 docx/pdf 文件。若请求 formal 且命中高风险，将返回 400。",
)
def export(
    project_id: str,
    request: ExportRequest,
    http_request: Request,
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
    return ExportResponse(file_url=_to_public_file_url(http_request, file_path))


@router.post(
    "/projects/generate",
    response_model=GenerateDocumentResponse,
    tags=["抽取与生成"],
    summary="一键生成文档",
    description=(
        "输入自然语言需求，自动执行创建项目、抽取、匹配、校验、渲染、导出全流程。"
        "若 formal 模式被高风险拦截，会自动降级为 draft 并返回下载链接。"
    ),
)
def generate_document(
    request: GenerateDocumentRequest,
    http_request: Request,
    service: ProjectService = Depends(get_project_service),
) -> GenerateDocumentResponse:
    result = service.generate_from_text(
        project_name=request.project_name,
        department=request.department,
        raw_input_text=request.raw_input_text,
        fmt=request.format,
        mode=request.mode,
        created_by=request.created_by,
        operator_id=request.operator_id,
    )

    return GenerateDocumentResponse(
        project_id=result["project_id"],
        missing_fields=result["missing_fields"],
        clarification_questions=result["clarification_questions"],
        risk_summary=result["risk_summary"],
        can_export_formal=result["can_export_formal"],
        preview_html=result["preview_html"],
        file_url=_to_public_file_url(http_request, result["file_path"]),
        export_blocked=result["export_blocked"],
        delivered_mode=result["delivered_mode"],
        message=result["message"],
        tool_calls=result.get("tool_calls", []),
    )
