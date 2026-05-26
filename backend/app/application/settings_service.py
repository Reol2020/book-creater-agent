"""LLM Profile 用例。"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import datetime

from app.application.profile_import import ProfileParseError, parse_profile_text
from app.domain.models import LlmProfile
from app.ports.llm_profile_repository import LlmProfileRepository
from app.ports.llm_provider import LlmProvider

TEST_PROMPT_USER = '回复"连接成功"四个字即可。'
TEST_PROMPT_SYSTEM = "你是一个连接测试工具。"
TEST_TIMEOUT_SEC = 30
TEST_MAX_TOKENS = 64


class SettingsService:
    def __init__(self, repo: LlmProfileRepository, llm: LlmProvider) -> None:
        self._repo = repo
        self._llm = llm

    async def list(self) -> list[LlmProfile]:
        return await self._repo.list()

    async def upsert(self, profile: LlmProfile) -> LlmProfile:
        if not profile.name.strip():
            raise ValueError("配置名称不能为空")
        return await self._repo.upsert(profile)

    async def delete(self, profile_id: str) -> None:
        await self._repo.delete(profile_id)

    async def get_active(self) -> LlmProfile | None:
        return await self._repo.get_active()

    async def set_active(self, profile_id: str) -> None:
        await self._repo.set_active(profile_id)

    async def import_from_text(self, text: str, fallback_name: str = "") -> LlmProfile:
        """解析 JSON / curl 文本为 draft profile。不持久化,前端再 upsert。"""
        try:
            return parse_profile_text(text, fallback_name)
        except ProfileParseError as e:
            raise ValueError(str(e)) from e

    async def test_profile(
        self,
        profile: LlmProfile,
        *,
        persist_id: str | None = None,
    ) -> AsyncIterator[dict]:
        """实测一个 profile,流式吐进度事件。
        事件格式: {"event": "...", **payload}
        - started
        - first_token (latency_ms)
        - chunk (text, total_chars)
        - done (latency_ms, chars)
        - error (title, detail)
        - timeout (after_sec)
        """
        # 短 prompt + 0 温度 + 极小 max_tokens,提速并降成本
        test_prof = replace(profile, max_tokens=TEST_MAX_TOKENS, temperature=0.0)
        loop = asyncio.get_running_loop()
        start = loop.time()
        first_at: float | None = None
        chars = 0

        yield {"event": "started"}

        async def _consume() -> AsyncIterator[dict]:
            nonlocal first_at, chars
            try:
                async for token in self._llm.chat_stream(
                    test_prof,
                    [{"role": "user", "content": TEST_PROMPT_USER}],
                    system=TEST_PROMPT_SYSTEM,
                ):
                    if first_at is None:
                        first_at = loop.time()
                        yield {
                            "event": "first_token",
                            "latency_ms": int((first_at - start) * 1000),
                        }
                    chars += len(token)
                    yield {"event": "chunk", "text": token, "total_chars": chars}
            except Exception as e:  # noqa: BLE001
                yield {
                    "event": "error",
                    "title": type(e).__name__,
                    "detail": str(e),
                }
                return

            elapsed_ms = int((loop.time() - start) * 1000)
            yield {"event": "done", "latency_ms": elapsed_ms, "chars": chars}
            # 持久化 verified_at(只在调用方传了 persist_id 时)
            if persist_id:
                await self._repo.mark_verified(persist_id, datetime.utcnow())

        # 把整个 _consume 包在 wait_for 里实现 watchdog
        agen = _consume().__aiter__()
        while True:
            try:
                ev = await asyncio.wait_for(agen.__anext__(), timeout=TEST_TIMEOUT_SEC)
            except StopAsyncIteration:
                return
            except TimeoutError:
                yield {"event": "timeout", "after_sec": TEST_TIMEOUT_SEC}
                return
            yield ev
