"""向量知识库接口 —— 设定 / 灵感 / 外部参考的存储与语义检索。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.models import KnowledgeItem, KnowledgeKind


@dataclass
class SearchHit:
    item: KnowledgeItem
    score: float


class KnowledgeStore(Protocol):
    async def upsert(self, item: KnowledgeItem, embedding: list[float]) -> None: ...

    async def delete(self, item_id: str) -> None: ...

    async def get(self, item_id: str) -> KnowledgeItem | None: ...

    async def list_by_project(
        self,
        project_id: str,
        *,
        kind: KnowledgeKind | None = None,
    ) -> list[KnowledgeItem]: ...

    async def search(
        self,
        project_id: str,
        query_embedding: list[float],
        *,
        k: int = 6,
        kind: KnowledgeKind | None = None,
        tags: list[str] | None = None,
    ) -> list[SearchHit]: ...
