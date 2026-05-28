/**
 * 简易 fetch 封装。
 *
 * 两种部署形态:
 *  1. 开发期:前端跑 3000,后端跑 8000 → NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
 *  2. 打包后:exe 启动后端同时托管前端静态文件 → 同源请求,BASE 留空
 */

const BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/+$/, "");

function url(path: string): string {
  return BASE + path;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown, message: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

// dev mode 启动顺序:用户跑 npm run dev 后立刻打开 :3000,但后端 uvicorn 的
// lifespan 还要 3-5 秒才完成 db.init / SQLAlchemy create_all。这段窗口 next dev
// 的 rewrites 转发到 :8000 会拿到 ECONNREFUSED 或 502 → 浏览器看到 500。
// 对幂等的 GET 做几次短重试,把启动窗口期吃掉,不打扰用户。
const RETRY_DELAYS_MS = [400, 800, 1500];

function shouldRetry(method: string, status: number | null): boolean {
  if (method !== "GET") return false;
  if (status === null) return true; // network error / fetch rejected
  return status >= 500; // 5xx 一般是后端临时不可用
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  let lastErr: unknown = null;
  for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt++) {
    let res: Response;
    try {
      res = await fetch(url(path), {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (e) {
      lastErr = e;
      if (shouldRetry(method, null) && attempt < RETRY_DELAYS_MS.length) {
        await new Promise((r) => setTimeout(r, RETRY_DELAYS_MS[attempt]));
        continue;
      }
      throw e;
    }
    if (!res.ok) {
      if (shouldRetry(method, res.status) && attempt < RETRY_DELAYS_MS.length) {
        // 5xx:消耗一下 body 释放连接,然后重试
        await res.text().catch(() => "");
        await new Promise((r) => setTimeout(r, RETRY_DELAYS_MS[attempt]));
        continue;
      }
      // 只能读一次 body:先拿 text,再尝试 JSON 解析
      const raw = await res.text();
      let detail: unknown = raw;
      try {
        detail = JSON.parse(raw);
      } catch {
        // 保持 raw 文本
      }
      const msg =
        (detail && typeof detail === "object" && "detail" in detail
          ? String((detail as { detail: unknown }).detail)
          : raw) || `HTTP ${res.status}`;
      throw new ApiError(res.status, detail, msg);
    }
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  }
  // 不会到这里;让 TS 满意
  throw lastErr instanceof Error ? lastErr : new Error("request failed");
}

export const http = {
  get: <T>(p: string) => request<T>("GET", p),
  post: <T>(p: string, body?: unknown) => request<T>("POST", p, body),
  put: <T>(p: string, body?: unknown) => request<T>("PUT", p, body),
  del: <T>(p: string) => request<T>("DELETE", p),
};

export const apiUrl = url;
