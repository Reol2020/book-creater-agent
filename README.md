# book-creater-agent

本地优先的网文 / 小说创作 Agent —— 写作 + 角色 / 世界观管理 + 向量知识库。

> 传承自桌面版 `novel_agent`(PySide6),Web 化 + RAG 强化。设计与踩坑沿用,见 [`DEV_NOTES.md`](./DEV_NOTES.md)。

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy 2 (async) / aiosqlite / Chroma |
| 前端 | Next.js 15 (App Router) / TypeScript / Tailwind / shadcn/ui / TipTap / Zustand |
| LLM | Anthropic / OpenAI / 兼容代理(沿用桌面版 LLMProfile 概念) |
| 部署 | 本地 `uvicorn` + `next dev`;后续可 Docker compose |

## 架构(六边形 / Ports & Adapters)

```
domain          纯业务,无框架依赖
  ↑
ports           接口契约 (Protocol)
  ↑
application     用例编排
  ↑
adapters/       inbound = FastAPI; outbound = SQLite/Chroma/LLM SDK
  ↑
config          DI 装配 —— 唯一知道实现的地方
```

切换 SQLite → Postgres / MongoDB,或抽离嵌入式版本,只换 adapter,不动业务。

## 开发起步

### 后端

```bash
cd backend
uv venv
uv pip install -e .
cp .env.example .env   # 填入 LLM API Key
uv run uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000/docs 看 OpenAPI。

### 前端

```bash
cd frontend
pnpm install   # 或 npm install
pnpm dev       # http://localhost:3000
```

## 目录速览

```
book-creater-agent/
├── backend/                # Python / FastAPI
│   └── app/
│       ├── domain/         # 业务模型 + 业务规则
│       ├── ports/          # 接口契约
│       ├── application/    # 用例服务
│       ├── adapters/
│       │   ├── inbound/api/    # FastAPI routers
│       │   └── outbound/       # SQLite / Chroma / LLM 实现
│       └── config/         # DI 容器 + 配置
├── frontend/               # Next.js 15
│   ├── app/                # 页面
│   ├── features/           # 业务能力切分
│   ├── components/         # ui (shadcn) + editor
│   └── lib/api/            # 后端契约层
├── DEV_NOTES.md
└── README.md
```

## 里程碑

- [x] M0:目录骨架 + 项目 CRUD + SSE 流式聊天最小闭环
- [ ] M1:Agent loop + 工具集 + 危险操作 SSE 异步确认
- [ ] M2:向量知识库 + RAG 注入 + 外部作品导入
- [ ] M3:TipTap 章节编辑器 + skills 一键技能 + 角色 / 世界观面板
- [ ] M4:打包 / 部署
