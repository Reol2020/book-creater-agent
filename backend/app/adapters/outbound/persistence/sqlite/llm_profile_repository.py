"""LlmProfileRepository 的 SQLite 实现。"""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.models import LlmProfile
from app.ports.llm_profile_repository import LlmProfileRepository

from .mappers import llm_profile_to_domain, llm_profile_to_orm
from .orm import LlmProfileORM


class SqliteLlmProfileRepository(LlmProfileRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._sf = session_factory

    async def list(self) -> list[LlmProfile]:
        async with self._sf() as s:
            rows = (await s.execute(select(LlmProfileORM))).scalars().all()
            return [llm_profile_to_domain(o) for o in rows]

    async def get(self, profile_id: str) -> LlmProfile | None:
        async with self._sf() as s:
            o = await s.get(LlmProfileORM, profile_id)
            return llm_profile_to_domain(o) if o else None

    async def upsert(self, profile: LlmProfile) -> LlmProfile:
        async with self._sf() as s:
            o = await s.get(LlmProfileORM, profile.id)
            if o is None:
                o = llm_profile_to_orm(profile)
                s.add(o)
            else:
                o.name = profile.name
                o.provider = profile.provider
                o.model = profile.model
                o.api_key = profile.api_key
                o.base_url = profile.base_url
                o.auth_type = profile.auth_type.value
                o.max_tokens = profile.max_tokens
                o.temperature = profile.temperature
                o.extra_headers = dict(profile.extra_headers or {})
                o.verified_at = profile.verified_at
            await s.commit()
            await s.refresh(o)
            return llm_profile_to_domain(o)

    async def mark_verified(self, profile_id: str, when) -> None:
        async with self._sf() as s:
            await s.execute(
                update(LlmProfileORM)
                .where(LlmProfileORM.id == profile_id)
                .values(verified_at=when)
            )
            await s.commit()

    async def delete(self, profile_id: str) -> None:
        async with self._sf() as s:
            o = await s.get(LlmProfileORM, profile_id)
            if o:
                await s.delete(o)
                await s.commit()

    async def get_active(self) -> LlmProfile | None:
        async with self._sf() as s:
            o = (await s.execute(
                select(LlmProfileORM).where(LlmProfileORM.is_active.is_(True)).limit(1)
            )).scalar_one_or_none()
            return llm_profile_to_domain(o) if o else None

    async def set_active(self, profile_id: str) -> None:
        async with self._sf() as s:
            # 先全部置 false,再把目标置 true
            await s.execute(update(LlmProfileORM).values(is_active=False))
            await s.execute(
                update(LlmProfileORM)
                .where(LlmProfileORM.id == profile_id)
                .values(is_active=True)
            )
            await s.commit()
