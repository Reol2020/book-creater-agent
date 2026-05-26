"""LlmProvider 实现:用官方 anthropic / openai SDK,async streaming。

桌面版 `core/llm_client.py` 是同步版本,这里重写为 async。但保留几个关键经验:
  - Anthropic 官方直连用 x-api-key,网关用 Bearer(profile.auth_type 区分)
  - Bedrock 路由的 Claude 不收 temperature → 收到错误就剥离重试一次
  - max_tokens 默认 16384(桌面版踩的坑,见 DEV_NOTES #1.3)
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.domain.models import (
    AssistantTurn,
    LlmAuthType,
    LlmProfile,
    ToolCall,
)
from app.ports.llm_provider import LlmProvider

_log = logging.getLogger(__name__)


# 部分网关返回的 Bedrock 错误信息特征字符串(剥离 temperature 重试用)
_BEDROCK_TEMP_ERR_HINTS = (
    "temperature",
    "Temperature",
    "is not supported",
)


def _is_bedrock_temperature_error(exc: Exception) -> bool:
    msg = str(exc)
    return any(h in msg for h in _BEDROCK_TEMP_ERR_HINTS)


class DirectLlmProvider(LlmProvider):
    """直接调 LLM SDK,无中间层。"""

    # ---------- Client builders ----------
    def _anthropic_client(self, profile: LlmProfile) -> AsyncAnthropic:
        kwargs: dict = {}
        headers: dict = dict(profile.extra_headers or {})
        if profile.base_url:
            kwargs["base_url"] = profile.base_url
        if profile.auth_type == LlmAuthType.BEARER:
            # 网关 / Bedrock proxy:用 Authorization: Bearer
            kwargs["api_key"] = "placeholder"  # SDK 必填,实际靠 default_headers
            headers["Authorization"] = f"Bearer {profile.api_key}"
        else:
            kwargs["api_key"] = profile.api_key
        if headers:
            kwargs["default_headers"] = headers
        return AsyncAnthropic(**kwargs)

    def _openai_client(self, profile: LlmProfile) -> AsyncOpenAI:
        kwargs: dict = {"api_key": profile.api_key or "placeholder"}
        if profile.base_url:
            kwargs["base_url"] = profile.base_url
        if profile.extra_headers:
            kwargs["default_headers"] = dict(profile.extra_headers)
        return AsyncOpenAI(**kwargs)

    # ---------- chat_stream ----------
    async def chat_stream(
        self,
        profile: LlmProfile,
        messages: list[dict],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        if profile.provider == "anthropic":
            async for t in self._anthropic_stream(
                profile, messages, system=system,
                max_tokens=max_tokens, temperature=temperature,
            ):
                yield t
        elif profile.provider == "openai":
            async for t in self._openai_stream(
                profile, messages, system=system,
                max_tokens=max_tokens, temperature=temperature,
            ):
                yield t
        else:
            raise ValueError(f"未知 provider: {profile.provider}")

    async def _anthropic_stream(
        self,
        profile: LlmProfile,
        messages: list[dict],
        *,
        system: str | None,
        max_tokens: int | None,
        temperature: float | None,
    ) -> AsyncIterator[str]:
        client = self._anthropic_client(profile)
        max_tok = max_tokens or profile.max_tokens
        temp = temperature if temperature is not None else profile.temperature

        async def _do_stream(include_temperature: bool) -> AsyncIterator[str]:
            kwargs: dict = {
                "model": profile.model,
                "max_tokens": max_tok,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system
            if include_temperature:
                kwargs["temperature"] = temp
            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text

        try:
            async for t in _do_stream(include_temperature=True):
                yield t
        except Exception as e:  # noqa: BLE001
            if _is_bedrock_temperature_error(e):
                _log.warning("剥离 temperature 重试 (Bedrock-routed Claude): %s", e)
                async for t in _do_stream(include_temperature=False):
                    yield t
            else:
                raise

    async def _openai_stream(
        self,
        profile: LlmProfile,
        messages: list[dict],
        *,
        system: str | None,
        max_tokens: int | None,
        temperature: float | None,
    ) -> AsyncIterator[str]:
        client = self._openai_client(profile)
        oai_messages: list[dict] = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        oai_messages.extend(messages)

        stream = await client.chat.completions.create(
            model=profile.model,
            messages=oai_messages,
            max_tokens=max_tokens or profile.max_tokens,
            temperature=temperature if temperature is not None else profile.temperature,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    # ---------- chat_with_tools ----------
    async def chat_with_tools(
        self,
        profile: LlmProfile,
        messages: list[dict],
        *,
        tools: list[dict],
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AssistantTurn:
        if profile.provider == "openai":
            return await self._openai_with_tools(
                profile, messages, tools=tools, system=system,
                max_tokens=max_tokens, temperature=temperature,
            )
        if profile.provider != "anthropic":
            raise ValueError(f"未知 provider: {profile.provider}")

        client = self._anthropic_client(profile)
        max_tok = max_tokens or profile.max_tokens
        temp = temperature if temperature is not None else profile.temperature

        kwargs: dict = {
            "model": profile.model,
            "max_tokens": max_tok,
            "messages": messages,
            "tools": tools,
            "temperature": temp,
        }
        if system:
            kwargs["system"] = system

        try:
            resp = await client.messages.create(**kwargs)
        except Exception as e:  # noqa: BLE001
            if _is_bedrock_temperature_error(e):
                kwargs.pop("temperature", None)
                resp = await client.messages.create(**kwargs)
            else:
                raise

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=dict(block.input or {}))
                )
        return AssistantTurn(
            text="".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=resp.stop_reason or "end_turn",
        )

    async def _openai_with_tools(
        self,
        profile: LlmProfile,
        messages: list[dict],
        *,
        tools: list[dict],
        system: str | None,
        max_tokens: int | None,
        temperature: float | None,
    ) -> AssistantTurn:
        import json as _json

        client = self._openai_client(profile)
        oai_messages: list[dict] = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        oai_messages.extend(messages)

        resp = await client.chat.completions.create(
            model=profile.model,
            messages=oai_messages,
            tools=tools,
            max_tokens=max_tokens or profile.max_tokens,
            temperature=temperature if temperature is not None else profile.temperature,
        )
        choice = resp.choices[0]
        msg = choice.message
        text = msg.content or ""
        tool_calls: list[ToolCall] = []
        for tc in (msg.tool_calls or []):
            try:
                args = _json.loads(tc.function.arguments or "{}")
            except _json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
        # OpenAI 的 finish_reason: tool_calls / stop / length …
        stop = "tool_use" if choice.finish_reason == "tool_calls" else (choice.finish_reason or "end_turn")
        return AssistantTurn(text=text, tool_calls=tool_calls, stop_reason=stop)
