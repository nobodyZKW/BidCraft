import { FormEvent, useMemo, useState } from "react";

import { GenerateDocumentResponse, generateDocument } from "../services/api";
import styles from "./index.module.css";

const SAMPLE_TEXT =
  "服务器采购项目，预算300万元，45天交付，付款30/60/10，验收按国家标准和测试报告执行，质保24个月，供应商需具备同类项目经验。";

type ExportFormat = "docx" | "pdf";
type ExportMode = "draft" | "formal";

const severityLabel: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

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
    <main className={styles.page}>
      <div className={styles.glowA} />
      <div className={styles.glowB} />
      <div className={styles.container}>
        <header className={styles.hero}>
          <span className={styles.badge}>BidCraft AI / MVP</span>
          <h1 className={styles.title}>采购文件智能生成工作台</h1>
          <p className={styles.subtitle}>
            一次输入自然语言需求，自动完成抽取、校验、渲染与导出。
          </p>
        </header>

        <section className={styles.layout}>
          <form className={styles.card} onSubmit={onSubmit}>
            <h2 className={styles.cardTitle}>需求输入</h2>
            <div className={styles.grid}>
              <label className={styles.field}>
                <span>项目名称</span>
                <input
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  required
                />
              </label>
              <label className={styles.field}>
                <span>采购部门</span>
                <input
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  required
                />
              </label>
              <label className={styles.field}>
                <span>导出格式</span>
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value as ExportFormat)}
                >
                  <option value="docx">Word (.docx)</option>
                  <option value="pdf">PDF (.pdf)</option>
                </select>
              </label>
              <label className={styles.field}>
                <span>导出模式</span>
                <select
                  value={mode}
                  onChange={(e) => setMode(e.target.value as ExportMode)}
                >
                  <option value="draft">草稿版</option>
                  <option value="formal">正式版</option>
                </select>
              </label>
            </div>

            <label className={styles.field}>
              <span>自然语言需求</span>
              <textarea
                rows={7}
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                required
              />
            </label>

            <div className={styles.actions}>
              <button className={styles.primaryBtn} type="submit" disabled={loading}>
                {loading ? "处理中..." : "一键生成"}
              </button>
              <button
                className={styles.secondaryBtn}
                type="button"
                onClick={() => setRawText(SAMPLE_TEXT)}
                disabled={loading}
              >
                填入示例
              </button>
            </div>
          </form>

          <aside className={styles.side}>
            <div className={styles.tipCard}>
              <h3>后端链接</h3>
              <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
                Swagger 接口文档
              </a>
              <a href="http://127.0.0.1:8000/redoc" target="_blank" rel="noreferrer">
                ReDoc 文档视图
              </a>
            </div>
            <div className={styles.tipCard}>
              <h3>测试建议</h3>
              <p>先用草稿版验证，再切正式版观察风险拦截。</p>
              <p>如果正式版拦截，系统会自动回落到草稿版并返回下载链接。</p>
            </div>
          </aside>
        </section>

        {error && (
          <section className={`${styles.card} ${styles.errorCard}`}>
            <h2 className={styles.cardTitle}>错误信息</h2>
            <pre>{error}</pre>
          </section>
        )}

        {result && (
          <>
            <section className={styles.stats}>
              <article className={styles.statItem}>
                <span>项目 ID</span>
                <strong>{result.project_id}</strong>
              </article>
              <article className={styles.statItem}>
                <span>正式版可导出</span>
                <strong>{String(result.can_export_formal)}</strong>
              </article>
              <article className={styles.statItem}>
                <span>实际导出模式</span>
                <strong>{result.delivered_mode === "formal" ? "正式版" : "草稿版"}</strong>
              </article>
              <article className={styles.statItem}>
                <span>风险数量</span>
                <strong>{result.risk_summary.length}</strong>
              </article>
            </section>

            <section className={styles.card}>
              <h2 className={styles.cardTitle}>导出结果</h2>
              {result.message ? <p className={styles.warnText}>{result.message}</p> : null}
              {result.file_url ? (
                <a className={styles.downloadBtn} href={result.file_url} target="_blank" rel="noreferrer">
                  下载{result.delivered_mode === "formal" ? "正式版" : "草稿版"}文件
                </a>
              ) : (
                <p>未生成可下载文件。</p>
              )}
            </section>

            <section className={styles.card}>
              <h2 className={styles.cardTitle}>缺失项与澄清问题</h2>
              <div className={styles.twoCol}>
                <div>
                  <h4>缺失字段</h4>
                  {result.missing_fields.length === 0 ? (
                    <p>无</p>
                  ) : (
                    <ul>
                      {result.missing_fields.map((field) => (
                        <li key={field}>{field}</li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  <h4>澄清问题</h4>
                  {result.clarification_questions.length === 0 ? (
                    <p>无</p>
                  ) : (
                    <ul>
                      {result.clarification_questions.map((question) => (
                        <li key={question}>{question}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </section>

            <section className={styles.card}>
              <h2 className={styles.cardTitle}>风险清单</h2>
              {sortedRisks.length === 0 ? (
                <p>未发现风险。</p>
              ) : (
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>级别</th>
                        <th>编码</th>
                        <th>说明</th>
                        <th>位置</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedRisks.map((risk, idx) => (
                        <tr key={`${risk.code}_${idx}`}>
                          <td>
                            <span className={`${styles.severity} ${styles[risk.severity]}`}>
                              {severityLabel[risk.severity] || risk.severity}
                            </span>
                          </td>
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

            <section className={styles.card}>
              <h2 className={styles.cardTitle}>文档预览</h2>
              <div className={styles.preview} dangerouslySetInnerHTML={{ __html: result.preview_html }} />
            </section>
          </>
        )}
      </div>
    </main>
  );
}
