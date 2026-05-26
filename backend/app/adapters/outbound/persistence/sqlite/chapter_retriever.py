"""SQLite FTS5 版章节检索。

为什么不用向量库:
- chromadb / lancedb 在 Python 3.14 上还没稳定 wheel(2026-05);
- 用户场景"中文网文找相关章节",FTS5 + bigram tokenizer 召回已经够用;
- 0 额外依赖,跟着主 sqlite db 走。

实现要点:
- 单独的 virtual table chapter_fts(chapter_id UNINDEXED, project_id UNINDEXED, content)
- 中文分词:tokenize='unicode61 remove_diacritics 0' + bigram (前后两个字符当 token,适合中文)
  ↑ FTS5 自带 unicode61 不会切中文,bigram 必须手动:索引时把内容拆成连续二字组
- 写入时按段(\n\n)切块,避免 BM25 被超长正文稀释
- search 时同样把 query bigram 化
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.ports.chapter_retriever import ChapterRetriever, ChapterSnippet


# ------- bigram 分词:中文 2-gram + 拉丁词整体保留
_LATIN = re.compile(r"[A-Za-z0-9_]+")


def _bigrams(text: str) -> list[str]:
    """把中文按 bigram 切,英文/数字按整 token 保留。"""
    text = text or ""
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        m = _LATIN.match(text, i)
        if m:
            out.append(m.group(0).lower())
            i = m.end()
            continue
        if i + 1 < len(text):
            nxt = text[i + 1]
            if not nxt.isspace():
                out.append(text[i:i + 2])
        i += 1
    return out


def _tokenize_for_fts(text: str) -> str:
    """转换成 FTS5 能拆词(以空格为界)的 bigram 表征。"""
    return " ".join(_bigrams(text))


def _split_paragraphs(content: str, *, max_len: int = 600) -> list[str]:
    """按 \\n\\n 切段,过长再硬切。"""
    chunks: list[str] = []
    for para in (content or "").split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_len:
            chunks.append(para)
        else:
            for i in range(0, len(para), max_len):
                chunks.append(para[i:i + max_len])
    return chunks


@dataclass
class _Hit:
    chapter_id: str
    project_id: str
    snippet: str
    score: float


class SqliteFtsChapterRetriever(ChapterRetriever):
    def __init__(
        self,
        session_factory: async_sessionmaker,
        chapter_lookup: Callable[[str], object] | None = None,
    ) -> None:
        self._sf = session_factory
        # chapter_lookup 可注入以拿到 order_index/title;如果 None,则降级为占位
        self._chapter_lookup = chapter_lookup

    async def _exec(self, sql: str, *params):
        async with self._sf() as s:
            conn = await s.connection()
            res = await conn.exec_driver_sql(sql, tuple(params))
            await s.commit()
            return res

    async def _query(self, sql: str, *params):
        async with self._sf() as s:
            conn = await s.connection()
            return (await conn.exec_driver_sql(sql, tuple(params))).all()

    async def ensure_table(self) -> None:
        # FTS5 virtual table。content 列存 bigram 化后的字符串,原文存 raw 列以便 snippet 返回。
        await self._exec(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chapter_fts USING fts5("
            "chapter_id UNINDEXED, project_id UNINDEXED, raw UNINDEXED, content,"
            " tokenize = 'unicode61 remove_diacritics 0')"
        )

    async def index_chapter(self, project_id: str, chapter_id: str, content: str) -> None:
        await self.ensure_table()
        # 先删旧
        await self._exec("DELETE FROM chapter_fts WHERE chapter_id = ?", chapter_id)
        for chunk in _split_paragraphs(content):
            tokens = _tokenize_for_fts(chunk)
            if not tokens:
                continue
            await self._exec(
                "INSERT INTO chapter_fts(chapter_id, project_id, raw, content) VALUES (?,?,?,?)",
                chapter_id, project_id, chunk, tokens,
            )

    async def remove_chapter(self, chapter_id: str) -> None:
        await self.ensure_table()
        await self._exec("DELETE FROM chapter_fts WHERE chapter_id = ?", chapter_id)

    async def search(
        self,
        project_id: str,
        query: str,
        *,
        k: int = 4,
    ) -> list[ChapterSnippet]:
        await self.ensure_table()
        bigrams = _bigrams(query)
        if not bigrams:
            return []
        # FTS5 MATCH 用空格分隔的 OR 默认是 AND;改成 OR 提高召回
        match_expr = " OR ".join(f'"{b}"' for b in bigrams[:32])

        rows = await self._query(
            "SELECT chapter_id, raw, bm25(chapter_fts) AS score "
            "FROM chapter_fts WHERE project_id = ? AND chapter_fts MATCH ? "
            "ORDER BY score LIMIT ?",
            project_id, match_expr, k,
        )

        out: list[ChapterSnippet] = []
        for chapter_id, raw, score in rows:
            order_index = 0
            title = ""
            if self._chapter_lookup is not None:
                try:
                    info = await self._chapter_lookup(chapter_id)  # type: ignore[misc]
                    if info is not None:
                        order_index = getattr(info, "order_index", 0)
                        title = getattr(info, "title", "")
                except Exception:  # noqa: BLE001
                    pass
            out.append(ChapterSnippet(
                chapter_id=chapter_id,
                order_index=order_index,
                title=title,
                snippet=raw,
                score=-float(score or 0.0),  # bm25 越小越好,翻号成"越大越好"
            ))
        return out


__all__ = ["SqliteFtsChapterRetriever", "ChapterSnippet"]
