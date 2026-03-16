from __future__ import annotations


INTENT_PARSE_PROMPT = (
    "识别用户意图并映射到固定枚举："
    "view_missing_fields / override_payment_clause / formal_export / draft_export / generate_document"
)

CLARIFICATION_PROMPT_TEMPLATE = (
    "检测到缺失字段，请先补充后继续。"
    "可补充后再次调用 continue 接口推进流程。"
)

FIX_PLAN_PROMPT_TEMPLATE = (
    "检测到高风险，需先处理阻断项。"
    "你可以选择修复方案后继续，或在允许时降级导出草稿。"
)

CONFIRM_EXPORT_PROMPT_TEMPLATE = (
    "即将执行正式版导出，请确认是否继续。"
)

DEFAULT_RESPONSE_TEMPLATE = (
    "流程已执行到 {current_step}。下一步建议: {next_action}。"
)

