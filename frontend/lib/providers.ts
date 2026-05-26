import type { LlmAuthType } from "./api/endpoints/settings";

export interface ProviderPreset {
  id: string;
  label: string;
  provider: "anthropic" | "openai";
  model: string;
  base_url: string;
  auth_type: LlmAuthType;
  hint?: string;
}

export const PROVIDER_PRESETS: ProviderPreset[] = [
  {
    id: "anthropic-direct",
    label: "Anthropic 官方直连",
    provider: "anthropic",
    model: "claude-sonnet-4-5",
    base_url: "",
    auth_type: "api_key",
    hint: "用 x-api-key,需国际网络",
  },
  {
    id: "anthropic-bearer",
    label: "Anthropic 网关 (Bearer)",
    provider: "anthropic",
    model: "claude-sonnet-4-5",
    base_url: "",
    auth_type: "bearer",
    hint: "Bedrock proxy / Claude-Code 代理常用",
  },
  {
    id: "openai",
    label: "OpenAI 官方",
    provider: "openai",
    model: "gpt-4o-mini",
    base_url: "https://api.openai.com/v1",
    auth_type: "api_key",
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    provider: "openai",
    model: "deepseek-chat",
    base_url: "https://api.deepseek.com/v1",
    auth_type: "api_key",
    hint: "OpenAI 兼容接口",
  },
  {
    id: "moonshot",
    label: "Moonshot Kimi",
    provider: "openai",
    model: "moonshot-v1-32k",
    base_url: "https://api.moonshot.cn/v1",
    auth_type: "api_key",
  },
  {
    id: "ollama",
    label: "Ollama (本地)",
    provider: "openai",
    model: "qwen2.5:7b",
    base_url: "http://localhost:11434/v1",
    auth_type: "api_key",
    hint: "本地无需 API Key,任意填即可",
  },
  {
    id: "custom",
    label: "自定义 OpenAI 兼容",
    provider: "openai",
    model: "",
    base_url: "",
    auth_type: "api_key",
  },
];
