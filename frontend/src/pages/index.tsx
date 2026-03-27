import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  AgentArtifacts,
  AgentChatResponse,
  AgentOption,
  BASE_URL,
  KnowledgeCitation,
  MatchedSection,
  agentChat,
  continueAgentProject,
} from "../services/api";
import styles from "./index.module.css";

type ChatRole = "user" | "assistant";

type ChatMessage = {
  role: ChatRole;
  content: string;
  timestamp: number;
};

type PauseKind =
  | "none"
  | "clarification"
  | "confirm_export"
  | "override_clause"
  | "fix_plan"
  | "generic";

type ClarificationItem = {
  field: string;
  question: string;
};

type StepId =
  | "project"
  | "extract"
  | "clarification"
  | "clause_match"
  | "validate"
  | "risk_fix"
  | "deliver"
  | "render"
  | "confirm_export"
  | "export";

type StepDef = {
  id: StepId;
  label: string;
  hint: string;
  tools: string[];
  nodes: string[];
};

const DEFAULT_MESSAGE =
  "请帮我生成货物类公开招标文件，预算 300 万元，交付周期 45 天，付款条款 30/60/10，验收方式为测试报告，质保 24 个月。";

const STEP_DEFS: StepDef[] = [
  {
    id: "project",
    label: "建立上下文",
    hint: "识别意图并创建本次会话项目。",
    tools: ["project_tools.ensure_project"],
    nodes: ["understand_intent", "ensure_project"],
  },
  {
    id: "extract",
    label: "需求抽取",
    hint: "把自然语言整理为结构化采购字段。",
    tools: ["extraction_tools.extract_requirements"],
    nodes: ["extract_requirements"],
  },
  {
    id: "clarification",
    label: "澄清补全",
    hint: "如果信息不足，在这里补充并重新审核。",
    tools: [
      "clarification_tools.ask_for_clarification",
      "clarification_tools.review_clarification",
      "extraction_tools.merge_clarifications",
    ],
    nodes: [
      "decide_need_clarification",
      "ask_for_clarification",
      "merge_clarifications",
    ],
  },
  {
    id: "clause_match",
    label: "条款匹配",
    hint: "匹配付款、验收、责任等模板条款。",
    tools: [
      "clause_tools.match_or_override",
      "clause_tools.list_clause_alternatives",
    ],
    nodes: ["match_clauses"],
  },
  {
    id: "validate",
    label: "规则校验",
    hint: "检查风险项并判断是否允许正式导出。",
    tools: ["validation_tools.validate_document"],
    nodes: ["validate_document"],
  },
  {
    id: "risk_fix",
    label: "风险处理",
    hint: "给出修复建议，或按草稿版继续。",
    tools: [
      "validation_tools.build_fix_options",
      "validation_tools.auto_repair_with_pe",
    ],
    nodes: [
      "decide_repair_or_continue",
      "build_fix_options",
      "auto_repair_with_pe",
    ],
  },
  {
    id: "render",
    label: "预览生成",
    hint: "生成文档预览，便于人工审查。",
    tools: ["render_tools.render_preview"],
    nodes: ["render_preview"],
  },
  {
    id: "confirm_export",
    label: "导出确认",
    hint: "正式导出前再次确认。",
    tools: [
      "clarification_tools.confirm_export.pending",
      "clarification_tools.confirm_export.accept",
      "clarification_tools.confirm_export.reject",
    ],
    nodes: ["confirm_export"],
  },
  {
    id: "export",
    label: "文件导出",
    hint: "输出草稿版或正式版文件。",
    tools: ["export_tools.export_document"],
    nodes: ["export_document"],
  },
];

const DISPLAY_STEP_DEFS: StepDef[] = [
  ...STEP_DEFS.filter(
    (step) =>
      step.id !== "render" && step.id !== "confirm_export" && step.id !== "export"
  ),
  {
    id: "deliver",
    label: "预览与导出",
    hint: "在同一个步骤中完成预览生成、导出确认和文件导出。",
    tools: [
      "render_tools.render_preview",
      "clarification_tools.confirm_export.pending",
      "clarification_tools.confirm_export.accept",
      "clarification_tools.confirm_export.reject",
      "export_tools.export_document",
    ],
    nodes: ["render_preview", "confirm_export", "export_document"],
  },
];

function normalizeStepId(stepId: StepId | null): StepId | null {
  if (stepId === "render" || stepId === "confirm_export" || stepId === "export") {
    return "deliver";
  }
  return stepId;
}

const STEP_CLICK_COMMANDS: Record<StepId, { userText: string; message: string }> = {
  project: { userText: "开始新的审查流程", message: "start workflow" },
  extract: { userText: "重新抽取需求", message: "please extract requirements again" },
  clarification: {
    userText: "查看需要补充的信息",
    message: "show missing fields only",
  },
  clause_match: { userText: "检查条款匹配", message: "replace payment clause" },
  validate: { userText: "重新执行规则校验", message: "validate document again" },
  risk_fix: {
    userText: "生成风险修复建议",
    message: "build fix options for high risks",
  },
  deliver: { userText: "生成预览并准备导出", message: "render preview" },
  render: { userText: "生成文档预览", message: "render preview" },
  confirm_export: { userText: "进入导出确认", message: "formal export" },
  export: { userText: "导出草稿文件", message: "draft export" },
};

function createSessionId(): string {
  return `session_${Date.now().toString(36)}_${Math.random()
    .toString(36)
    .slice(2, 10)}`;
}

function getLastToolCall(payload: AgentChatResponse | null): string {
  if (!payload || payload.tool_calls.length === 0) return "";
  return payload.tool_calls[payload.tool_calls.length - 1];
}

function inferPauseKind(payload: AgentChatResponse | null): PauseKind {
  if (!payload || !payload.requires_user_input) return "none";
  const lastToolCall = getLastToolCall(payload);
  if (lastToolCall.includes("clarification_tools.confirm_export.pending")) {
    return "confirm_export";
  }
  if (
    lastToolCall.includes("clarification_tools.ask_for_clarification") ||
    lastToolCall.includes("clarification_tools.review_clarification")
  ) {
    return "clarification";
  }
  if (lastToolCall.includes("clause_tools.list_clause_alternatives")) {
    return "override_clause";
  }
  if (lastToolCall.includes("validation_tools.build_fix_options")) {
    return "fix_plan";
  }
  return "generic";
}

function toClarificationItems(options: AgentOption[]): ClarificationItem[] {
  return options
    .map((option) => {
      const field = typeof option.field === "string" ? option.field : "";
      const question =
        typeof option.question === "string" && option.question.trim()
          ? option.question
          : `请补充字段：${field}`;
      return field ? { field, question } : null;
    })
    .filter((item): item is ClarificationItem => item !== null);
}

function clarificationItemsFromArtifacts(
  artifacts: AgentArtifacts
): ClarificationItem[] {
  const fields = artifacts.missing_fields ?? [];
  const questions = artifacts.clarification_questions ?? [];
  return fields.map((field, index) => ({
    field,
    question: questions[index] || `请补充字段：${field}`,
  }));
}

function clarificationItemsFromMessage(message: string): ClarificationItem[] {
  const errors = parseClarificationErrors(message);
  const fields = [
    ...new Set(
      errors
        .map((errorText) => detectFieldFromError(errorText))
        .filter((field): field is string => Boolean(field))
    ),
  ];
  return fields.map((field) => ({
    field,
    question: `请重新补充字段：${field}`,
  }));
}

function optionText(option: AgentOption): string {
  if (typeof option.text === "string" && option.text.trim()) return option.text;
  if (typeof option.question === "string" && option.question.trim()) {
    return option.question;
  }
  if (typeof option.field === "string" && option.field.trim()) return option.field;
  if (typeof option.id === "string" && option.id.trim()) return option.id;
  if (typeof option.id === "number") return String(option.id);
  return "继续";
}

const FIELD_EXAMPLES: Record<string, string[]> = {
  acceptance_standard: [
    "按测试报告验收",
    "按技术规格书和测试报告验收",
  ],
  warranty_months: ["24", "36"],
  payment_terms: ["30/60/10", "合同签订后30%，验收合格后60%，质保期满后10%"],
  delivery_days: ["45", "30"],
  budget_amount: ["300万元", "3000000"],
};

function parseClarificationErrors(message: string): string[] {
  const marker = "Reason:";
  const index = message.indexOf(marker);
  const detail = index >= 0 ? message.slice(index + marker.length).trim() : message.trim();
  return detail
    .split(/;\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function detectFieldFromError(errorText: string): string | null {
  for (const field of Object.keys(FIELD_EXAMPLES)) {
    if (errorText.includes(field)) return field;
  }
  return null;
}

function buildFieldHint(field: string): string {
  switch (field) {
    case "acceptance_standard":
      return "需要写清按什么标准验收，不能只写模糊时间描述。";
    case "warranty_months":
      return "建议填写纯数字月数，例如 24 或 36。";
    case "payment_terms":
      return "建议写完整付款安排，不要只写单笔预付款。";
    case "delivery_days":
      return "建议填写明确天数，例如 30 或 45。";
    case "budget_amount":
      return "建议填写明确预算金额。";
    default:
      return "请补充更明确、可直接落到文件里的值。";
  }
}

function buildClarificationCoachMessageLegacy(payload: AgentChatResponse): string | null {
  const isRejected = payload.tool_calls.some((toolCall) =>
    toolCall.startsWith("clarification_tools.review_clarification.reject")
  );
  if (!isRejected || !payload.assistant_message) return null;

  const errors = parseClarificationErrors(payload.assistant_message);
  const lines = ["这次澄清还不能直接用于生成文件，我帮你拆一下问题："];

  for (const errorText of errors) {
    const field = detectFieldFromError(errorText);
    if (!field) {
      lines.push(`- ${errorText}`);
      continue;
    }
    lines.push(`- ${field}：${buildFieldHint(field)}`);
    const examples = FIELD_EXAMPLES[field];
    if (examples?.length) {
      lines.push(`  建议示例：${examples.join(" / ")}`);
    }
  }

  const suggestions = toClarificationItems(payload.options)
    .map((item) => {
      const example = FIELD_EXAMPLES[item.field]?.[0];
      return example ? `${item.field}=${example}` : null;
    })
    .filter((item): item is string => Boolean(item));

  if (suggestions.length > 0) {
    lines.push("");
    lines.push("你可以直接这样补充：");
    lines.push(...suggestions.map((item) => `- ${item}`));
  }

  return lines.join("\n");
}

function formatAssistantMessage(payload: AgentChatResponse): string {
  return buildClarificationCoachMessage(payload) ?? payload.assistant_message;
}

function buildClarificationCoachMessage(payload: AgentChatResponse): string | null {
  const isClarificationTurn =
    payload.requires_user_input && inferPauseKind(payload) === "clarification";
  if (!isClarificationTurn) return null;

  const errors = parseClarificationErrors(payload.assistant_message);
  const lines = ["这一步需要把字段补充成系统可直接落到文件里的写法。"];

  if (errors.length > 0 && payload.assistant_message.includes("Reason:")) {
    lines.push("当前主要问题：");
    for (const errorText of errors) {
      const field = detectFieldFromError(errorText);
      if (field) {
        lines.push(`- ${field}：${buildFieldHint(field)}`);
      } else {
        lines.push(`- ${errorText}`);
      }
    }
  } else {
    lines.push("当前还缺少关键字段，建议按下面的示例直接填写。");
  }

  const suggestions = toClarificationItems(payload.options)
    .map((item) => {
      const example = FIELD_EXAMPLES[item.field]?.[0];
      return example ? `${item.field}=${example}` : null;
    })
    .filter((item): item is string => Boolean(item));

  if (suggestions.length > 0) {
    lines.push("可直接参考：");
    lines.push(...suggestions.map((item) => `- ${item}`));
  }

  return lines.join("\n");
}

function parseInlineClarifications(
  text: string,
  allowedFields: string[]
): Record<string, string> {
  const normalizedText = text
    .replace(/^补充澄清[:：]?\s*/i, "")
    .replace(/^澄清[:：]?\s*/i, "")
    .trim();
  if (!normalizedText) return {};

  const allowed = new Set(allowedFields);
  const entries = normalizedText
    .split(/[;\n；]+/)
    .map((item) => item.trim())
    .filter(Boolean);

  const parsed: Record<string, string> = {};
  for (const entry of entries) {
    const match = entry.match(/^([a-zA-Z_][a-zA-Z0-9_]*)\s*[:=：]\s*(.+)$/);
    if (!match) continue;
    const field = match[1].trim();
    const value = match[2].trim();
    if (!value) continue;
    if (allowed.size > 0 && !allowed.has(field)) continue;
    parsed[field] = value;
  }
  return parsed;
}

function resolveExportFileUrl(artifacts: AgentArtifacts): string | null {
  if (typeof artifacts.file_url === "string" && artifacts.file_url.trim()) {
    return artifacts.file_url;
  }
  const filePath = artifacts.file_path;
  if (!filePath || typeof filePath !== "string") return null;
  const normalized = filePath.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  if (parts.length === 0) return null;
  const filename = encodeURIComponent(parts[parts.length - 1]);
  return `${BASE_URL.replace(/\/$/, "")}/exports/${filename}`;
}

function stepHasToolCall(payload: AgentChatResponse | null, step: StepDef): boolean {
  if (!payload) return false;
  return payload.tool_calls.some((toolCall) =>
    step.tools.some((tool) => toolCall.startsWith(tool))
  );
}

function findStepByNode(node: string): StepId | null {
  if (!node || node === "respond" || node === "done" || node === "init") {
    return null;
  }
  return normalizeStepId(
    STEP_DEFS.find((step) => step.nodes.includes(node as StepId))?.id ?? null
  );
}

function getLastTouchedStepId(payload: AgentChatResponse | null): StepId | null {
  if (!payload) return null;
  for (let index = payload.tool_calls.length - 1; index >= 0; index -= 1) {
    const toolCall = payload.tool_calls[index];
    const step = STEP_DEFS.find((item) =>
      item.tools.some((tool) => toolCall.startsWith(tool))
    );
    if (step) return normalizeStepId(step.id);
  }
  return null;
}

function getActiveStepId(
  payload: AgentChatResponse | null,
  pauseKind: PauseKind
): StepId | null {
  if (!payload) return null;
  if (payload.requires_user_input) {
    if (pauseKind === "clarification") return "clarification";
    if (pauseKind === "confirm_export") return "deliver";
    if (pauseKind === "override_clause") return "clause_match";
    if (pauseKind === "fix_plan") return "risk_fix";
  }
  return normalizeStepId(
    findStepByNode(payload.current_step) ??
    findStepByNode(payload.next_action) ??
    getLastTouchedStepId(payload)
  );
}

function getStepState(
  step: StepDef,
  payload: AgentChatResponse | null,
  activeStepId: StepId | null
): "active" | "done" | "upcoming" {
  if (activeStepId === step.id) return "active";
  if (stepHasToolCall(payload, step)) return "done";
  return "upcoming";
}

function severityCount(
  artifacts: AgentArtifacts,
  severity: "high" | "medium" | "low"
): number {
  return (artifacts.risk_summary ?? []).filter(
    (item) => item.severity === severity
  ).length;
}

function citationsOf(
  value: { citations?: KnowledgeCitation[] } | null | undefined
): KnowledgeCitation[] {
  return value?.citations ?? [];
}

export default function Home() {
  const [sessionId, setSessionId] = useState<string>("pending");
  const [projectId, setProjectId] = useState<string | null>(null);
  const [inputMessage, setInputMessage] = useState<string>(DEFAULT_MESSAGE);
  const [continueMessage, setContinueMessage] = useState<string>("");
  const [clarificationValues, setClarificationValues] = useState<
    Record<string, string>
  >({});
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [result, setResult] = useState<AgentChatResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const chatListRef = useRef<HTMLDivElement | null>(null);

  const pauseKind = inferPauseKind(result);
  const clarificationItems = useMemo(() => {
    if (pauseKind !== "clarification" || !result) return [];
    const fromOptions = toClarificationItems(result.options);
    if (fromOptions.length > 0) return fromOptions;
    const fromArtifacts = clarificationItemsFromArtifacts(result.artifacts ?? {});
    if (fromArtifacts.length > 0) return fromArtifacts;
    return clarificationItemsFromMessage(result.assistant_message ?? "");
  }, [pauseKind, result]);
  const clarificationCoachMessage = useMemo(
    () => (result && pauseKind === "clarification" ? buildClarificationCoachMessage(result) : null),
    [pauseKind, result]
  );
  const activeStepId = useMemo(
    () => getActiveStepId(result, pauseKind),
    [pauseKind, result]
  );

  const artifacts = result?.artifacts ?? {};
  const exportFileUrl = resolveExportFileUrl(artifacts);
  const highRiskCount = severityCount(artifacts, "high");
  const mediumRiskCount = severityCount(artifacts, "medium");
  const lowRiskCount = severityCount(artifacts, "low");
  const matchedSections = (artifacts.matched_sections ?? []) as MatchedSection[];
  const traceEntries = artifacts.trace ?? [];
  const traceSummary = artifacts.trace_summary;

  useEffect(() => {
    setSessionId(createSessionId());
  }, []);

  useEffect(() => {
    const element = chatListRef.current;
    if (!element) return;
    element.scrollTo({ top: element.scrollHeight, behavior: "smooth" });
  }, [messages, loading, error, result?.assistant_message]);

  async function submitTurn(params: {
    userText: string;
    message?: string;
    userClarifications?: Record<string, unknown>;
  }): Promise<void> {
    const userText = params.userText.trim();
    const message = (params.message ?? userText).trim();
    if (!projectId && !message) {
      setError("请输入内容后再发送。");
      return;
    }

    setLoading(true);
    setError("");
    if (userText) {
      const userMessage: ChatMessage = {
        role: "user",
        content: userText,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMessage]);
    }
    try {
      const effectiveSessionId =
        sessionId === "pending" ? createSessionId() : sessionId;
      if (sessionId === "pending") setSessionId(effectiveSessionId);

      const payload = projectId
        ? await continueAgentProject(projectId, {
            message,
            user_clarifications: params.userClarifications ?? {},
          })
        : await agentChat({
            message,
            session_id: effectiveSessionId,
            user_clarifications: params.userClarifications ?? {},
          });

      if (payload.project_id) setProjectId(payload.project_id);
      setResult(payload);
      setMessages((prev) => {
        const next = [...prev];
        if (payload.assistant_message) {
          next.push({
            role: "assistant",
            content: formatAssistantMessage(payload),
            timestamp: Date.now(),
          });
        }
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }

  async function onSendMessage(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const message = inputMessage.trim();
    if (!message) return;
    setInputMessage("");
    if (projectId && pauseKind === "clarification") {
      const parsedClarifications = parseInlineClarifications(
        message,
        clarificationItems.map((item) => item.field)
      );
      if (Object.keys(parsedClarifications).length > 0) {
        await submitTurn({
          userText: message,
          message: `update fields -> ${Object.entries(parsedClarifications)
            .map(([field, value]) => `${field}=${value}`)
            .join("; ")}`,
          userClarifications: parsedClarifications,
        });
        return;
      }
    }
    await submitTurn({ userText: message });
  }

  async function onContinueWithText(
    event: FormEvent<HTMLFormElement>
  ): Promise<void> {
    event.preventDefault();
    if (!projectId) return;
    const text = continueMessage.trim();
    setContinueMessage("");
    if (pauseKind === "clarification") {
      const parsedClarifications = parseInlineClarifications(
        text,
        clarificationItems.map((item) => item.field)
      );
      if (Object.keys(parsedClarifications).length > 0) {
        await submitTurn({
          userText: text,
          message: `update fields -> ${Object.entries(parsedClarifications)
            .map(([field, value]) => `${field}=${value}`)
            .join("; ")}`,
          userClarifications: parsedClarifications,
        });
        return;
      }
    }
    await submitTurn({ userText: text || "继续流程", message: text });
  }

  async function onSubmitClarifications(
    event: FormEvent<HTMLFormElement>
  ): Promise<void> {
    event.preventDefault();
    if (!projectId) return;
    const payload: Record<string, string> = {};
    for (const item of clarificationItems) {
      const value = (clarificationValues[item.field] ?? "").trim();
      if (value) payload[item.field] = value;
    }
    if (Object.keys(payload).length === 0) {
      setError("请至少填写一个需要补充的字段。");
      return;
    }
    const clarificationText = Object.entries(payload)
      .map(([field, value]) => `${field}=${value}`)
      .join("; ");
    await submitTurn({
      userText: `补充澄清：${clarificationText}`,
      message: `update fields -> ${clarificationText}`,
      userClarifications: payload,
    });
  }

  async function onSelectOption(option: AgentOption): Promise<void> {
    if (!projectId || !result) return;
    const label = optionText(option);
    const idValue =
      typeof option.id === "string" || typeof option.id === "number"
        ? String(option.id)
        : label;

    if (pauseKind === "confirm_export") {
      const confirmed = idValue === "confirm";
      await submitTurn({
        userText: confirmed ? "确认正式导出" : "取消正式导出",
        message: confirmed ? "confirm formal export" : "cancel formal export",
        userClarifications: { confirmed_export: confirmed },
      });
      return;
    }

    if (pauseKind === "override_clause") {
      await submitTurn({
        userText: `选择条款：${idValue}`,
        message: `override clause ${idValue}`,
        userClarifications: { override_clause_id: idValue },
      });
      return;
    }

    await submitTurn({
      userText: `选择：${label}`,
      message: label,
    });
  }

  async function onAllowDraftContinue(): Promise<void> {
    if (!projectId) return;
    await submitTurn({
      userText: "允许降级为草稿版继续",
      message: "allow draft and continue",
      userClarifications: { allow_draft: true },
    });
  }

  async function onAutoRepairWithPe(): Promise<void> {
    if (!projectId) return;
    await submitTurn({
      userText: "执行一次自动修复",
      message: "auto repair with pe once",
      userClarifications: { auto_repair_with_pe: true },
    });
  }

  async function onExportDraft(): Promise<void> {
    if (!projectId) return;
    await submitTurn({
      userText: "导出草稿文件",
      message: "draft export",
    });
  }

  async function onExportFormal(): Promise<void> {
    if (!projectId) return;
    await submitTurn({
      userText: "正式导出文件",
      message: "formal export",
    });
  }

  function onResetSession(): void {
    setSessionId(createSessionId());
    setProjectId(null);
    setInputMessage(DEFAULT_MESSAGE);
    setContinueMessage("");
    setClarificationValues({});
    setMessages([]);
    setResult(null);
    setError("");
  }

  async function onStepClick(stepId: StepId): Promise<void> {
    if (loading) return;
    const nextCommand = STEP_CLICK_COMMANDS[stepId] ?? STEP_CLICK_COMMANDS.deliver;
    await submitTurn({
      userText: nextCommand.userText,
      message: nextCommand.message,
    });
    return;
    /*
    const commandByStep: Record<StepId, { userText: string; message: string }> = {
      project: { userText: "开始新的审查流程", message: "start workflow" },
      extract: { userText: "重新抽取需求", message: "please extract requirements again" },
      clarification: {
        userText: "查看需要补充的信息",
        message: "show missing fields only",
      },
      clause_match: { userText: "检查条款匹配", message: "replace payment clause" },
      validate: { userText: "重新执行规则校验", message: "validate document again" },
      risk_fix: {
        userText: "生成风险修复建议",
        message: "build fix options for high risks",
      },
      render: { userText: "生成文档预览", message: "render preview" },
      confirm_export: { userText: "进入导出确认", message: "formal export" },
      export: { userText: "导出草稿文件", message: "draft export" },
    };

      deliver: { userText: "生成预览并准备导出", message: "render preview" },
    const command = commandByStep[stepId];
    await submitTurn({ userText: command.userText, message: command.message });
    */
  }

  const pauseTitle =
    pauseKind === "clarification"
      ? "请补充澄清信息"
      : pauseKind === "confirm_export"
      ? "请确认是否正式导出"
      : pauseKind === "override_clause"
      ? "请确认条款替换"
      : pauseKind === "fix_plan"
      ? "请决定风险处理方式"
      : "请继续本轮审查";

  const pauseDescription =
    pauseKind === "clarification"
      ? "把缺失字段补完整后，系统会继续审核并刷新结果。"
      : pauseKind === "confirm_export"
      ? "确认后会继续正式导出；取消则回到会话审查。"
      : pauseKind === "override_clause"
      ? "你可以在这里人工选择更合适的条款版本。"
      : pauseKind === "fix_plan"
      ? "当前存在风险项，请选择修复方案或改为草稿导出。"
      : "系统在等待你的下一步操作。";

  return (
    <main className={styles.page}>
      <div className={styles.workspace}>
        <aside className={styles.sidebar}>
          <section className={styles.brandCard}>
            <span className={styles.brandEyebrow}>BidCraft AI Workspace</span>
            <h1>招标文件审查工作台</h1>
            <p>左侧跟踪流程、风险和依据，右侧用对话完成补充、审查和修改。</p>
            <div className={styles.summaryGrid}>
              <div className={styles.summaryCard}>
                <span>当前节点</span>
                <strong>{activeStepId ?? "待开始"}</strong>
              </div>
              <div className={styles.summaryCard}>
                <span>项目编号</span>
                <strong>{projectId ?? "未创建"}</strong>
              </div>
              <div className={styles.summaryCard}>
                <span>高风险</span>
                <strong>{highRiskCount}</strong>
              </div>
              <div className={styles.summaryCard}>
                <span>缺失字段</span>
                <strong>{artifacts.missing_fields?.length ?? 0}</strong>
              </div>
            </div>
            <div className={styles.brandActions}>
              <button
                type="button"
                className={styles.primaryButton}
                onClick={onResetSession}
                disabled={loading}
              >
                新建会话
              </button>
              <a
                href="http://127.0.0.1:8000/docs"
                target="_blank"
                rel="noreferrer"
                className={styles.ghostLink}
              >
                打开 API 文档
              </a>
            </div>
          </section>

          <section className={styles.sidebarPanel}>
            <div className={styles.panelHeading}>
              <div>
                <h2>流程导航</h2>
                <p>像 AI 工作流一样显示进度，你也可以直接点击节点继续。</p>
              </div>
            </div>
            <div className={styles.stepList}>
              {DISPLAY_STEP_DEFS.map((step, index) => {
                const state = getStepState(step, result, activeStepId);
                return (
                  <button
                    key={step.id}
                    type="button"
                    className={[
                      styles.stepCard,
                      state === "active" ? styles.stepCardActive : "",
                      state === "done" ? styles.stepCardDone : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    onClick={() => void onStepClick(step.id)}
                    disabled={loading}
                  >
                    <span className={styles.stepIndex}>
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div className={styles.stepBody}>
                      <div className={styles.stepHeader}>
                        <strong>{step.label}</strong>
                        <span
                          className={
                            state === "active"
                              ? styles.badgeActive
                              : state === "done"
                              ? styles.badgeDone
                              : styles.badgeUpcoming
                          }
                        >
                          {state === "active"
                            ? "当前"
                            : state === "done"
                            ? "已完成"
                            : "待执行"}
                        </span>
                      </div>
                      <p>{step.hint}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          <section className={styles.sidebarPanel}>
            <div className={styles.panelHeading}>
              <div>
                <h2>摘要与依据</h2>
                <p>风险、条款依据、运行轨迹都集中在这一列里。</p>
              </div>
            </div>

            <div className={styles.metricGrid}>
              <div className={styles.metricCard}>
                <span>高风险</span>
                <strong>{highRiskCount}</strong>
              </div>
              <div className={styles.metricCard}>
                <span>中风险</span>
                <strong>{mediumRiskCount}</strong>
              </div>
              <div className={styles.metricCard}>
                <span>低风险</span>
                <strong>{lowRiskCount}</strong>
              </div>
              <div className={styles.metricCard}>
                <span>正式导出</span>
                <strong>{String(artifacts.can_export_formal ?? false)}</strong>
              </div>
            </div>

            {traceSummary ? (
              <div className={styles.traceMeta}>
                <span>trace {traceSummary.trace_count}</span>
                <span>LLM {traceSummary.llm_decision_count}</span>
                <span>工具 {traceSummary.tool_call_count}</span>
                <span>{traceSummary.duration_ms} ms</span>
              </div>
            ) : null}

            {exportFileUrl ? (
              <a
                href={exportFileUrl}
                target="_blank"
                rel="noreferrer"
                className={styles.downloadButton}
              >
                下载当前导出文件
              </a>
            ) : null}

            {(artifacts.missing_fields ?? []).length > 0 ? (
              <div className={styles.infoBlock}>
                <h3>待补字段</h3>
                <ul className={styles.tagList}>
                  {(artifacts.missing_fields ?? []).map((field) => (
                    <li key={field}>{field}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {matchedSections.length > 0 ? (
              <div className={styles.infoBlock}>
                <h3>条款依据</h3>
                <div className={styles.cardStack}>
                  {matchedSections.map((section) => (
                    <article
                      key={`${section.section_id}_${section.selected_clause_id}`}
                      className={styles.infoCard}
                    >
                      <div className={styles.infoCardHeader}>
                        <strong>{section.section_id}</strong>
                        <span>{section.selected_clause_id}</span>
                      </div>
                      <p>{section.reason}</p>
                      {section.alternatives.length > 0 ? (
                        <small>候选：{section.alternatives.join(" / ")}</small>
                      ) : null}
                      {citationsOf(section).length > 0 ? (
                        <div className={styles.citationList}>
                          {citationsOf(section).map((citation) => (
                            <div
                              key={`${section.selected_clause_id}_${citation.source_id}`}
                              className={styles.citationCard}
                            >
                              <strong>{citation.title}</strong>
                              <code>{citation.source_id}</code>
                              <p>{citation.excerpt}</p>
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              </div>
            ) : null}

            {(artifacts.risk_summary ?? []).length > 0 ? (
              <div className={styles.infoBlock}>
                <h3>风险列表</h3>
                <div className={styles.cardStack}>
                  {(artifacts.risk_summary ?? []).map((risk, index) => (
                    <article key={`${risk.code}_${index}`} className={styles.infoCard}>
                      <div className={styles.riskHeader}>
                        <span
                          className={
                            risk.severity === "high"
                              ? styles.riskHigh
                              : risk.severity === "medium"
                              ? styles.riskMedium
                              : styles.riskLow
                          }
                        >
                          {risk.severity}
                        </span>
                        <strong>{risk.code}</strong>
                      </div>
                      <p>{risk.message}</p>
                      <small>{risk.location}</small>
                    </article>
                  ))}
                </div>
              </div>
            ) : null}

            {traceEntries.length > 0 ? (
              <div className={styles.infoBlock}>
                <h3>运行轨迹</h3>
                <ol className={styles.timeline}>
                  {traceEntries.map((trace, index) => (
                    <li
                      key={`${index}_${trace}`}
                      className={
                        index === traceEntries.length - 1
                          ? styles.timelineCurrent
                          : ""
                      }
                    >
                      <code>{trace}</code>
                    </li>
                  ))}
                </ol>
              </div>
            ) : null}
          </section>
        </aside>

        <section className={styles.chatPane}>
          <section className={styles.chatHero}>
            <div>
              <span className={styles.chatEyebrow}>AI 审查对话</span>
              <h2>像与助手协作一样审查、修改、继续</h2>
              <p>右侧专注对话和人工决策。你可以直接提修改意见，也可以根据系统提示逐项补充。</p>
            </div>
            <div className={styles.traceMeta}>
              <span>Session {sessionId === "pending" ? "初始化中" : sessionId}</span>
              <span>Project {projectId ?? "未创建"}</span>
            </div>
          </section>

          <section className={styles.chatPanel}>
            <div className={styles.panelHeading}>
              <div>
                <h2>对话记录</h2>
                <p>通过对话进行审查、修正和继续。</p>
              </div>
            </div>
            <div ref={chatListRef} className={styles.chatList}>
              {messages.length === 0 ? (
                <div className={styles.emptyChat}>
                  <strong>还没有开始对话</strong>
                  <p>发送一条采购需求，右侧会以对话方式推进审查和修改。</p>
                </div>
              ) : (
                messages.map((message) => (
                  <article
                    key={`${message.timestamp}_${message.role}`}
                    className={
                      message.role === "user"
                        ? styles.messageUser
                        : styles.messageAssistant
                    }
                  >
                    <div className={styles.messageMeta}>
                      <strong>{message.role === "user" ? "你" : "BidCraft Agent"}</strong>
                    </div>
                    <p>{message.content}</p>
                  </article>
                ))
              )}

              {loading ? (
                <article className={styles.messageAssistant}>
                  <div className={styles.messageMeta}>
                    <strong>BidCraft Agent</strong>
                  </div>
                  <div className={styles.thinkingBubble}>
                    <span className={styles.thinkingDot} />
                    <span className={styles.thinkingDot} />
                    <span className={styles.thinkingDot} />
                    <p>AI 正在思考 / 审查中…</p>
                  </div>
                </article>
              ) : null}

              {result?.requires_user_input ? (
                <article className={styles.messageAssistant}>
                  <div className={styles.messageMeta}>
                    <strong>待你处理</strong>
                  </div>
                  <div className={styles.chatActionCard}>
                    <h3>{pauseTitle}</h3>
                    <p>{pauseDescription}</p>
                    {clarificationCoachMessage ? (
                      <div className={styles.guidanceCard}>
                        <strong>填写建议</strong>
                        <p>{clarificationCoachMessage}</p>
                      </div>
                    ) : null}

                    {pauseKind === "clarification" ? (
                      <form onSubmit={onSubmitClarifications} className={styles.reviewForm}>
                        {clarificationItems.map((item) => (
                          <label key={item.field} className={styles.fieldBlock}>
                            <span>{item.question}</span>
                            <input
                              value={clarificationValues[item.field] ?? ""}
                              onChange={(event) =>
                                setClarificationValues((prev) => ({
                                  ...prev,
                                  [item.field]: event.target.value,
                                }))
                              }
                              placeholder={`请输入 ${item.field}`}
                              disabled={loading}
                            />
                          </label>
                        ))}
                        <button
                          type="submit"
                          className={styles.primaryButton}
                          disabled={loading}
                        >
                          提交补充并继续
                        </button>
                      </form>
                    ) : pauseKind === "fix_plan" ? (
                      <div className={styles.reviewForm}>
                        <p className={styles.helperText}>
                          你可以先尝试一次自动修复，或允许降级为草稿版继续导出。
                        </p>
                        <ul className={styles.bulletList}>
                          {result.options.map((option, index) => (
                            <li key={`${index}_${optionText(option)}`}>{optionText(option)}</li>
                          ))}
                        </ul>
                        <div className={styles.composerActions}>
                          <button
                            type="button"
                            className={styles.primaryButton}
                            onClick={onAutoRepairWithPe}
                            disabled={loading}
                          >
                            自动修复一次
                          </button>
                          <button
                            type="button"
                            className={styles.secondaryButton}
                            onClick={onAllowDraftContinue}
                            disabled={loading}
                          >
                            改为草稿继续
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className={styles.reviewForm}>
                        <div className={styles.optionGrid}>
                          {result.options.length > 0 ? (
                            result.options.map((option, index) => (
                              <button
                                key={`${index}_${optionText(option)}`}
                                type="button"
                                className={styles.optionButton}
                                onClick={() => void onSelectOption(option)}
                                disabled={loading}
                              >
                                {optionText(option)}
                              </button>
                            ))
                          ) : (
                            <p className={styles.emptyState}>
                              当前没有预设选项，你也可以直接在下方补充说明。
                            </p>
                          )}
                        </div>
                      </div>
                    )}

                    <form onSubmit={onContinueWithText} className={styles.inlineForm}>
                      <input
                        value={continueMessage}
                        onChange={(event) => setContinueMessage(event.target.value)}
                        placeholder="可选：补充一句说明，再继续审查"
                        disabled={loading}
                      />
                      <button
                        type="submit"
                        className={styles.primaryButton}
                        disabled={loading}
                      >
                        继续
                      </button>
                    </form>
                  </div>
                </article>
              ) : null}

              {artifacts.preview_html ? (
                <article className={styles.messageAssistant}>
                  <div className={styles.messageMeta}>
                    <strong>当前预览</strong>
                  </div>
                  <div className={styles.chatActionCard}>
                    <div className={styles.cardToolbar}>
                      <div className={styles.cardToolbarActions}>
                        {artifacts.can_export_formal ? (
                          <button
                            type="button"
                            className={styles.primaryButton}
                            onClick={onExportFormal}
                            disabled={loading || !projectId}
                          >
                            正式导出
                          </button>
                        ) : (
                          <button
                            type="button"
                            className={styles.secondaryButton}
                            onClick={onExportDraft}
                            disabled={loading || !projectId}
                          >
                            导出草稿
                          </button>
                        )}
                      </div>
                      <p>文档已经生成预览，你可以直接在对话区下方继续审查。</p>
                      {exportFileUrl ? (
                        <a
                          href={exportFileUrl}
                          target="_blank"
                          rel="noreferrer"
                          className={styles.downloadButtonInline}
                        >
                          导出文件
                        </a>
                      ) : null}
                    </div>
                    <div
                      className={styles.previewFrame}
                      dangerouslySetInnerHTML={{ __html: artifacts.preview_html }}
                    />
                  </div>
                </article>
              ) : null}

              {exportFileUrl && !artifacts.preview_html ? (
                <article className={styles.messageAssistant}>
                  <div className={styles.messageMeta}>
                    <strong>导出结果</strong>
                  </div>
                  <div className={styles.chatActionCard}>
                    <p>当前轮次已经产生可下载文件。</p>
                    <a
                      href={exportFileUrl}
                      target="_blank"
                      rel="noreferrer"
                      className={styles.downloadButton}
                    >
                      下载当前导出文件
                    </a>
                  </div>
                </article>
              ) : null}

              {error ? (
                <article className={styles.messageAssistant}>
                  <div className={styles.messageMeta}>
                    <strong>错误信息</strong>
                  </div>
                  <div className={styles.chatActionCard}>
                    <pre className={styles.errorPre}>{error}</pre>
                  </div>
                </article>
              ) : null}
            </div>
            <form onSubmit={onSendMessage} className={styles.composer}>
              <textarea
                rows={4}
                value={inputMessage}
                onChange={(event) => setInputMessage(event.target.value)}
                placeholder="输入采购需求、修改意见，或让 AI 重新审查某一部分。"
                disabled={loading}
              />
              <div className={styles.composerActions}>
                <button
                  type="submit"
                  className={styles.primaryButton}
                  disabled={loading || !inputMessage.trim()}
                >
                  {projectId ? "发送并继续审查" : "开始审查"}
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={onResetSession}
                  disabled={loading}
                >
                  清空对话
                </button>
              </div>
            </form>
          </section>
        </section>
      </div>
    </main>
  );
}
