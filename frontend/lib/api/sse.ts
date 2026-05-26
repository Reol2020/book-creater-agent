/**
 * SSE 客户端 —— 后端用 POST 发,所以原生 EventSource 不能用。
 * 这里手动用 fetch + ReadableStream 解析 `event: xxx\ndata: {...}\n\n`。
 */

export type SseEvent = { event: string; data: unknown };

export interface SseHandlers {
  onEvent: (e: SseEvent) => void;
  onError?: (err: unknown) => void;
  onDone?: () => void;
  signal?: AbortSignal;
}

export async function postSse(
  url: string,
  body: unknown,
  handlers: SseHandlers,
): Promise<void> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(body),
    signal: handlers.signal,
  });
  if (!res.ok || !res.body) {
    handlers.onError?.(new Error(`HTTP ${res.status}`));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buf = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      let idx;
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        const block = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const event = parseEventBlock(block);
        if (event) handlers.onEvent(event);
      }
    }
    handlers.onDone?.();
  } catch (err) {
    handlers.onError?.(err);
  }
}

function parseEventBlock(block: string): SseEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (!line) continue;
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (dataLines.length === 0) return null;
  const raw = dataLines.join("\n");
  try {
    return { event, data: JSON.parse(raw) };
  } catch {
    return { event, data: raw };
  }
}
