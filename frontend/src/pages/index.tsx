import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  AgentArtifacts,
  AgentChatResponse,
  AgentOption,
  BASE_URL,
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

type StepDef = {
  id:
    | "project"
    | "extract"
    | "clarification"
    | "clause_match"
    | "validate"
    | "risk_fix"
    | "render"
    | "confirm_export"
    | "export";
  label: string;
  tools: string[];
};

const STEP_DEFS: StepDef[] = [
  { id: "project", label: "项目初始化", tools: ["project_tools.ensure_project"] },
  { id: "extract", label: "结构化抽取", tools: ["extraction_tools.extract_requirements"] },
  {
    id: "clarification",
    label: "缺失澄清",
    tools: ["clarification_tools.ask_for_clarification", "extraction_tools.merge_clarifications"],
  },
  {
    id: "clause_match",
    label: "条款匹配",
    tools: ["clause_tools.match_or_override", "clause_tools.list_clause_alternatives"],
  },
  { id: "validate", label: "风险校验", tools: ["validation_tools.validate_document"] },
  { id: "risk_fix", label: "修复决策", tools: ["validation_tools.build_fix_options"] },
  { id: "render", label: "渲染预览", tools: ["render_tools.render_preview"] },
  {
    id: "confirm_export",
    label: "导出确认",
    tools: [
      "clarification_tools.confirm_export.pending",
      "clarification_tools.confirm_export.accept",
      "clarification_tools.confirm_export.reject",
    ],
  },
  { id: "export", label: "文档导出", tools: ["export_tools.export_document"] },
];

function createSessionId(): string {
  return `session_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
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
  if (lastToolCall.includes("clarification_tools.ask_for_clarification")) {
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
  const items: ClarificationItem[] = [];
  for (const option of options) {
    const field = typeof option.field === "string" ? option.field : "";
    if (!field) continue;
    const question =
      typeof option.question === "string" && option.question.trim()
        ? option.question
        : `请补充字段: ${field}`;
    items.push({ field, question });
  }
  return items;
}

function optionText(option: AgentOption): string {
  if (typeof option.text === "string" && option.text.trim()) return option.text;
  if (typeof option.question === "string" && option.question.trim()) return option.question;
  if (typeof option.field === "string" && option.field.trim()) return option.field;
  if (typeof option.id === "string" && option.id.trim()) return option.id;
  if (typeof option.id === "number") return String(option.id);
  return "continue";
}

function resolveExportFileUrl(artifacts: AgentArtifacts): string | null {
  const filePath = artifacts.file_path;
  if (!filePath || typeof filePath !== "string") return null;
  const normalized = filePath.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  if (parts.length === 0) return null;
  const filename = encodeURIComponent(parts[parts.length - 1]);
  return `${BASE_URL.replace(/\/$/, "")}/exports/${filename}`;
}

function stepIsDone(payload: AgentChatResponse | null, tools: string[]): boolean {
  if (!payload) return false;
  return payload.tool_calls.some((toolCall) => tools.some((tool) => toolCall.startsWith(tool)));
}

export default function Home() {
  const [sessionId, setSessionId] = useState<string>("pending");
  const [projectId, setProjectId] = useState<string | null>(null);
  const [inputMessage, setInputMessage] = useState<string>(
    "请帮我生成货物类公开招标文件，预算300万，交付期45天，付款30/60/10，质保24个月。"
  );
  const [continueMessage, setContinueMessage] = useState<string>("");
  const [clarificationValues, setClarificationValues] = useState<Record<string, string>>({});
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [result, setResult] = useState<AgentChatResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const pauseKind = inferPauseKind(result);
  const clarificationItems = useMemo(
    () => (pauseKind === "clarification" && result ? toClarificationItems(result.options) : []),
    [pauseKind, result]
  );

  const stepActiveId: StepDef["id"] | null = useMemo(() => {
    if (!result) return null;
    if (!result.requires_user_input) return null;
    if (pauseKind === "clarification") return "clarification";
    if (pauseKind === "confirm_export") return "confirm_export";
    if (pauseKind === "override_clause") return "clause_match";
    if (pauseKind === "fix_plan") return "risk_fix";
    return null;
  }, [pauseKind, result]);

  const artifacts = result?.artifacts ?? {};
  const exportFileUrl = resolveExportFileUrl(artifacts);

  useEffect(() => {
    setSessionId(createSessionId());
  }, []);

  async function submitTurn(params: {
    userText: string;
    message?: string;
    userClarifications?: Record<string, unknown>;
  }): Promise<void> {
    const userText = params.userText.trim();
    const message = (params.message ?? userText).trim();
    if (!projectId && !message) {
      setError("请输入消息后再发送。");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const effectiveSessionId =
        sessionId === "pending" ? createSessionId() : sessionId;
      if (sessionId === "pending") {
        setSessionId(effectiveSessionId);
      }
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

      if (payload.project_id) {
        setProjectId(payload.project_id);
      }
      setResult(payload);
      setMessages((prev) => {
        const next = [...prev];
        if (userText) {
          next.push({ role: "user", content: userText, timestamp: Date.now() });
        }
        if (payload.assistant_message) {
          next.push({
            role: "assistant",
            content: payload.assistant_message,
            timestamp: Date.now() + 1,
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
    await submitTurn({ userText: message });
  }

  async function onContinueWithText(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!projectId) return;
    const text = continueMessage.trim();
    setContinueMessage("");
    await submitTurn({ userText: text || "继续流程", message: text });
  }

  async function onSubmitClarifications(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!projectId) return;
    const payload: Record<string, string> = {};
    for (const item of clarificationItems) {
      const value = (clarificationValues[item.field] ?? "").trim();
      if (value) {
        payload[item.field] = value;
      }
    }
    if (Object.keys(payload).length === 0) {
      setError("请至少填写一个澄清字段。");
      return;
    }
    const clarificationText = Object.entries(payload)
      .map(([field, value]) => `${field}=${value}`)
      .join("; ");
    await submitTurn({
      userText: `澄清补充: ${clarificationText}`,
      message: `update fields -> ${clarificationText}`,
      userClarifications: payload,
    });
  }

  async function onSelectOption(option: AgentOption): Promise<void> {
    if (!projectId || !result) return;
    const label = optionText(option);
    const idValue =
      typeof option.id === "string" || typeof option.id === "number" ? String(option.id) : label;

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
        userText: `选择付款条款: ${idValue}`,
        message: `override clause ${idValue}`,
        userClarifications: { override_clause_id: idValue },
      });
      return;
    }

    await submitTurn({
      userText: `选择: ${label}`,
      message: label,
    });
  }

  async function onAllowDraftContinue(): Promise<void> {
    if (!projectId) return;
    await submitTurn({
      userText: "允许降级到草稿并继续",
      message: "allow draft and continue",
      userClarifications: { allow_draft: true },
    });
  }

  async function onAutoRepairWithPe(): Promise<void> {
    if (!projectId) return;
    await submitTurn({
      userText: "执行PE自动修复一次",
      message: "auto repair with pe once",
      userClarifications: { auto_repair_with_pe: true },
    });
  }

  function onResetSession(): void {
    setSessionId(createSessionId());
    setProjectId(null);
    setInputMessage("");
    setContinueMessage("");
    setClarificationValues({});
    setMessages([]);
    setResult(null);
    setError("");
  }

  async function onStepClick(stepId: StepDef["id"]): Promise<void> {
    if (loading) return;
    const commandByStep: Record<StepDef["id"], { userText: string; message: string }> = {
      project: { userText: "开始流程", message: "start workflow" },
      extract: { userText: "重新抽取需求", message: "please extract requirements again" },
      clarification: { userText: "只查看缺失字段", message: "show missing fields only" },
      clause_match: { userText: "替换付款条款", message: "replace payment clause" },
      validate: { userText: "重新进行风险校验", message: "validate document again" },
      risk_fix: { userText: "给出高风险修复选项", message: "build fix options for high risks" },
      render: { userText: "生成预览", message: "render preview" },
      confirm_export: { userText: "正式导出", message: "formal export" },
      export: { userText: "草稿导出", message: "draft export" },
    };

    const command = commandByStep[stepId];
    await submitTurn({
      userText: command.userText,
      message: command.message,
    });
  }

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.hero}>
          <div>
            <h1>BidCraft Agent Chat</h1>
            <p>输入采购需求后，由工具链自动推进抽取、匹配、校验、导出；支持暂停与继续。</p>
          </div>
          <div className={styles.heroMeta}>
            <span>Session: {sessionId}</span>
            <span>Project: {projectId ?? "-"}</span>
            <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
              API Docs
            </a>
          </div>
        </header>

        <section className={styles.card}>
          <h2>流程步骤</h2>
          <div className={styles.stepBar}>
            {STEP_DEFS.map((step) => {
              const done = stepIsDone(result, step.tools);
              const active = stepActiveId === step.id;
              const cls = [
                styles.step,
                done ? styles.stepDone : "",
                active ? styles.stepActive : "",
              ]
                .filter(Boolean)
                .join(" ");
              return (
                <button
                  key={step.id}
                  className={`${cls} ${styles.stepButton}`}
                  type="button"
                  onClick={() => void onStepClick(step.id)}
                  disabled={loading}
                  title={`点击执行: ${step.label}`}
                >
                  <span>{step.label}</span>
                </button>
              );
            })}
          </div>
          {result ? (
            <div className={styles.statusLine}>
              <span>current_step: {result.current_step || "-"}</span>
              <span>next_action: {result.next_action || "-"}</span>
              <span className={result.requires_user_input ? styles.badgePause : styles.badgeRun}>
                {result.requires_user_input ? "Paused" : "Running/Done"}
              </span>
            </div>
          ) : null}
        </section>

        <section className={styles.layout}>
          <div className={styles.column}>
            <section className={styles.card}>
              <h2>对话</h2>
              <form onSubmit={onSendMessage} className={styles.inputBlock}>
                <textarea
                  rows={4}
                  value={inputMessage}
                  onChange={(event) => setInputMessage(event.target.value)}
                  placeholder="输入你的采购需求或指令，例如：请正式导出、只查看缺失字段、替换付款条款..."
                  disabled={loading}
                />
                <div className={styles.actions}>
                  <button type="submit" disabled={loading || !inputMessage.trim()}>
                    {projectId ? "发送并继续" : "开始流程"}
                  </button>
                  <button type="button" className={styles.secondary} onClick={onResetSession} disabled={loading}>
                    新会话
                  </button>
                </div>
              </form>

              <div className={styles.chatBox}>
                {messages.length === 0 ? (
                  <p className={styles.empty}>暂无对话，先发送一条需求开始。</p>
                ) : (
                  messages.map((message) => (
                    <div
                      key={`${message.timestamp}_${message.role}`}
                      className={message.role === "user" ? styles.userBubble : styles.assistantBubble}
                    >
                      <strong>{message.role === "user" ? "You" : "Agent"}</strong>
                      <p>{message.content}</p>
                    </div>
                  ))
                )}
              </div>
            </section>

            {result?.requires_user_input ? (
              <section className={styles.card}>
                <h2>暂停输入</h2>
                {pauseKind === "clarification" ? (
                  <form onSubmit={onSubmitClarifications} className={styles.pauseForm}>
                    {clarificationItems.map((item) => (
                      <label key={item.field} className={styles.field}>
                        <span>{item.question}</span>
                        <input
                          value={clarificationValues[item.field] ?? ""}
                          onChange={(event) =>
                            setClarificationValues((prev) => ({
                              ...prev,
                              [item.field]: event.target.value,
                            }))
                          }
                          placeholder={`填写 ${item.field}`}
                          disabled={loading}
                        />
                      </label>
                    ))}
                    <button type="submit" disabled={loading}>
                      提交澄清并继续
                    </button>
                  </form>
                ) : pauseKind === "fix_plan" ? (
                  <div className={styles.pauseForm}>
                    <p>检测到高风险。可先按建议修复，或允许降级草稿继续导出。</p>
                    <ul className={styles.optionList}>
                      {result.options.map((option, index) => (
                        <li key={`${index}_${optionText(option)}`}>{optionText(option)}</li>
                      ))}
                    </ul>
                    <div className={styles.actions}>
                      <button type="button" onClick={onAutoRepairWithPe} disabled={loading}>
                        PE自动修复一次
                      </button>
                      <button type="button" onClick={onAllowDraftContinue} disabled={loading}>
                        允许草稿继续
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className={styles.pauseForm}>
                    <p>当前步骤需要你确认后继续。</p>
                    <div className={styles.optionButtons}>
                      {result.options.length > 0 ? (
                        result.options.map((option, index) => (
                          <button
                            key={`${index}_${optionText(option)}`}
                            type="button"
                            onClick={() => void onSelectOption(option)}
                            disabled={loading}
                          >
                            {optionText(option)}
                          </button>
                        ))
                      ) : (
                        <p className={styles.empty}>当前没有预设选项，可直接继续。</p>
                      )}
                    </div>
                  </div>
                )}

                <form onSubmit={onContinueWithText} className={styles.inlineContinue}>
                  <input
                    value={continueMessage}
                    onChange={(event) => setContinueMessage(event.target.value)}
                    placeholder="可选：补充说明后继续"
                    disabled={loading}
                  />
                  <button type="submit" disabled={loading}>
                    继续
                  </button>
                </form>
              </section>
            ) : null}

            {error ? (
              <section className={`${styles.card} ${styles.errorCard}`}>
                <h2>错误</h2>
                <pre>{error}</pre>
              </section>
            ) : null}
          </div>

          <div className={styles.column}>
            <section className={styles.card}>
              <h2>Tool Calls</h2>
              {!result || result.tool_calls.length === 0 ? (
                <p className={styles.empty}>暂无工具调用。</p>
              ) : (
                <ul className={styles.toolList}>
                  {result.tool_calls.map((toolCall, index) => (
                    <li key={`${index}_${toolCall}`}>
                      <code>{toolCall}</code>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className={styles.card}>
              <h2>产物</h2>
              <div className={styles.kv}>
                <span>can_export_formal</span>
                <strong>{String(artifacts.can_export_formal ?? false)}</strong>
              </div>
              {exportFileUrl ? (
                <a href={exportFileUrl} className={styles.download} target="_blank" rel="noreferrer">
                  下载导出文件
                </a>
              ) : (
                <p className={styles.empty}>暂无可下载文件。</p>
              )}
              {artifacts.error ? <p className={styles.errorText}>error: {String(artifacts.error)}</p> : null}
            </section>

            <section className={styles.card}>
              <h2>缺失字段</h2>
              {(artifacts.missing_fields ?? []).length === 0 ? (
                <p className={styles.empty}>无</p>
              ) : (
                <ul className={styles.optionList}>
                  {(artifacts.missing_fields ?? []).map((field) => (
                    <li key={field}>{field}</li>
                  ))}
                </ul>
              )}
            </section>

            <section className={styles.card}>
              <h2>风险摘要</h2>
              {(artifacts.risk_summary ?? []).length === 0 ? (
                <p className={styles.empty}>无风险</p>
              ) : (
                <div className={styles.riskTableWrap}>
                  <table>
                    <thead>
                      <tr>
                        <th>Severity</th>
                        <th>Code</th>
                        <th>Message</th>
                        <th>Location</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(artifacts.risk_summary ?? []).map((risk, index) => (
                        <tr key={`${risk.code}_${index}`}>
                          <td>{risk.severity}</td>
                          <td>{risk.code}</td>
                          <td>{risk.message}</td>
                          <td>{risk.location}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>
        </section>

        {artifacts.preview_html ? (
          <section className={styles.card}>
            <h2>文档预览</h2>
            <div className={styles.preview} dangerouslySetInnerHTML={{ __html: artifacts.preview_html }} />
          </section>
        ) : null}
      </div>
    </main>
  );
}
