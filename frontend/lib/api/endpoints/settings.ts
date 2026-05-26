import { http, apiUrl } from "../http";

export type LlmAuthType = "api_key" | "bearer";

export interface LlmProfile {
  id: string;
  name: string;
  provider: string;
  model: string;
  api_key: string;
  base_url: string;
  auth_type: LlmAuthType;
  max_tokens: number;
  temperature: number;
  extra_headers: Record<string, string>;
  verified_at: string | null;
}

export type LlmProfileDraft = Partial<LlmProfile> & {
  name: string;
  provider: string;
  model: string;
};

export interface ProfileTestEvent {
  event:
    | "started"
    | "first_token"
    | "chunk"
    | "done"
    | "error"
    | "timeout";
  data: Record<string, unknown>;
}

export const settingsApi = {
  list: () => http.get<LlmProfile[]>("/api/settings/llm-profiles"),
  upsert: (body: LlmProfileDraft) =>
    http.post<LlmProfile>("/api/settings/llm-profiles", body),
  remove: (id: string) =>
    http.del<void>(`/api/settings/llm-profiles/${id}`),
  getActive: () =>
    http.get<LlmProfile | null>("/api/settings/llm-profiles/active"),
  activate: (id: string) =>
    http.post<void>(`/api/settings/llm-profiles/${id}/activate`),
  importText: (text: string, fallbackName = "") =>
    http.post<LlmProfile>("/api/settings/llm-profiles/import", {
      text,
      fallback_name: fallbackName,
    }),
  testStream: async (
    profile: LlmProfileDraft,
    opts: {
      signal?: AbortSignal;
      onEvent: (e: ProfileTestEvent) => void;
      onError?: (err: unknown) => void;
      onDone?: () => void;
    },
  ) => {
    const resp = await fetch(apiUrl("/api/settings/llm-profiles/test"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile }),
      signal: opts.signal,
    });
    if (!resp.ok || !resp.body) {
      opts.onError?.(new Error(`HTTP ${resp.status}`));
      return;
    }
    const reader = resp.body.getReader();
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
          let event = "message";
          let data = "";
          for (const line of block.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            else if (line.startsWith("data:")) data += line.slice(5).trim();
          }
          let parsed: Record<string, unknown> = {};
          if (data) {
            try {
              parsed = JSON.parse(data);
            } catch {
              parsed = { raw: data };
            }
          }
          opts.onEvent({ event: event as ProfileTestEvent["event"], data: parsed });
        }
      }
      opts.onDone?.();
    } catch (e) {
      opts.onError?.(e);
    }
  },
};
