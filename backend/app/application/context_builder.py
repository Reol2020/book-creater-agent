"""ProjectContextBuilder —— 把项目状态切片塞进 prompt。

策略:按优先级排序,每段按字符预算截断;字符预算近似为 token 预算 / 1.6
(中文场景偏保守)。

优先级(高→低):
  1. project meta (name/genre/style)
  2. synopsis
  3. outline
  4. active chapter (若指定)
  5. characters
  6. world entries
  7. recent chapter summaries
  8. retrieved snippets (B2 RAG 注入)

每段有最低保留长度;超限时按比例缩减低优先级段。
"""
from __future__ import annotations

from app.application.project_service import ProjectService
from app.ports.chapter_retriever import ChapterRetriever
from app.prompts import ProjectContext
from app.prompts.context import CharacterBrief, ChapterBrief, WorldBrief

# 字符预算 ~ token * 1.6,中文偏保守
DEFAULT_CHAR_BUDGET = 12000
RECENT_CHAPTER_LIMIT = 3


def _truncate(text: str, limit: int) -> str:
    if not text or limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


class ProjectContextBuilder:
    def __init__(
        self,
        project_service: ProjectService,
        retriever: ChapterRetriever | None = None,
    ) -> None:
        self._svc = project_service
        self._retriever = retriever

    async def build(
        self,
        project_id: str,
        *,
        active_chapter_id: str | None = None,
        char_budget: int = DEFAULT_CHAR_BUDGET,
        retrieved: list[str] | None = None,
        query: str | None = None,
        retrieve_k: int = 4,
    ) -> ProjectContext:
        if retrieved is None and query and self._retriever is not None:
            try:
                hits = await self._retriever.search(project_id, query, k=retrieve_k)
                retrieved = [
                    f"第{h.order_index}章《{h.title}》: {h.snippet}" if h.title else h.snippet
                    for h in hits
                ]
            except Exception:  # noqa: BLE001
                retrieved = None
        project = await self._svc.get(project_id)
        characters = await self._svc.list_characters(project_id)
        world = await self._svc.list_world(project_id)
        chapters = await self._svc.list_chapters(project_id)

        # ---- 预算分配
        budget = max(2000, char_budget)
        meta_budget = 400
        synopsis_budget = min(800, budget // 6)
        outline_budget = min(2000, budget // 3)
        active_budget = min(3000, budget // 3) if active_chapter_id else 0
        retrieved_budget = min(1500, budget // 5) if retrieved else 0

        consumed = meta_budget + synopsis_budget + outline_budget + active_budget + retrieved_budget
        rest = max(1000, budget - consumed)
        char_budget_each = max(120, rest // 3 // max(1, len(characters)))
        world_budget_each = max(120, rest // 3 // max(1, len(world)))
        recent_budget_each = max(120, rest // 3 // RECENT_CHAPTER_LIMIT)

        ctx = ProjectContext(
            project_id=project.id,
            name=_truncate(project.name, 80),
            genre=_truncate(project.genre, 80),
            style=_truncate(project.style, 240),
            synopsis=_truncate(project.synopsis, synopsis_budget),
            outline=_truncate(project.outline, outline_budget),
        )

        # active chapter
        if active_chapter_id:
            target = next((c for c in chapters if c.id == active_chapter_id), None)
            if target:
                ctx.active_chapter = ChapterBrief(
                    order_index=target.order_index,
                    title=target.title,
                    summary=_truncate(target.summary, 400),
                    content=_truncate(target.content, max(0, active_budget - 400)),
                )

        # characters
        ctx.characters = [
            CharacterBrief(
                name=c.name, role=c.role,
                profile=_truncate(c.profile, char_budget_each),
            )
            for c in characters
        ]

        # world
        ctx.world = [
            WorldBrief(
                title=w.title, category=w.category,
                content=_truncate(w.content, world_budget_each),
            )
            for w in world
        ]

        # recent chapter summaries —— 取最近 N 章(排除 active)
        recents = sorted(chapters, key=lambda c: c.order_index, reverse=True)
        recents = [c for c in recents if c.id != active_chapter_id][:RECENT_CHAPTER_LIMIT]
        recents = sorted(recents, key=lambda c: c.order_index)
        ctx.recent_chapters = [
            ChapterBrief(
                order_index=c.order_index, title=c.title,
                summary=_truncate(c.summary or _truncate(c.content, 200), recent_budget_each),
            )
            for c in recents
        ]

        if retrieved:
            ctx.retrieved = [_truncate(s, retrieved_budget // max(1, len(retrieved))) for s in retrieved]

        return ctx
