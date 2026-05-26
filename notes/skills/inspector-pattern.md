# Inspector Pattern · Agent-First UI

## 问题

LLM agent 自动改了项目数据,用户在聊天框,**怎么知道哪儿被改了**?

错的方向:
- 改完弹 toast "已更新章节" — 用户没在看那块,toast 就是噪声
- 全屏切到"章节"页验证 — 打断对话流
- 改完无提示 — 用户对 agent 失去信任

对的方向:**所有项目状态在主屏旁边常驻,被改的地方亮一下,用户想看就看**。

## 套路

### 1. 双栏 shell 替代 Tab 路由

```
┌──────────────────────────────────────┬──────────────────────┐
│                                      │ ▾ 概览          ●    │
│  AI 对话(主区,自适应宽度)         │ ▾ 章节 (12)     ●    │
│                                      │ ▸ 人物 (5)            │
│                                      │ ▸ 世界观 (3)          │
└──────────────────────────────────────┴──────────────────────┘
```

- 左:agent 聊天(单独 url,无 tab 参数)
- 右:Accordion section 列表,每节默认收 / 默认开自配
- 折叠态:窄轨 36px + 4 图标,有未读的图标上 pulse dot

### 2. "未读修改"是状态机,不是 toast

```ts
// inspector-changes.tsx
const [unread, setUnread] = useState<Set<SectionKey>>(new Set());

window.addEventListener("data_changed", (e) => {
  const { tool_name, affects } = e.detail;
  // 优先用 tool_name 精准定位
  if (TOOL_TO_SECTION[tool_name]) mark(TOOL_TO_SECTION[tool_name]);
  // 兜底:tree → chapters/characters/world 三个都 mark
  else for (const k in affects) mark(AFFECTS_FALLBACK[k]);
});

// section 展开时清自己的 dot —— 已经在看就不算"未读"
useEffect(() => { if (isOpen && hasUnread) clear(key); }, [isOpen]);
```

### 3. tool_name → section 反推表

后端在 `tool_result` 事件里多带 `tool_name`,前端硬编码:

```ts
const TOOL_TO_SECTION = {
  set_synopsis: "overview",
  add_chapter: "chapters",
  upsert_character: "characters",
  upsert_world: "world",
  // ...
};
```

精准 > 用 `affects` 兜底。`affects` 只是粗粒度的"影响哪一类",
section dot 要细到具体那一节。

### 4. 编辑跳转 = Inspector 只读 + Dialog 弹窗

不要在 Inspector 里做复杂的内联编辑(空间不够)。
点条目 → Dialog,Dialog 里复用现有表单组件。

## 反例

- ❌ 在 AppHeader 一个角放红点 "项目有更新":用户不知道哪一节,要点开看。
- ❌ 每次 tool_result 弹 toast "AI 修改了 xxx":3 个工具串调就 3 条 toast 刷屏。
- ❌ 用 tab 路由(`?tab=overview`)切换 inspector 内 section:
  router 切换有延迟,而且 inspector 应该多节同开。Accordion 才对。
- ❌ Inspector 实时双向绑定 agent 修改:数据流复杂,且 agent 改到一半 UI 抖。
  → "事件触发 reload"够用,且统一走 `useDataChanged`。

## 真实位置

- Shell: `frontend/components/workspace/shell.tsx`
- Inspector 容器: `frontend/components/workspace/inspector/index.tsx`
- 状态机: `frontend/lib/store/inspector-changes.tsx`
- 编辑 Dialog 集中: `frontend/components/workspace/inspector/edit-dialogs.tsx`
