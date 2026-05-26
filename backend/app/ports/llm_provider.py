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
        """工具调用回合。返回完整 turn(可能含 tool_calls)。

        注意:这一回合不流式 —— LLM 决定调工具时整段决策一次返回。
        流式只发生在最终的纯文本回合。
        """
        ...
