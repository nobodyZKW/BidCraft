from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import MatchedSection, Project, RiskItem


class CreateProjectRequest(BaseModel):
    project_name: str = Field(min_length=1, description="椤圭洰鍚嶇О")
    department: str = Field(min_length=1, description="閲囪喘閮ㄩ棬")
    created_by: str = Field(default="system", description="鍒涘缓浜?)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_name": "鏈嶅姟鍣ㄩ噰璐」鐩?,
                "department": "淇℃伅閮?,
                "created_by": "buyer_001",
            }
        }
    )


class CreateProjectResponse(BaseModel):
    project_id: str = Field(description="椤圭洰 ID")


class ExtractRequest(BaseModel):
    raw_input_text: str = Field(min_length=1, description="閲囪喘闇€姹傝嚜鐒惰瑷€鏂囨湰")
    operator_id: str = Field(default="system", description="鎿嶄綔浜?)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "raw_input_text": (
                    "鏈嶅姟鍣ㄩ噰璐」鐩紝棰勭畻300涓囧厓锛?5澶╀氦浠橈紝浠樻30/60/10锛?
                    "楠屾敹鎸夊浗瀹舵爣鍑嗘墽琛岋紝璐ㄤ繚24涓湀銆?
                ),
                "operator_id": "buyer_001",
            }
        }
    )


class ExtractResponse(BaseModel):
    structured_data: dict = Field(description="缁撴瀯鍖栨娊鍙栫粨鏋?)
    missing_fields: list[str] = Field(description="缂哄け瀛楁鍒楄〃")
    clarification_questions: list[str] = Field(description="闇€婢勬竻闂鍒楄〃")


class MatchClausesResponse(BaseModel):
    sections: list[MatchedSection] = Field(description="绔犺妭涓庢潯娆惧尮閰嶇粨鏋?)


class MatchClausesRequest(BaseModel):
    selected_clause_ids: list[str] = Field(default_factory=list, description="浜哄伐鎸囧畾鏉℃ ID")
    operator_id: str = Field(default="system", description="鎿嶄綔浜?)

    model_config = ConfigDict(json_schema_extra={"example": {"selected_clause_ids": [], "operator_id": "buyer_001"}})


class ValidateRequest(BaseModel):
    selected_clause_ids: list[str] = Field(default_factory=list, description="浜哄伐鎸囧畾鏉℃ ID")
    operator_id: str = Field(default="system", description="鎿嶄綔浜?)

    model_config = ConfigDict(json_schema_extra={"example": {"selected_clause_ids": [], "operator_id": "buyer_001"}})


class ValidateResponse(BaseModel):
    risk_summary: list[RiskItem] = Field(description="椋庨櫓椤瑰垪琛?)
    can_export_formal: bool = Field(description="鏄惁鍏佽姝ｅ紡鐗堝鍑?)


class RenderRequest(BaseModel):
    selected_clause_ids: list[str] = Field(default_factory=list, description="浜哄伐鎸囧畾鏉℃ ID")
    operator_id: str = Field(default="system", description="鎿嶄綔浜?)

    model_config = ConfigDict(json_schema_extra={"example": {"selected_clause_ids": [], "operator_id": "buyer_001"}})


class RenderResponse(BaseModel):
    doc_version_id: str = Field(description="鏂囨。鐗堟湰 ID")
    preview_html: str = Field(description="HTML 棰勮鍐呭")


class ExportRequest(BaseModel):
    format: str = Field(description="瀵煎嚭鏍煎紡锛屾敮鎸?docx 鎴?pdf")
    mode: str = Field(description="瀵煎嚭妯″紡锛屾敮鎸?draft 鎴?formal")
    selected_clause_ids: list[str] = Field(default_factory=list, description="浜哄伐鎸囧畾鏉℃ ID")
    operator_id: str = Field(default="system", description="鎿嶄綔浜?)

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
    file_url: str = Field(description="鍙笅杞芥枃浠?URL")


class ProjectResponse(BaseModel):
    project: Project = Field(description="椤圭洰璇︽儏")


class GenerateDocumentRequest(BaseModel):
    project_name: str = Field(min_length=1, description="椤圭洰鍚嶇О")
    department: str = Field(min_length=1, description="閲囪喘閮ㄩ棬")
    raw_input_text: str = Field(min_length=1, description="閲囪喘闇€姹傝嚜鐒惰瑷€鏂囨湰")
    format: str = Field(default="docx", description="瀵煎嚭鏍煎紡锛宒ocx/pdf")
    mode: str = Field(default="draft", description="瀵煎嚭妯″紡锛宒raft/formal")
    created_by: str = Field(default="system", description="鍒涘缓浜?)
    operator_id: str = Field(default="system", description="鎿嶄綔浜?)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_name": "鏈嶅姟鍣ㄩ噰璐」鐩?,
                "department": "淇℃伅閮?,
                "raw_input_text": (
                    "鏈嶅姟鍣ㄩ噰璐」鐩紝棰勭畻300涓囧厓锛?5澶╀氦浠橈紝浠樻30/60/10锛?
                    "楠屾敹鎸夊浗瀹舵爣鍑嗘墽琛岋紝璐ㄤ繚24涓湀銆?
                ),
                "format": "pdf",
                "mode": "formal",
                "created_by": "buyer_001",
                "operator_id": "buyer_001",
            }
        }
    )


class GenerateDocumentResponse(BaseModel):
    project_id: str = Field(description="椤圭洰 ID")
    missing_fields: list[str] = Field(description="缂哄け瀛楁鍒楄〃")
    clarification_questions: list[str] = Field(description="闇€婢勬竻闂鍒楄〃")
    risk_summary: list[RiskItem] = Field(description="椋庨櫓椤瑰垪琛?)
    can_export_formal: bool = Field(description="鏄惁鍏佽姝ｅ紡鐗堝鍑?)
    preview_html: str = Field(description="HTML 棰勮鍐呭")
    file_url: str | None = Field(default=None, description="鏈€缁堝彲涓嬭浇鏂囦欢 URL")
    export_blocked: bool = Field(default=False, description="鏄惁瑙﹀彂姝ｅ紡鐗堟嫤鎴?)
    delivered_mode: str = Field(default="draft", description="瀹為檯瀵煎嚭妯″紡")
    message: str = Field(default="", description="琛ュ厖璇存槑")
    tool_calls: list[str] = Field(default_factory=list, description="调用的 tool 列表")


