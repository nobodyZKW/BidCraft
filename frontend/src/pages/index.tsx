import { CSSProperties, FormEvent, useMemo, useState } from "react";

import { GenerateDocumentResponse, generateDocument } from "../services/api";

const SAMPLE_TEXT =
  "服务器采购项目，预算300万元，45天交付，付款30/60/10，验收按国家标准和测试报告执行，质保24个月，供应商需具备同类项目经验。";

type ExportFormat = "docx" | "pdf";
type ExportMode = "draft" | "formal";

export default function Home() {
  const [projectName, setProjectName] = useState("服务器采购项目");
  const [department, setDepartment] = useState("信息部");
  const [rawText, setRawText] = useState(SAMPLE_TEXT);
  const [format, setFormat] = useState<ExportFormat>("docx");
  const [mode, setMode] = useState<ExportMode>("draft");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<GenerateDocumentResponse | null>(null);

  const sortedRisks = useMemo(() => {
    if (!result) return [];
    const rank: Record<string, number> = { high: 0, medium: 1, low: 2 };
    return [...result.risk_summary].sort(
      (a, b) => rank[a.severity] - rank[b.severity]
    );
  }, [result]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await generateDocument({
        project_name: projectName,
        department,
        raw_input_text: rawText,
        format,
        mode,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "32px 20px 48px",
        background:
          "linear-gradient(140deg, #f7f5e9 0%, #eef4f8 35%, #fff9f0 100%)",
        fontFamily: "'Segoe UI', 'PingFang SC', sans-serif",
      }}
    >
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <h1 style={{ margin: "0 0 8px", fontSize: 40 }}>BidCraft AI</h1>
        <p style={{ margin: "0 0 24px", color: "#2f3a45" }}>
          输入自然语言需求，系统会自动抽取、校验、渲染并导出文件。
        </p>

        <form
          onSubmit={onSubmit}
          style={{
            border: "1px solid #d9d6c8",
            background: "#fffdfa",
            borderRadius: 16,
            padding: 20,
            boxShadow: "0 8px 24px rgba(30, 38, 48, 0.06)",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
              marginBottom: 12,
            }}
          >
            <label>
              项目名称
              <input
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                style={inputStyle}
                required
              />
            </label>
            <label>
              采购部门
              <input
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                style={inputStyle}
                required
              />
            </label>
            <label>
              导出格式
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value as ExportFormat)}
                style={inputStyle}
              >
                <option value="docx">docx</option>
                <option value="pdf">pdf</option>
              </select>
            </label>
            <label>
              导出模式
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as ExportMode)}
                style={inputStyle}
              >
                <option value="draft">草稿版</option>
                <option value="formal">正式版</option>
              </select>
            </label>
          </div>

          <label style={{ display: "block" }}>
            自然语言需求
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              rows={6}
              style={{ ...inputStyle, resize: "vertical", width: "100%" }}
              required
            />
          </label>

          <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
            <button type="submit" disabled={loading} style={buttonStyle}>
              {loading ? "处理中..." : "一键生成"}
            </button>
            <button
              type="button"
              onClick={() => setRawText(SAMPLE_TEXT)}
              style={secondaryButtonStyle}
            >
              使用示例
            </button>
          </div>
        </form>

        {error && (
          <section style={{ ...panelStyle, borderColor: "#f2b5b5", background: "#fff2f2" }}>
            <h3 style={{ marginTop: 0 }}>错误信息</h3>
            <pre style={{ marginBottom: 0, whiteSpace: "pre-wrap" }}>{error}</pre>
          </section>
        )}

        {result && (
          <>
            <section style={panelStyle}>
              <h2 style={{ marginTop: 0 }}>生成结果</h2>
              <p>项目ID：{result.project_id}</p>
              <p>可导出正式版：<strong>{String(result.can_export_formal)}</strong></p>
              <p>实际导出模式：<strong>{result.delivered_mode === "formal" ? "正式版" : "草稿版"}</strong></p>
              {result.message ? <p style={{ color: "#a85a00" }}>{result.message}</p> : null}
              {result.file_url ? (
                <a href={result.file_url} target="_blank" rel="noreferrer">
                  下载文件
                </a>
              ) : (
                <p>未生成可下载文件。</p>
              )}
            </section>

            <section style={panelStyle}>
              <h3 style={{ marginTop: 0 }}>缺失字段</h3>
              {result.missing_fields.length === 0 ? (
                <p>无</p>
              ) : (
                <ul>
                  {result.missing_fields.map((field) => (
                    <li key={field}>{field}</li>
                  ))}
                </ul>
              )}

              <h3>澄清问题</h3>
              {result.clarification_questions.length === 0 ? (
                <p>无</p>
              ) : (
                <ul>
                  {result.clarification_questions.map((question) => (
                    <li key={question}>{question}</li>
                  ))}
                </ul>
              )}
            </section>

            <section style={panelStyle}>
              <h3 style={{ marginTop: 0 }}>风险列表</h3>
              {sortedRisks.length === 0 ? (
                <p>未发现风险。</p>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      <th style={thStyle}>级别</th>
                      <th style={thStyle}>编码</th>
                      <th style={thStyle}>说明</th>
                      <th style={thStyle}>位置</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedRisks.map((risk, idx) => (
                      <tr key={`${risk.code}_${idx}`}>
                        <td style={tdStyle}>{risk.severity}</td>
                        <td style={tdStyle}>{risk.code}</td>
                        <td style={tdStyle}>{risk.message}</td>
                        <td style={tdStyle}>{risk.location}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>

            <section style={panelStyle}>
              <h3 style={{ marginTop: 0 }}>文档预览</h3>
              <div
                style={{
                  border: "1px solid #d8dde3",
                  borderRadius: 10,
                  background: "#ffffff",
                  padding: 12,
                  maxHeight: 500,
                  overflow: "auto",
                }}
                dangerouslySetInnerHTML={{ __html: result.preview_html }}
              />
            </section>
          </>
        )}
      </div>
    </main>
  );
}

const inputStyle: CSSProperties = {
  marginTop: 6,
  width: "100%",
  padding: "10px 12px",
  border: "1px solid #cfd5db",
  borderRadius: 10,
  boxSizing: "border-box",
  background: "#fff",
};

const buttonStyle: CSSProperties = {
  background: "#204c6f",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  padding: "10px 18px",
  cursor: "pointer",
};

const secondaryButtonStyle: CSSProperties = {
  background: "#f0f3f6",
  color: "#1e3342",
  border: "1px solid #cfd5db",
  borderRadius: 10,
  padding: "10px 16px",
  cursor: "pointer",
};

const panelStyle: CSSProperties = {
  marginTop: 16,
  border: "1px solid #d9d6c8",
  borderRadius: 14,
  background: "#fffdfa",
  padding: 16,
};

const thStyle: CSSProperties = {
  textAlign: "left",
  borderBottom: "1px solid #dde1e6",
  padding: "8px 6px",
};

const tdStyle: CSSProperties = {
  borderBottom: "1px solid #eef1f4",
  padding: "8px 6px",
  verticalAlign: "top",
};
