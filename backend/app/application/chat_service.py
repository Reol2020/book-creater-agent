"""纯文本流式聊天用例(M0 最小闭环)。

不带工具调用 / agent loop。M1 由 AgentService 接管复杂场景。
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from app.ports.llm_profile_repository import LlmProfileRepository
from app.ports.llm_provider import LlmProvider


class NoActiveProfileError(RuntimeError):
    pass


class ChatService:
    def __init__(self, llm: LlmProvider, profiles: LlmProfileRepository) -> None:
        self._llm = llm
        self._profiles = profiles

    async def stream(
        self,
        messages: list[dict],
        *,
        system: str | None = None,
    ) -> AsyncIterator[str]:
        profile = await self._profiles.get_active()
        if profile is None:
            raise NoActiveProfileError("尚未启用 LLM 配置,请到设置页添加并启用一个。")
        async for token in self._llm.chat_stream(profile, messages, system=system):
            yield token
