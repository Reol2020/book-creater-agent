import { apiUrl } from "../http";
import { postSse, type SseHandlers } from "../sse";

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export type ConfirmPolicy = "default" | "auto" | "confirm-all";

export interface AgentStreamBody {
  messages: ChatMessage[];
  project_id: string;
  confirm_policy?: ConfirmPolicy;
  system?: string;
}

export const chatApi = {
  stream(
    body: { messages: ChatMessage[]; system?: string },
    handlers: SseHandlers,
  ) {
    return postSse(apiUrl("/api/chat/stream"), body, handlers);
  },
  agentStream(body: AgentStreamBody, handlers: SseHandlers) {
    return postSse(apiUrl("/api/chat/agent-stream"), body, handlers);
  },
};
