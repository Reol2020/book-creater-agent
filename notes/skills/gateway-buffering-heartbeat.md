# 网关缓冲 + 心跳事件

## 问题

LLM 直连 Anthropic / OpenAI 时,流式 SSE 是逐 token 出的,前端可以 0.x 秒看到首字。

但走第三方网关(Mify、PPIO、Bedrock proxy 等)时,网关会**把上游的 SSE 重新打包后再 flush**:

- `text_delta` 还算细,几百毫秒一批
- `input_json_delta`(tool_use 的 input,长章节正文走这里)被攒成大块,**实测 Mify 上 30~60s 才 flush 一次**

用户场景:让 AI 写一章 ~3000 字的小说

```
0.0s  user: 写第3章, 2500 字
3.8s  text_delta: "好的,我用 ..." (TTFT)
8.8s  content_block_start tool_use=add_chapter
12.8s input_json_delta chars=20  ← 第一批
14.8s ~ 73.9s  完全静默 59 秒  ← 网关在缓冲
73.9s input_json_delta chars=312
74.3s content_block_stop chars=3588 ← 一次性 flush 完
74.3s tool_call dispatched
84.7s done
```

那 59 秒里前端只看到 "思考中…",**用户怀疑卡死,按 Ctrl-C / 关 tab / 提工单**。

## 套路

### 1. 后端:静默超阈值就发心跳

不要 `async for ev in upstream` 一把梭,改成 **queue + 后台 consumer + 主循环带超时**:

```python
# backend/app/application/agent_service.py
queue: asyncio.Queue = asyncio.Queue()
sentinel = object()

async def _consume():
    try:
        async for ev in self._llm.chat_with_tools_stream(...):
            await queue.put(ev)
    except Exception as e:
        await queue.put(("__exc__", e))
    finally:
        await queue.put(sentinel)

consumer = asyncio.create_task(_consume())
silence_started_at = time.monotonic()
while True:
    try:
        item = await asyncio.wait_for(queue.get(), timeout=4.0)
    except asyncio.TimeoutError:
        # 上游静默 ≥4s,不取消上游 stream,只发心跳
        yield {"event": "heartbeat",
               "data": {"silent_seconds": round(time.monotonic() - silence_started_at, 1)}}
        continue
    silence_started_at = time.monotonic()
    if item is sentinel: break
    ...
```

**两条铁律**(踩坑得来的):

1. **千万不要 `await asyncio.wait_for(gen.__anext__(), timeout=…)`**:
   超时会触发生成器 cancel,这层 cancel 会传到底层 SDK 的 HTTP body reader,
   `httpcore.receive_response_body.failed exception=CancelledError()`。
   你以为是"上游卡死",其实是你自己把它掐了。
   **必须用后台 task + queue 解耦**,主循环超时不影响上游。

2. **心跳阈值 4s** 是个折中:
   - 比正常 `tool_progress`(~0.8s 一次)间隔大,避免抢资源;
   - 比 5s 的"用户开始焦虑"阈值小,空白期能至少跳两次;
   - 比 10s+ 太长,网关静默期前几秒就静默,用户已经在数秒。

### 2. 前端:把心跳渲染成"活跃徽章"

前端拿到 `heartbeat` 不需要做业务,只需更新一个 `lastHeartbeatAt` state,
`PendingHint` / `ProgressCard` 上读它显示"● 后端活跃 · Ns 前":

```tsx
} else if (e.event === "heartbeat") {
  setLastHeartbeatAt(Date.now());
}

// ProgressCard:
{hbAge !== null && (
  <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] text-emerald-600">
    ● 后端活跃 · {hbAge}s 前
  </span>
)}
```

要让秒数滚动,需要 `setInterval(forceTick, 1000)` 在 streaming 期间常驻
(光靠 heartbeat 4s 跳一次,UI 就一卡一卡)。

### 3. UI 文案:把"网关缓冲"写出来

只要你知道是网关行为,**直接告诉用户**比让他猜更好:

> 字数分批接收(网关缓冲),写完会自动落到右侧项目

把秒数提到主指标位置(大字、`tabular-nums`),字数挪到次要位置 ——
因为网关缓冲时字数会冻结几十秒,秒数则一直在动,符合用户对"时间在过"的直觉。

## 反例

- ❌ 用 `EventSource` + 自动重连:网关静默期足够触发浏览器 default timeout,
  连接被重置,工具回合丢了。**主动心跳 + fetch+ReadableStream** 是稳的。
- ❌ 把 partial_json 内容塞进 SSE 推给前端做活体反馈:用户不需要看半截 JSON,
  只发字符数(`chars`)就够了,既省带宽又保 UX。
- ❌ 在前端搞 "客户端心跳 ping":心跳是要证明**上游 + 后端**整条链路,不只是 socket。
  必须由后端在事件循环里发,才能反映 agent 真实状态。
- ❌ 心跳事件带敏感字段(model 名、prompt 摘要):本来是给前端看活体的,
  顺手塞业务数据会污染协议。心跳只携带 `silent_seconds`,业务事件归业务事件。

## 真实位置

- 后端心跳 + queue 模式: `backend/app/application/agent_service.py:96-158`
- Anthropic raw events 解析(text_delta / input_json_delta): `backend/app/adapters/outbound/llm/direct/provider.py:337-388`
- 前端心跳消费: `frontend/components/workspace/assistant-panel.tsx`(`lastHeartbeatAt` state)

## 适用范围

任何"前端 ↔ 后端 ↔ 第三方 LLM 网关"三层链路,只要中间层可能 buffer >= 5s,
都应当上心跳。直连 Anthropic / OpenAI 官方 API 时心跳几乎不会触发(token 间隔小),
但也不会出问题,**默认开启没坏处**。
