# BidCraft AI (MVP)

采购文件智能生成系统 MVP。  
支持流程：需求输入 -> 结构化抽取 -> 条款匹配 -> 合规校验 -> 渲染预览 -> Word/PDF 导出。

## 1. MVP 范围
- 采购类型：`goods`
- 采购方式：`public_tender`
- 核心能力：
  - 自然语言需求输入
  - JSON Schema 结构化抽取
  - 缺失项提示
  - 条款自动匹配（版本化）
  - 动态模板组装
  - 基础合规规则校验（10+）
  - `docx/pdf` 导出

## 2. 目录结构
```text
.
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ core/
│  │  ├─ llm/
│  │  ├─ models/
│  │  ├─ renderers/
│  │  ├─ repositories/
│  │  ├─ rules/
│  │  ├─ schemas/
│  │  └─ services/
│  └─ tests/
├─ config/
├─ data/
│  ├─ clauses/
│  ├─ templates/
│  ├─ seeds/
│  └─ runtime/
├─ docs/
├─ frontend/
├─ .env.example
├─ AGENTS.md
├─ plans.md
└─ implement.md
```

## 3. API Key 使用说明（DeepSeek）
系统优先读取 `config/config.py` 中的 `DEEPSEEK_API_KEY`（或 `API_KEY`）。  
你已配置的 `config/config.py` 会被 `backend/app/core/settings.py` 自动加载。

也可通过环境变量覆盖：
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`

## 4. 安装与运行
### 4.1 后端
```bash
pip install -r requirements.txt
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Swagger/OpenAPI:
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/openapi.json`

### 4.2 前端（骨架）
```bash
cd frontend
npm install
npm run dev
```

## 5. 核心接口
- `POST /api/projects`
- `POST /api/projects/{project_id}/extract`
- `POST /api/projects/{project_id}/clauses/match`
- `POST /api/projects/{project_id}/validate`
- `POST /api/projects/{project_id}/render`
- `POST /api/projects/{project_id}/export`

## 6. 测试
```bash
pytest backend/tests -q
```

包含测试：
- schema 校验测试
- 规则引擎测试
- 模板装配测试
- 导出测试
- API 端到端测试

## 7. 导出规则
- `mode=draft`：允许中低风险并添加草稿水印
- `mode=formal`：仅当 `can_export_formal=true` 才允许
- 文件命名：`项目名称_文件类型_版本号_日期.docx/pdf`

## 8. 注意事项
- 条款和模板不写死在业务逻辑中，全部在 `data/` 下维护。
- 审计日志、快照、文档版本落盘在 `data/runtime/`。
- 当前前端为 MVP 骨架页，核心功能由后端 API 驱动。
