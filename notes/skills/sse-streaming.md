# SSE 流式协议

## 问题

LLM 流式响应 + 工具调用 + 错误 + 用户确认,前端要按事件类型切换 UI。
原始 newline-delimited JSON 不够,标准 `EventSource` 又只支持单事件名。

## 套路

### 1. 一种连接,多种 event,统一 data=json

后端 `text/event-stream`,严格遵守 `event: <name>\ndata: <json>\n\n`:

```
event: started
data: {"agent_id":"..."}

event: token
data: {"text":"他抬起头"}

event: tool_call
data: {"id":"call_1","name":"add_chapter","arguments":{...},"side_effect":"create"}

event: tool_result
data: {"id":"call_1","ok":true,"text":"已新增第3章","affects":{"tree":true}}

event: error
data: {"title":"超出 token","detail":"max_tokens=4096"}

event: done
data: {}
```

事件类型固定:`started / token / tool_call / tool_result / confirm_required / error / done`。

### 2. 前端:fetch + ReadableStream 而不是 EventSource

`EventSource` 不能传 POST body / 自定义 header。改用 `fetch` + 手动 SSE 解析:

```ts
// frontend/lib/api/endpoints/chat.ts
async function agentStream(body, { onEvent, signal }) {
  const res = await fetch("/api/chat/agent-stream", {
    method: "POST", body: JSON.stringify(body), signal,
  });
  const reader = res.body!.getReader();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += new TextDecoder().decode(value);
    let idx;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, idx); buf = buf.slice(idx + 2);
      const ev = parseSSE(block);  // 解出 event + data
      onEvent(ev);
    }
  }
}
```

### 3. 异步 generator → SSE 序列化

后端这一步老踩 watchdog 坑:

```python
async def event_stream():
    try:
        async for ev in agent_service.run(req):
            yield f"event: {ev['event']}\ndata: {json.dumps(ev['data'], ensure_ascii=False)}\n\n"
    except asyncio.CancelledError:
        # 用户断开,不要 raise,直接 return,否则 starlette 报红
        return
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'title':'unhandled','detail':str(e)})}\n\n"
```

`StreamingResponse(event_stream(), media_type="text/event-stream")`,
nginx / IIS 反代时一定要关 buffering(`X-Accel-Buffering: no`)。

## 反例

- ❌ 把所有事件塞在一个 `event: message` 里,前端用 `data.type` 分流。
  正经实现就是利用 SSE 的 `event:` 字段,客户端可读性更高。
- ❌ 把超大正文塞进单条 `event: token`。LLM token 通常很小,**真有大块输出
  也要切片**,否则前端 `JSON.parse` 阻塞。
- ❌ 错误用 HTTP 4xx 返回:连接已经升级到流,中途不能改 HTTP 状态码。
  错误改用 `event: error` + 客户端展示。

## 真实位置

- 后端: `backend/app/adapters/inbound/api/chat.py` (`/api/chat/agent-stream`)
- 前端解析: `frontend/lib/api/endpoints/chat.ts` (`agentStream`)
- 消费方: `frontend/components/workspace/assistant-panel.tsx`
