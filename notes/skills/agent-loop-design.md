# Agent Loop:能调工具的 LLM 循环

## 问题

把 LLM 从"聊天框"升级到"能动手改项目数据的 agent",要解决三件事:

1. 让 LLM 知道有哪些工具(schema)
2. 拿到 LLM 的工具调用,执行,把结果回灌
3. 多轮往返,直到 LLM 说"我说完了"

Anthropic 与 OpenAI 的 tool call 消息壳**完全不同**,但可以共享外层骨架。

## 套路

### 1. Skill = (schema + 执行函数 + 副作用标签)

```python
# backend/app/skills/base.py
@dataclass
class FunctionSkill:
    name: str
    description: str
    parameters: dict          # JSON Schema
    side_effect: SideEffect   # "create" | "update" | "delete" | "read" | "compose"
    handler: Callable[[SkillContext, dict], Awaitable[SkillResult]]
```

`side_effect` 不是装饰糖,是**确认策略 + UI 卡片**的依据:
`create` 默认放行、`update/delete` 默认确认、`read` 完全静默。

### 2. Registry 一处注册 + 双协议导出

```python
class SkillRegistry:
    def anthropic_tools(self) -> list[dict]: ...   # {name, description, input_schema}
    def openai_tools(self) -> list[dict]: ...      # {type:"function", function:{...}}
    async def dispatch(self, name, ctx, args) -> SkillResult: ...
```

**不要试图统一两家的工具消息壳**。Anthropic 是 `content: [{type:"tool_use"…}]` 块,
OpenAI 是 `tool_calls: [{id, function:{…}}]` 字段,两个 `_assistant_message` /
`_tool_results_messages` helper 分写,反而最简单。

### 3. 主循环:状态机比 while 直观

```
while True:
    yield "started"
    response = await llm.chat_with_tools(messages, tools, ...)
    if response.text:        yield "token"...
    if not response.tool_calls:
        yield "done"; break
    for tc in response.tool_calls:
        yield "tool_call"
        result = await registry.dispatch(...)
        yield "tool_result"
        messages.extend(_tool_results_messages([result]))
    if iter > MAX_TOOL_ITERS:
        yield "error: too many iterations"; break
```

设上限(`MAX_TOOL_ITERS=8`)。LLM 会自循环。

### 4. 让前端感知"哪个 section 被改了"

工具的 `side_effect` 不够,前端还要知道**改的是哪类数据**。
做法:每个 SkillResult 多带一个 `affects: {meta?: bool, tree?: bool, doc?: bool}`,
前端订阅 `data_changed` 事件按 affects 决定刷哪块。

更精准的方式:在 SSE 事件 detail 里再带 `tool_name`,前端有
`tool → section` 的反推表(见 `inspector-pattern.md`)。

## 反例

- ❌ 在 application 层直接 import `anthropic` SDK:换 provider 就得改业务代码。
  → 套 `LlmProvider` Protocol,SDK 调用全在 adapter。
- ❌ 把 tool 的执行做成"先生成 SQL,LLM 决定是否执行":延迟 + 风险都倍增。
  执行决策应在**工具内部**,LLM 只看 schema。
- ❌ 工具 result 的 text 直接塞 LLM 工作消息,不做摘要:多轮后 context 爆炸。
  → SkillResult 提供 `summary`(给 LLM)和 `display`(给 UI)两个字段。

## 真实位置

- 协议: `backend/app/ports/llm_provider.py`
- 双协议适配: `backend/app/adapters/outbound/llm/direct/provider.py`
- 主循环: `backend/app/application/agent_service.py`
- 13 个 skills: `backend/app/skills/project_skills.py`
