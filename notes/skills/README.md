# skills · 跨项目通用方法论

这里收集的不是 book-creater-agent 的实现细节(那些在 `../../DEV_NOTES.md`),
而是**可以搬到下一个项目继续用**的设计套路。每篇按"问题 / 套路 / 反例"三段写。

| 文件 | 适用场景 |
|------|---------|
| [agent-loop-design.md](agent-loop-design.md) | 写一个能调工具的 LLM agent 循环 |
| [sse-streaming.md](sse-streaming.md) | 后端 SSE 事件协议 + 前端 EventSource 消费 |
| [inspector-pattern.md](inspector-pattern.md) | Agent-First UI:聊天为主、状态环绕、未读高亮 |
| [refresh-avalanche.md](refresh-avalanche.md) | 多事件合并刷新,避免每个 tool_result 都全量重载 |
| [hexagonal-python.md](hexagonal-python.md) | 用 Python 包路径 + Protocol 模拟六边形架构 |

---

## 添加新 skill 的标准

1. 至少在 2 个项目里被验证过(避免 over-generalize)
2. 标题用动词(`*-design` / `*-pattern` / `*-streaming`),搜得到
3. 每篇必须包含**反例**:不这样做会变成什么样
4. 引用真实代码位置(`backend/app/xxx.py:N`)而不是伪代码,空气架构没人看
