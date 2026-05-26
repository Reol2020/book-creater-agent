"""依赖装配 (Composition Root)。

整个工程里只有这里能 import adapters。其他层都通过 ports.* 拿到接口,
由这里负责把具体实现注入。这样未来切换 SQLite→Postgres / Chroma→Qdrant
只改这个文件 + 加一个新 adapter。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.application.agent_service import AgentService
from app.application.chat_service import ChatService
from app.application.context_builder import ProjectContextBuilder
from app.application.project_service import ProjectService
from app.application.settings_service import SettingsService
from app.skills import SkillRegistry, build_default_registry
from app.config.settings import Settings, get_settings
from app.ports.chapter_retriever import ChapterRetriever
from app.ports.llm_profile_repository import LlmProfileRepository
from app.ports.llm_provider import LlmProvider
from app.ports.project_repository import ProjectRepository


@dataclass
class Container:
    settings: Settings
    project_repo: ProjectRepository
    profile_repo: LlmProfileRepository
    llm_provider: LlmProvider
    chapter_retriever: ChapterRetriever
    project_service: ProjectService
    chat_service: ChatService
    settings_service: SettingsService
    agent_service: AgentService
    skills: SkillRegistry
    context_builder: ProjectContextBuilder
    # 持有 Database 以便 lifespan 关闭
    _database: object  # noqa: A003


async def build_container() -> Container:
    settings = get_settings()

    # 仅在 composition root 内 import adapters
    from app.adapters.outbound.llm.direct.provider import DirectLlmProvider
    from app.adapters.outbound.persistence.sqlite.chapter_retriever import (
        SqliteFtsChapterRetriever,
    )
    from app.adapters.outbound.persistence.sqlite.database import Database
    from app.adapters.outbound.persistence.sqlite.llm_profile_repository import (
        SqliteLlmProfileRepository,
    )
    from app.adapters.outbound.persistence.sqlite.project_repository import (
        SqliteProjectRepository,
    )

    db = Database(settings.data_path / "app.db")
    await db.init()

    project_repo = SqliteProjectRepository(db.session_factory)
    profile_repo = SqliteLlmProfileRepository(db.session_factory)
    llm_provider = DirectLlmProvider()

    chapter_retriever = SqliteFtsChapterRetriever(db.session_factory)

    base_project_service = ProjectService(project_repo)
    project_service = _ChapterIndexingProjectService(base_project_service, chapter_retriever)
    chat_service = ChatService(llm_provider, profile_repo)
    settings_service = SettingsService(profile_repo, llm_provider)
    skills = build_default_registry()
    agent_service = AgentService(llm_provider, profile_repo, skills, project_service)
    context_builder = ProjectContextBuilder(project_service, chapter_retriever)

    return Container(
        settings=settings,
        project_repo=project_repo,
        profile_repo=profile_repo,
        llm_provider=llm_provider,
        project_service=project_service,
        chat_service=chat_service,
        settings_service=settings_service,
        agent_service=agent_service,
        skills=skills,
        context_builder=context_builder,
        chapter_retriever=chapter_retriever,
        _database=db,
    )


# ---------------------------------------------------------- chapter index 装饰器
class _ChapterIndexingProjectService:
    """ProjectService 的薄包装,在章节写/删时同步更新 FTS 索引。

    放在 composition root,业务层完全感知不到 RAG。
    """
    def __init__(self, inner: ProjectService, retriever: ChapterRetriever) -> None:
        self._inner = inner
        self._retriever = retriever

    def __getattr__(self, name):
        return getattr(self._inner, name)

    async def create_chapter(self, chapter):
        saved = await self._inner.create_chapter(chapter)
        try:
            await self._retriever.index_chapter(saved.project_id, saved.id, saved.content)
        except Exception:  # noqa: BLE001
            pass
        return saved

    async def update_chapter(self, chapter):
        saved = await self._inner.update_chapter(chapter)
        try:
            await self._retriever.index_chapter(saved.project_id, saved.id, saved.content)
        except Exception:  # noqa: BLE001
            pass
        return saved

    async def delete_chapter(self, chapter_id: str) -> None:
        await self._inner.delete_chapter(chapter_id)
        try:
            await self._retriever.remove_chapter(chapter_id)
        except Exception:  # noqa: BLE001
            pass


async def shutdown_container(container: Container) -> None:
    db = container._database
    if hasattr(db, "dispose"):
        await db.dispose()
