from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.api.routes_agent import router_agent
from app.core.settings import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "采购文件智能生成系统 MVP。支持需求抽取、条款匹配、合规校验、"
        "文档渲染与导出。"
    ),
    openapi_tags=[
        {"name": "项目管理", "description": "项目创建与状态查询"},
        {"name": "抽取与生成", "description": "结构化抽取、条款匹配、一键生成"},
        {"name": "校验与导出", "description": "风险校验、文档渲染与导出"},
    ],
    swagger_ui_parameters={
        "docExpansion": "none",
        "defaultModelsExpandDepth": -1,
        "displayRequestDuration": True,
    },
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(router_agent)
app.mount("/exports", StaticFiles(directory=settings.export_dir), name="exports")


@app.get("/", response_class=HTMLResponse, tags=["项目管理"], summary="后端首页")
def home() -> str:
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{settings.app_name} API</title>
  <style>
    :root {{
      --bg: #f6f6f2;
      --card: #ffffff;
      --text: #1f2a35;
      --muted: #587083;
      --accent: #2f6d96;
      --line: #d4dce3;
    }}
    body {{
      margin: 0;
      font-family: "Noto Sans SC","Microsoft YaHei","Segoe UI",sans-serif;
      background: linear-gradient(140deg, #f8f4e8 0%, #edf4f7 38%, #fff8f2 100%);
      color: var(--text);
    }}
    .wrap {{
      max-width: 980px;
      margin: 24px auto;
      padding: 0 16px 32px;
    }}
    .hero {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 20px;
      box-shadow: 0 8px 20px rgba(31, 42, 53, 0.08);
    }}
    .hero h1 {{ margin: 0 0 8px; }}
    .hero p {{ margin: 0; color: var(--muted); }}
    .links {{
      display: grid;
      grid-template-columns: repeat(auto-fit,minmax(220px,1fr));
      gap: 12px;
      margin-top: 14px;
    }}
    .link-card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
    }}
    .link-card a {{
      color: var(--accent);
      text-decoration: none;
      font-weight: 700;
    }}
    .table {{
      margin-top: 14px;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{
      border-bottom: 1px solid var(--line);
      text-align: left;
      padding: 10px 12px;
      font-size: 14px;
    }}
    th {{ background: #f2f6f9; }}
    code {{
      background: #f2f6f9;
      padding: 2px 6px;
      border-radius: 6px;
      font-family: Consolas, monospace;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>{settings.app_name} / {settings.app_version}</h1>
      <p>采购文件智能生成系统后端服务已启动。建议通过 Swagger 快速调试接口。</p>
      <div class="links">
        <div class="link-card"><a href="/docs">打开 Swagger UI</a></div>
        <div class="link-card"><a href="/redoc">打开 ReDoc</a></div>
        <div class="link-card"><a href="/health">健康检查</a></div>
      </div>
    </section>

    <section class="table">
      <table>
        <thead>
          <tr>
            <th>方法</th>
            <th>路径</th>
            <th>说明</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>POST</td><td><code>/api/projects</code></td><td>创建项目</td></tr>
          <tr><td>POST</td><td><code>/api/projects/{{project_id}}/extract</code></td><td>需求抽取</td></tr>
          <tr><td>POST</td><td><code>/api/projects/{{project_id}}/clauses/match</code></td><td>条款匹配</td></tr>
          <tr><td>POST</td><td><code>/api/projects/{{project_id}}/validate</code></td><td>规则校验</td></tr>
          <tr><td>POST</td><td><code>/api/projects/{{project_id}}/render</code></td><td>文档渲染</td></tr>
          <tr><td>POST</td><td><code>/api/projects/{{project_id}}/export</code></td><td>导出文档</td></tr>
          <tr><td>POST</td><td><code>/api/projects/generate</code></td><td>一键生成</td></tr>
        </tbody>
      </table>
    </section>
  </div>
</body>
</html>
"""


@app.get("/health", tags=["项目管理"], summary="健康检查")
def health() -> dict[str, str]:
    return {"status": "ok"}
