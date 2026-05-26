"""ChapterRetriever —— 章节正文的轻量检索接口。

设计目标:在不引入向量库 / 嵌入模型的前提下,给 agent 提供"找相关段落"的能力。
默认实现是 SQLite FTS5(无需额外依赖),后续可以替换为 sqlite-vec / 远程向量库。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ChapterSnippet:
    chapter_id: str
    order_index: int
    title: str
    snippet: str
    score: float


class ChapterRetriever(Protocol):
    async def index_chapter(self, project_id: str, chapter_id: str, content: str) -> None: ...
    async def remove_chapter(self, chapter_id: str) -> None: ...
    async def search(
        self,
        project_id: str,
        query: str,
        *,
        k: int = 4,
    ) -> list[ChapterSnippet]: ...
