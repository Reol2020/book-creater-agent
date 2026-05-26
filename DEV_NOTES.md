# book-creater-agent 开发笔记

> 持续更新。每次解决新问题、加新功能、做关键决策都在这里追加一节。
> 目的:让下一个写代码的人(包括未来的自己)一眼看到坑在哪、为什么这么写。

**桌面版前身 `novel_agent` 的 18 节坑沉淀在 `D:\extendCode\DEV_NOTES.md`,核心结论已在下面 #1 节摘要。**

---

## 项目当前结构

```
book-creater-agent/
├── backend/                            # Python / FastAPI
│   └── app/
│       ├── domain/                     # 纯业务,零框架依赖
│       ├── ports/                      # Protocol 接口
│       ├── application/                # 用例服务
│       ├── adapters/
│       │   ├── inbound/api/            # FastAPI routers (REST + SSE)
│       │   └── outbound/
│       │       ├── persistence/sqlite/
│       │       ├── knowledge/chroma/
│       │       └── llm/direct/
│       └── config/                     # DI 装配
├── frontend/                           # Next.js 15 + TS + Tailwind + shadcn + TipTap
│   ├── app/                            # 页面层
│   ├── features/                       # 业务能力切分
│   ├── components/                     # ui (shadcn) + editor
│   └── lib/api/                        # 后端契约层
├── DEV_NOTES.md
└── README.md
```

---

## 1. 桌面版传承:已经踩过的坑(摘要)

完整版在 `D:\extendCode\DEV_NOTES.md`。这里只列结论,避免在 web 版重蹈覆辙。

### 1.1 Anthropic SDK 双鉴权(直连 + Bedrock 网关)

- 直连官方 → `x-api-key` 头
- Bedrock / OpenRouter / 国内网关 → `Authorization: Bearer xxx`
- **必须看 base_url 的形态决定鉴权方式,不能用单一字段**

### 1.2 Bedrock 路由的 Claude 不接受 `temperature`

- 部分网关收到 `temperature` 直接 400
- 解法:`_run_with_retry` 检测到这个错就剥离 `temperature` 重发一次

### 1.3 LLM 默认 `max_tokens` 必须够大

- 桌面版默认 4096 → 大纲生成被截断到 ~3000 字,且 LLM 不报错
- web 版起步直接 16384,profile 可调
- 注意:`min(profile.max_tokens, request.max_tokens)` 的 cap 逻辑别忘

### 1.4 流式 token 高频写入会触发 UI 崩溃

- 桌面版 PySide6 上是 SIGSEGV
- web 版前端用 `requestAnimationFrame` 或 50ms 节流批量插入
  TipTap 节点,**不要每个 token 直接 dispatch transaction**

### 1.5 模态对话框被遮住会让用户以为程序卡死

- 桌面版 `ConfirmToolDialog` 被主窗口遮住 → "未响应"
- web 版危险操作确认改用**前端组件 + 强制 z-index 顶层 + 标题栏 toast 提示**

### 1.6 Agent 多轮工具调用结束后,UI 不要全量刷新

- 桌面版每个工具 result 触发一次全量 reload → 主线程被塞死
- web 版策略:中间过程仅 SSE 推增量;前端只更新对应 feature slice;
  完整刷新留到 agent 整轮结束 1 次

### 1.7 项目数据格式(桌面版用 JSON 文件)

- web 版改用 SQLite 规范化表 + JPA 风格 ORM
- 但 `domain/models.py` 仍是纯 dataclass,**不依赖** SQLAlchemy 实体
- 这是为了未来若回归"嵌入式 / JSON 文件"模式时,domain 层零改动

---

## 2. 架构决策:六边形 / Ports & Adapters

**决策**:不搞 Maven 多模块那种物理隔离,Python 用包路径 + 单向依赖约束实现六边形。

**约束**(代码评审时检查):
- `app/domain/**` 和 `app/ports/**` **不允许** import `fastapi / sqlalchemy /
  chromadb / anthropic / openai`
- `app/application/**` 只 import `domain` 和 `ports`,通过构造器注入实现
- `app/adapters/outbound/**` 各自实现一个 Port
- `app/config/container.py` 是**唯一**装配实现的地方
- `app/main.py` 不直接 import adapter,只 import `config` 拿到组装好的 app

**收益**:换 SQLite → Postgres / 换 Chroma → Qdrant / 抽离嵌入式版本只动 adapter。

> 注意:Python 不像 Java 有编译期的 module-path 隔离,反向 import 不会报错。
> 靠人工审 + 可选 import-linter 工具兜底。

---

## 3. LLM Provider 抽象

**桌面版有 `core/llm_client.py` 660 行**,做了 Anthropic / OpenAI 双协议
适配 + Bedrock 重试 + tool_use 翻译。**不直接复用**(同步 API + Qt 耦合),
但其上的协议抽象思想保留。

新设计:
- `ports/llm_provider.py` 定义 `LlmProvider` Protocol
  - `chat_stream(messages, system, ...) -> AsyncIterator[str]`
  - `chat_with_tools(messages, tools, system, ...) -> AssistantTurn`
- `adapters/outbound/llm/direct/` 用官方 `anthropic` / `openai` async SDK 实现
- 多 profile / 重试 / token 计量包在 adapter 内部,业务层不感知

---

## 4. SSE 流式约定

后端用 `StreamingResponse(media_type="text/event-stream")`,事件格式:

```
event: token
data: {"text": "他"}

event: tool_call
data: {"id": "...", "name": "add_chapter", "args": {...}, "risky": true}

event: tool_result
data: {"id": "...", "ok": true, "summary": "..."}

event: confirm_required
data: {"id": "...", "name": "delete_chapter", "args": {...}}

event: done
data: {"text": "...full..."}

event: error
data: {"message": "...", "detail": "..."}
```

前端用 `EventSource` 监听各 event;`confirm_required` 弹模态,
用户点击后 `POST /api/agent/confirm/{id}` 异步握手,**不阻塞 SSE 主流**。

---

## 5. Agent 内核 + RAG(2026-05-26)

后端最小可运行 agent loop 已落地:

```
backend/app/
├── prompts/                 # system/continue/summarize/extract 4 个模板,统一吃 ProjectContext
├── skills/                  # 13 个工具(meta/character/world/chapter)
│   ├── base.py              # Skill Protocol、SideEffect 字段(create/update/delete/read/compose)
│   └── registry.py          # build_default_registry() 一次注册,dispatch 转发
├── application/
│   ├── agent_service.py     # MAX_TOOL_ITERS=8 主循环;按 provider 拼 tool_use 消息
│   └── context_builder.py   # 按 token 预算切片,可选触发 RAG 检索
├── ports/chapter_retriever.py
└── adapters/outbound/persistence/sqlite/chapter_retriever.py  # FTS5 + 中文 bigram
```

**已踩过的坑**:
- SQLAlchemy AsyncSession 的 `connection()` 是 transactional,`exec_driver_sql` 写入后**必须 `await s.commit()`**,否则 FTS 索引一直空(以为分词器坏了排查半天)。
- `Anthropic` 与 `OpenAI` 的 tool_call → tool_result 消息壳完全不同。Anthropic 是 `content: [{type:"tool_use"…}]` + `content: [{type:"tool_result"…}]`,OpenAI 是 `tool_calls` + `role:"tool"`。**抽象时按 provider 分两个 helper,不要试图统一**。
- `python` 在 Win 上可能解析到 Microsoft Store 的 stub(返回 49 退出码、零输出),开发期一律 `./.venv/Scripts/python.exe` 或显式 `py -3.13`。
- chromadb 在 Python 3.14 没轮子 → 改 sqlite-vec 又麻烦,**最小 RAG 选 SQLite FTS5 + bigram**,自己 `_bigrams()` 切中文,够用。

---

## 6. Workspace UI 重构:从 Tab 到 Agent-First IDE(2026-05-26)

**问题**:旧版 `app/workspace/page.tsx` 把 AI 助手做成 5 个平级 Tab 之一(概览/章节/人物/世界观/AI 助手),
违背产品定位。用户进项目还要先点一下侧栏才能开始对话。

**重构后(单层 shell)**:
```
WorkspaceShell
├── AppHeader  (项目名 · 题材 · [📖 阅读] · [⏵ 折叠 inspector])
├── AssistantPanel        ← 主区,自适应宽度
└── Inspector             ← 右 360px / 折叠 36px 窄轨
    └── Accordion: 概览 / 章节 / 人物 / 世界观
```

URL 简化:`?id=X&tab=Y` → `?id=X`(老链接 useEffect 自动 replace)。

**关键设计**:

1. **未读修改追踪** — `lib/store/inspector-changes.tsx` 维护 `Set<sectionKey>`,
   监听 `window.dispatchEvent("data_changed", { tool_name, affects })`,
   按 tool_name 反推 section(`set_synopsis → overview` / `add_chapter → chapters` / …),
   tool_name 缺失则按 `affects` 兜底(`tree → chapters/characters/world` 三个都 mark)。
   section 展开时清自己的 dot —— 已经在看就不需要红点了。
2. **折叠态窄轨** — 4 图标 + 有未读的 pulse dot,手机 / 小屏默认折叠,`localStorage` 记忆。
3. **Reader 全屏** — Radix Dialog + portal,左 240px 目录 + 中 max-w-2xl 正文,
   ESC 关闭、上下章按钮、聊天上下文不丢。

**已踩过的坑(对照桌面版 #18 复盘)**:

- **18.1 刷新雪崩复刻** — 一轮 agent 调 5 个 tool,每个 `data_changed` 事件触发
  3 个 section 各自 reload,最坏 15 次 API 调用。
  → 修法:`useDataChanged` 内部 `setTimeout(120ms)` 合并,
  保证 burst 内只 reload 1 次(`frontend/lib/hooks/use-data-changed.ts`)。
- **JSX in `.ts` 文件** — Provider 写 JSX 时文件后缀必须 `.tsx`。
  TypeScript 报错信息很迷糊(`'>' expected`),记住第一时间检查后缀。
- **Radix Accordion CSS 动画依赖** — `data-[state=closed]:animate-accordion-up` 需要在
  `tailwind.config.ts` 的 `keyframes` 显式定义 `accordion-up/down`,
  shadcn/ui 文档没强调,缺了不报错只是不动画。
- **`React.KeyboardEvent.isComposing` 类型** — 直接 `e.isComposing` TS 不认,
  要 `(e.nativeEvent as { isComposing?: boolean }).isComposing`。
  IME 中文输入法 Enter 误触发问题,桌面版 #9 也踩过。
- **`setTurns` updater 内捕获工具名** — 我在 `setTurns(prev => …)` 的 updater 里
  通过闭包写外层变量(`resolvedToolName = t.name`),依赖 React 18 的 setState updater
  同步执行特性。可读性差,**未来用 ref 重写**。
- **跨 section 重复 reload** — chapters/characters/world 三个 section 都听 `tree`,
  `add_chapter` 只该刷 chapters。短期靠 ① 上面的 debounce 兜底 + ② tool_name 精确推断
  section dot;后续可在 `useDataChanged` 加 tool_name 过滤参数。

---

## 7. 通用 skills 笔记目录(`notes/skills/`)

跨项目复用的方法论沉淀,不与 book-creater-agent 强绑定。详见 `notes/skills/README.md`。
当前包含:
- `agent-loop-design.md` — Anthropic + OpenAI 双协议工具循环骨架
- `sse-streaming.md` — FastAPI + 前端 EventSource 的事件协议
- `inspector-pattern.md` — Agent 改动后"在哪里"的可视化(本次新加)
- `refresh-avalanche.md` — 多事件合并刷新(桌面 + web 双版本通用)
- `hexagonal-python.md` — Python 包路径 + Protocol 实现六边形

---

## 变更历史

| 日期 | 内容 |
|------|------|
| 2026-05-26 | 初始化:Python + FastAPI + SQLite + Chroma + Next.js + TipTap;六边形目录骨架 |
| 2026-05-26 | Agent 内核 + 13 skills + SQLite FTS5 RAG(prompts/skills/agent_service/context_builder) |
| 2026-05-26 | Workspace 改 Agent-First 双栏 shell;新增 Inspector / Reader / 未读 dot;`useDataChanged` 加 debounce |
