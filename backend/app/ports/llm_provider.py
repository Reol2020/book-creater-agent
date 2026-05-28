"""LLM Provider 接口。

业务层只通过这个接口调 LLM。换 SDK / 换 Provider / mock 测试都只换实现。
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from app.domain.models import AssistantTurn, LlmProfile


class LlmProvider(Protocol):
    async def chat_stream(
        self,
        profile: LlmProfile,
        messages: list[dict],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """普通流式聊天,逐 token yield。"""
        ...

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
        """工具调用回合(非流式)。返回完整 turn(可能含 tool_calls)。

        agent loop 优先使用 ``chat_with_tools_stream``;此方法保留给非流式路径
        (如内部测试、单步推理)。
        """
        ...

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
        """工具调用回合(流式)。

        yield 事件:
          {"type": "text_delta", "text": "..."}  - LLM 写正文时的实时增量
          {"type": "tool_progress", "id": str, "name": str, "chars": int,
            "phase": "start"|"delta"|"end"}  - LLM 正在生成 tool_use 块的 input
            (例如长章节正文)。chars 是 partial_json 累计长度,仅作活体心跳,
            不携带内容。Provider 会节流到 ~每 0.8s 一次。
          {"type": "final", "turn": AssistantTurn}  - 流末完整 turn(含 tool_calls)

        让 agent loop 边出字边推送给前端,避免长生成场景"等 80 秒才看到第一个字"。
        """
        ...
