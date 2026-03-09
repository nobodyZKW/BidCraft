from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import MatchedSection, Project, RiskItem


class CreateProjectRequest(BaseModel):
    project_name: str = Field(min_length=1, description="项目名称")
    department: str = Field(min_length=1, description="采购部门")
    created_by: str = Field(default="system", description="创建人")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_name": "服务器采购项目",
                "department": "信息部",
                "created_by": "buyer_001",
            }
        }
    )


class CreateProjectResponse(BaseModel):
    project_id: str = Field(description="项目 ID")


class ExtractRequest(BaseModel):
    raw_input_text: str = Field(min_length=1, description="采购需求自然语言文本")
    operator_id: str = Field(default="system", description="操作人")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "raw_input_text": (
                    "服务器采购项目，预算300万元，45天交付，付款30/60/10，"
                    "验收按国家标准执行，质保24个月。"
                ),
                "operator_id": "buyer_001",
            }
        }
    )


class ExtractResponse(BaseModel):
    structured_data: dict = Field(description="结构化抽取结果")
    missing_fields: list[str] = Field(description="缺失字段列表")
    clarification_questions: list[str] = Field(description="需澄清问题列表")


class MatchClausesResponse(BaseModel):
    sections: list[MatchedSection] = Field(description="章节与条款匹配结果")


class MatchClausesRequest(BaseModel):
    selected_clause_ids: list[str] = Field(default_factory=list, description="人工指定条款 ID")
    operator_id: str = Field(default="system", description="操作人")

    model_config = ConfigDict(json_schema_extra={"example": {"selected_clause_ids": [], "operator_id": "buyer_001"}})


class ValidateRequest(BaseModel):
    selected_clause_ids: list[str] = Field(default_factory=list, description="人工指定条款 ID")
    operator_id: str = Field(default="system", description="操作人")

    model_config = ConfigDict(json_schema_extra={"example": {"selected_clause_ids": [], "operator_id": "buyer_001"}})


class ValidateResponse(BaseModel):
    risk_summary: list[RiskItem] = Field(description="风险项列表")
    can_export_formal: bool = Field(description="是否允许正式版导出")


class RenderRequest(BaseModel):
    selected_clause_ids: list[str] = Field(default_factory=list, description="人工指定条款 ID")
    operator_id: str = Field(default="system", description="操作人")

    model_config = ConfigDict(json_schema_extra={"example": {"selected_clause_ids": [], "operator_id": "buyer_001"}})


class RenderResponse(BaseModel):
    doc_version_id: str = Field(description="文档版本 ID")
    preview_html: str = Field(description="HTML 预览内容")


class ExportRequest(BaseModel):
    format: str = Field(description="导出格式，支持 docx 或 pdf")
    mode: str = Field(description="导出模式，支持 draft 或 formal")
    selected_clause_ids: list[str] = Field(default_factory=list, description="人工指定条款 ID")
    operator_id: str = Field(default="system", description="操作人")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "format": "pdf",
                "mode": "formal",
                "selected_clause_ids": [],
                "operator_id": "buyer_001",
            }
        }
    )


class ExportResponse(BaseModel):
    file_url: str = Field(description="可下载文件 URL")


class ProjectResponse(BaseModel):
    project: Project = Field(description="项目详情")


class GenerateDocumentRequest(BaseModel):
    project_name: str = Field(min_length=1, description="项目名称")
    department: str = Field(min_length=1, description="采购部门")
    raw_input_text: str = Field(min_length=1, description="采购需求自然语言文本")
    format: str = Field(default="docx", description="导出格式，docx/pdf")
    mode: str = Field(default="draft", description="导出模式，draft/formal")
    created_by: str = Field(default="system", description="创建人")
    operator_id: str = Field(default="system", description="操作人")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_name": "服务器采购项目",
                "department": "信息部",
                "raw_input_text": (
                    "服务器采购项目，预算300万元，45天交付，付款30/60/10，"
                    "验收按国家标准执行，质保24个月。"
                ),
                "format": "pdf",
                "mode": "formal",
                "created_by": "buyer_001",
                "operator_id": "buyer_001",
            }
        }
    )


class GenerateDocumentResponse(BaseModel):
    project_id: str = Field(description="项目 ID")
    missing_fields: list[str] = Field(description="缺失字段列表")
    clarification_questions: list[str] = Field(description="需澄清问题列表")
    risk_summary: list[RiskItem] = Field(description="风险项列表")
    can_export_formal: bool = Field(description="是否允许正式版导出")
    preview_html: str = Field(description="HTML 预览内容")
    file_url: str | None = Field(default=None, description="最终可下载文件 URL")
    export_blocked: bool = Field(default=False, description="是否触发正式版拦截")
    delivered_mode: str = Field(default="draft", description="实际导出模式")
    message: str = Field(default="", description="补充说明")
