"""LlmProvider 实现:用官方 anthropic / openai SDK,async streaming。

桌面版 `core/llm_client.py` 是同步版本,这里重写为 async。但保留几个关键经验:
  - Anthropic 官方直连用 x-api-key,网关用 Bearer(profile.auth_type 区分)
  - Bedrock 路由的 Claude 不收 temperature → 收到错误就剥离重试一次
  - max_tokens 默认 16384(桌面版踩的坑,见 DEV_NOTES #1.3)
  - **必须有总超时**:某些第三方网关(如 Mify)对非流式请求返回 SSE 格式
    错误体,Anthropic SDK 解析不了会死循环读 body,既不返回也不抛异常。
    上层 agent loop 因此卡死在"思考中"。统一用 httpx.Timeout 限死。
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import httpx

from app.domain.models import (
    AssistantTurn,
    LlmAuthType,
    LlmProfile,
    ToolCall,
)
from app.ports.llm_provider import LlmProvider

# anthropic / openai 的顶层 import 各 1s+(pydantic schema 注册重),
# 这会让后端 lifespan 多花 2s 才能接受请求。改成首次使用时再 import,
# 把启动从 ~3s 降到 ~1s。
if TYPE_CHECKING:  # 仅供类型检查,不进运行时 import
    from anthropic import AsyncAnthropic
    from openai import AsyncOpenAI

_log = logging.getLogger(__name__)


# 总超时:连接 15s + 整体请求 120s。
# - 整 120s 是兜底,正常 LLM 一次工具回合 5-30s 完成
# - 上层 asyncio.wait_for 再加一层防护(httpx 在 keep-alive 异常情况下也可能卡)
_HTTP_TIMEOUT = httpx.Timeout(120.0, connect=15.0)
_OUTER_TIMEOUT_SEC = 150.0


# Bedrock 路由的 Claude(如 Opus 4.x)拒绝 temperature/top_p/top_k。
# 桌面版踩过:错误信息形态有 "`temperature` is not supported" / "temperature is deprecated" 等。
_UNSUPPORTED_PARAMS = ("temperature", "top_p", "top_k")


def _strip_unsupported_params(exc: Exception, params: dict) -> bool:
    """根据 SDK 错误信息,从 params 里剥掉 Bedrock 不接受的字段。
    返回 True 表示有剥离、可重试。
    """
    msg = str(exc).lower()
    stripped = False
    for bad in _UNSUPPORTED_PARAMS:
        if (
            f"`{bad}`" in msg
            or f"{bad} is deprecated" in msg
            or f"{bad} is not supported" in msg
        ):
            if params.pop(bad, None) is not None:
                stripped = True
    return stripped


class LlmTimeoutError(RuntimeError):
    """LLM 调用整体超时(兜底,优先看 _HTTP_TIMEOUT 错误)。"""


def _final_msg_to_turn(msg) -> AssistantTurn:
    """anthropic Message → 我们的 AssistantTurn。"""
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in msg.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(
                ToolCall(id=block.id, name=block.name, arguments=dict(block.input or {}))
            )
    return AssistantTurn(
        text="".join(text_parts),
        tool_calls=tool_calls,
        stop_reason=msg.stop_reason or "end_turn",
    )


class DirectLlmProvider(LlmProvider):
    """直接调 LLM SDK,无中间层。"""

    # ---------- Client builders ----------
    def _anthropic_client(self, profile: LlmProfile) -> "AsyncAnthropic":
        from anthropic import AsyncAnthropic  # lazy
        # SDK 默认会重试 2 次,关掉:失败更快、日志更清晰
        # (我们自己有 _is_bedrock_temperature_error 重试逻辑)
        kwargs: dict = {"timeout": _HTTP_TIMEOUT, "max_retries": 0}
        if profile.base_url:
            kwargs["base_url"] = profile.base_url
        if profile.auth_type == LlmAuthType.BEARER:
            # 网关 / Bedrock proxy:用 SDK 内置 auth_token,SDK 会发
            # Authorization: Bearer <token> 且 **不发 x-api-key**。
            # 桌面版踩过:同时设 api_key="placeholder" + 手写 Authorization 头时,
            # SDK 仍发 x-api-key: placeholder,Mify/PPIO 这类用 x-api-key 鉴权的
            # 网关收到 "placeholder" 直接 400,且响应是 SSE 格式 → SDK 卡死。
            kwargs["auth_token"] = profile.api_key
            kwargs["api_key"] = None
        else:
            kwargs["api_key"] = profile.api_key
        if profile.extra_headers:
            kwargs["default_headers"] = dict(profile.extra_headers)
        return AsyncAnthropic(**kwargs)

    def _openai_client(self, profile: LlmProfile) -> "AsyncOpenAI":
        from openai import AsyncOpenAI  # lazy
        kwargs: dict = {
            "api_key": profile.api_key or "sk-no-key",  # 本地 server 也允许空
            "timeout": _HTTP_TIMEOUT,
            "max_retries": 0,
        }
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
            # 复用 _strip_unsupported_params 的判断逻辑(仅判断,不改 kwargs)
            msg = str(e).lower()
            if any(
                f"`{b}`" in msg or f"{b} is deprecated" in msg or f"{b} is not supported" in msg
                for b in _UNSUPPORTED_PARAMS
            ):
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

        # 关键:用 .stream() 而不是 .create()
        # Mify/PPIO 网关对长 prompt 的非流式 messages.create 会发 SSE 格式响应体,
        # SDK 的 JSON parser 死循环读 body,asyncio.wait_for 也无法切断(httpx 在
        # 流式 reading 状态吞掉 cancellation)。改用 stream(),SDK 走 SSE parser
        # 与 Mify 协议天然匹配,流末调 final_message() 拿到完整 message 还原成
        # AssistantTurn。桌面同步版没踩到这个坑只是因为同步连接管理不同。
        async def _call() -> object:
            async with client.messages.stream(**kwargs) as stream:
                async for _ in stream:  # 必须消费事件,否则 final_message() 拿不到
                    pass
                return await stream.get_final_message()

        _log.info(
            "anthropic.messages.stream model=%s base_url=%s msgs=%d tools=%d",
            profile.model, profile.base_url or "<default>",
            len(messages), len(tools),
        )
        try:
            resp = await asyncio.wait_for(_call(), timeout=_OUTER_TIMEOUT_SEC)
        except asyncio.TimeoutError as e:
            _log.error("LLM 调用超时 %ss (provider=anthropic, base_url=%s)",
                       _OUTER_TIMEOUT_SEC, profile.base_url or "<default>")
            raise LlmTimeoutError(
                f"LLM 调用超时 {_OUTER_TIMEOUT_SEC:.0f}s,通常是网关返回了 SDK "
                f"无法解析的响应体。请检查 LLM 配置或换 provider。"
            ) from e
        except Exception as e:  # noqa: BLE001
            if _strip_unsupported_params(e, kwargs):
                _log.warning("剥离 temperature/top_p/top_k 后重试: %s", e)
                resp = await asyncio.wait_for(_call(), timeout=_OUTER_TIMEOUT_SEC)
            else:
                raise

        return _final_msg_to_turn(resp)

    # ---------- chat_with_tools_stream ----------
    async def chat_with_tools_stream(
        self,
        profile: LlmProfile,
        messages: list[dict],
        *,
        tools: list[dict],
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[dict]:
        # OpenAI 流式 + tools 协议复杂(deltas 拼 tool_calls.arguments),先降级到非流式
        if profile.provider == "openai":
            turn = await self._openai_with_tools(
                profile, messages, tools=tools, system=system,
                max_tokens=max_tokens, temperature=temperature,
            )
            yield {"type": "final", "turn": turn}
            return
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

        # 把 final_message 通过闭包传出来(async generator 不能 return value)
        final_holder: dict = {}

        # tool_use 块的 input 也是流式的(input_json_delta),长章节正文走这条通道。
        # 我们不把内容透传给前端(避免一整章正文塞进对话),只统计字符数,节流后
        # 发 tool_progress 事件让用户知道"AI 正在写,已写 N 字"。
        _PROGRESS_INTERVAL = 0.8  # seconds

        async def _stream_events(kw: dict) -> AsyncIterator[dict]:
            async with client.messages.stream(**kw) as stream:
                cur_tool_id: str | None = None
                cur_tool_name: str | None = None
                cur_tool_chars = 0
                last_progress_at = 0.0
                async for event in stream:
                    et = event.type
                    if et == "content_block_start":
                        block = event.content_block
                        if getattr(block, "type", "") == "tool_use":
                            cur_tool_id = block.id
                            cur_tool_name = block.name
                            cur_tool_chars = 0
                            last_progress_at = time.monotonic()
                            yield {
                                "type": "tool_progress",
                                "id": cur_tool_id,
                                "name": cur_tool_name,
                                "chars": 0,
                                "phase": "start",
                            }
                    elif et == "content_block_delta":
                        d = event.delta
                        dt = getattr(d, "type", "")
                        if dt == "text_delta":
                            yield {"type": "text_delta", "text": d.text}
                        elif dt == "input_json_delta" and cur_tool_name is not None:
                            cur_tool_chars += len(getattr(d, "partial_json", "") or "")
                            now = time.monotonic()
                            if now - last_progress_at >= _PROGRESS_INTERVAL:
                                last_progress_at = now
                                yield {
                                    "type": "tool_progress",
                                    "id": cur_tool_id,
                                    "name": cur_tool_name,
                                    "chars": cur_tool_chars,
                                    "phase": "delta",
                                }
                    elif et == "content_block_stop":
                        if cur_tool_name is not None:
                            yield {
                                "type": "tool_progress",
                                "id": cur_tool_id,
                                "name": cur_tool_name,
                                "chars": cur_tool_chars,
                                "phase": "end",
                            }
                            cur_tool_id = None
                            cur_tool_name = None
                            cur_tool_chars = 0
                final_holder["msg"] = await stream.get_final_message()

        _log.info(
            "anthropic.messages.stream(tools) model=%s base_url=%s msgs=%d tools=%d",
            profile.model, profile.base_url or "<default>",
            len(messages), len(tools),
        )
        try:
            async for ev in _stream_events(kwargs):
                yield ev
        except Exception as e:  # noqa: BLE001
            # Bedrock 拒绝 temperature/top_p/top_k 的错误在 stream 进入瞬间抛出,
            # 此时还没 yield 过任何 delta,可以安全重试。
            if "msg" in final_holder:
                # 已经流过部分内容才出错,不能重试(会重复 yield)
                raise
            if not _strip_unsupported_params(e, kwargs):
                raise
            _log.warning("剥离 temperature/top_p/top_k 后重试 (stream): %s", e)
            async for ev in _stream_events(kwargs):
                yield ev

        final_msg = final_holder.get("msg")
        if final_msg is None:
            raise RuntimeError("流结束但未拿到 final_message")
        yield {"type": "final", "turn": _final_msg_to_turn(final_msg)}

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

        _log.info(
            "openai.chat.completions.create model=%s base_url=%s msgs=%d tools=%d",
            profile.model, profile.base_url or "<default>",
            len(oai_messages), len(tools),
        )
        try:
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model=profile.model,
                    messages=oai_messages,
                    tools=tools,
                    max_tokens=max_tokens or profile.max_tokens,
                    temperature=temperature if temperature is not None else profile.temperature,
                ),
                timeout=_OUTER_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError as e:
            _log.error("LLM 调用超时 %ss (provider=openai, base_url=%s)",
                       _OUTER_TIMEOUT_SEC, profile.base_url or "<default>")
            raise LlmTimeoutError(
                f"LLM 调用超时 {_OUTER_TIMEOUT_SEC:.0f}s。"
            ) from e
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
