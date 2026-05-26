"""把任意来源(env JSON / 原生 JSON / curl)解析成 LlmProfile draft。

四种 JSON shape 沿用桌面版 parse_profile_json 的算法 (见 D:\\extendCode\\novel_agent\\core\\profile_import.py),
新增第 5 种:curl 命令。所有解析都不持久化、不发请求,只产出 draft 实例。
"""
from __future__ import annotations

import json
import re
import shlex
from urllib.parse import urlparse

from app.domain.models import LlmAuthType, LlmProfile


class ProfileParseError(ValueError):
    """无法识别输入文本。"""


# ---------------------------------------------------------------- 主入口
def parse_profile_text(text: str, fallback_name: str = "") -> LlmProfile:
    """先按 curl 试,再按 JSON 试,失败抛 ProfileParseError。"""
    s = text.strip()
    if not s:
        raise ProfileParseError("输入为空")

    # curl 优先(很容易识别)
    if s.lower().startswith("curl") or "\ncurl" in s.lower():
        return _parse_curl(s, fallback_name)

    try:
        return _parse_json(s, fallback_name)
    except ProfileParseError:
        raise
    except json.JSONDecodeError as e:
        # 不是 JSON 也不是 curl
        raise ProfileParseError(
            f"无法识别输入。请粘贴 JSON env 或 curl 命令。({e.msg})"
        ) from e


# ---------------------------------------------------------------- JSON 四种 shape
def _parse_json(text: str, fallback_name: str) -> LlmProfile:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ProfileParseError("JSON 顶层必须是对象 {}")

    # Shape 1: 原生 LlmProfile JSON
    if any(k in data for k in ("provider", "api_key", "auth_type")):
        auth = data.get("auth_type", "api_key")
        # 兼容桌面版的 "auth_token" 旧名 → 新枚举叫 "bearer"
        if auth == "auth_token":
            auth = "bearer"
        return LlmProfile(
            name=data.get("name") or fallback_name or "导入配置",
            provider=data.get("provider", "anthropic"),
            model=data.get("model", ""),
            api_key=data.get("api_key", ""),
            base_url=data.get("base_url", ""),
            temperature=float(data.get("temperature", 0.7)),
            max_tokens=int(data.get("max_tokens", 16384)),
            extra_headers=dict(data.get("extra_headers", {}) or {}),
            auth_type=LlmAuthType(auth),
        )

    # Shape 2/3: env 风格 —— 嵌套 {"env": {...}} 或扁平
    env = data.get("env") if isinstance(data.get("env"), dict) else data
    if not isinstance(env, dict):
        raise ProfileParseError("解析失败:找不到 env 键值对")

    # Shape 2: Anthropic env
    anth_keys = (
        "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY",
        "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_REASONING_MODEL",
    )
    if any(k in env for k in anth_keys):
        token = env.get("ANTHROPIC_AUTH_TOKEN") or ""
        api_key = env.get("ANTHROPIC_API_KEY") or ""
        if token:
            key, auth = token, LlmAuthType.BEARER
        else:
            key, auth = api_key, LlmAuthType.API_KEY
        model = (
            env.get("ANTHROPIC_MODEL")
            or env.get("ANTHROPIC_DEFAULT_SONNET_MODEL")
            or env.get("ANTHROPIC_DEFAULT_OPUS_MODEL")
            or env.get("ANTHROPIC_DEFAULT_HAIKU_MODEL")
            or env.get("ANTHROPIC_REASONING_MODEL")
            or "claude-sonnet-4-5"
        )
        base_url = env.get("ANTHROPIC_BASE_URL", "") or ""
        host = urlparse(base_url).hostname if base_url else ""
        name = fallback_name or (f"Anthropic@{host}" if host else "Anthropic 导入")
        return LlmProfile(
            name=name, provider="anthropic", model=model,
            api_key=key, base_url=base_url, auth_type=auth,
        )

    # Shape 3: OpenAI 风格 env
    openai_key = env.get("OPENAI_API_KEY") or env.get("API_KEY") or ""
    base_url = (
        env.get("OPENAI_BASE_URL") or env.get("OPENAI_API_BASE")
        or env.get("BASE_URL") or ""
    )
    model = env.get("OPENAI_MODEL") or env.get("MODEL") or ""
    if not (openai_key or base_url or model):
        raise ProfileParseError(
            "无法识别此 JSON。请确认包含 ANTHROPIC_* 或 OPENAI_* 键,"
            "或符合原生 LlmProfile 字段。"
        )
    host = urlparse(base_url).hostname if base_url else ""
    name = fallback_name or (f"OpenAI@{host}" if host else "OpenAI 导入")
    return LlmProfile(
        name=name, provider="openai", model=model,
        api_key=openai_key, base_url=base_url,
        auth_type=LlmAuthType.API_KEY,
    )


# ---------------------------------------------------------------- curl
_CURL_HEADER_FLAGS = ("-H", "--header")
_CURL_DATA_FLAGS = ("-d", "--data", "--data-raw", "--data-binary")


def _parse_curl(text: str, fallback_name: str) -> LlmProfile:
    """从 curl 命令抽取 base_url、API key、model(在 body 里时)。"""
    # 把多行的 \\ 续行合并
    cleaned = re.sub(r"\\\s*\n", " ", text).strip()
    # shlex 在 Windows 上要 posix=True 才能正确处理引号
    try:
        tokens = shlex.split(cleaned, posix=True)
    except ValueError as e:
        raise ProfileParseError(f"curl 命令解析失败: {e}") from e
    if not tokens or tokens[0].lower() != "curl":
        raise ProfileParseError("不是 curl 命令")

    url = ""
    headers: dict[str, str] = {}
    body_text = ""

    i = 1
    while i < len(tokens):
        t = tokens[i]
        if t in _CURL_HEADER_FLAGS and i + 1 < len(tokens):
            kv = tokens[i + 1]
            if ":" in kv:
                k, v = kv.split(":", 1)
                headers[k.strip()] = v.strip()
            i += 2
        elif t in _CURL_DATA_FLAGS and i + 1 < len(tokens):
            body_text = tokens[i + 1]
            i += 2
        elif t in ("-X", "--request", "--location", "-L", "--compressed", "-i", "-v", "-s", "-S"):
            # 跳过单 flag,有些后面跟值
            if t in ("-X", "--request") and i + 1 < len(tokens):
                i += 2
            else:
                i += 1
        elif t.startswith("http://") or t.startswith("https://"):
            url = t
            i += 1
        else:
            i += 1

    if not url:
        raise ProfileParseError("curl 命令里找不到 URL")

    # 抽 Authorization / x-api-key / api-key
    auth_type = LlmAuthType.API_KEY
    api_key = ""
    extra: dict[str, str] = {}
    for k, v in headers.items():
        kl = k.lower()
        if kl == "authorization":
            m = re.match(r"^Bearer\s+(.+)$", v.strip(), re.IGNORECASE)
            if m:
                api_key = m.group(1)
                auth_type = LlmAuthType.BEARER
            else:
                api_key = v.strip()
                auth_type = LlmAuthType.BEARER
        elif kl in ("x-api-key", "api-key"):
            api_key = v.strip()
            auth_type = LlmAuthType.API_KEY
        elif kl in ("content-type", "accept", "anthropic-version"):
            # 标准 header,不需要保存
            if kl == "anthropic-version":
                extra[k] = v
        else:
            extra[k] = v

    # 推断 provider:URL host 含 anthropic → anthropic;否则 openai 兼容
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if "anthropic" in host:
        provider = "anthropic"
    else:
        provider = "openai"

    # 截 base_url:去掉路径里的 /v1/messages 或 /v1/chat/completions 等结尾
    base_path = parsed.path or ""
    base_path = re.sub(r"/(messages|chat/completions|completions|responses)/?$", "", base_path)
    base_url = f"{parsed.scheme}://{parsed.netloc}{base_path}".rstrip("/")

    # 试着从 body 里抠 model 字段
    model = ""
    if body_text:
        try:
            body = json.loads(body_text)
            if isinstance(body, dict):
                model = body.get("model", "") or ""
        except json.JSONDecodeError:
            pass
    if not model:
        model = "claude-sonnet-4-5" if provider == "anthropic" else "gpt-4o-mini"

    name = fallback_name or (f"{provider.title()}@{host}" if host else f"{provider} 导入")
    return LlmProfile(
        name=name, provider=provider, model=model,
        api_key=api_key, base_url=base_url,
        auth_type=auth_type, extra_headers=extra,
    )
