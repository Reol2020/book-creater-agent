"""Embedding 接口 —— 文本向量化,服务于 RAG。"""
from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量 embedding。返回与输入等长的向量列表。"""
        ...

    @property
    def dimension(self) -> int:
        """向量维度,初始化向量库需要。"""
        ...
