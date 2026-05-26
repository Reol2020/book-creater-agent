"""ProjectRepository 的 SQLite 实现。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.models import Chapter, Character, Project, WorldEntry
from app.ports.project_repository import ProjectRepository

from .mappers import (
    chapter_to_domain,
    chapter_to_orm,
    character_to_domain,
    character_to_orm,
    project_to_domain,
    project_to_orm,
    world_to_domain,
    world_to_orm,
)
from .orm import (
    ChapterORM,
    CharacterORM,
    ProjectORM,
    WorldEntryORM,
)


class SqliteProjectRepository(ProjectRepository):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._sf = session_factory

    # ============================================================ Project
    async def create_project(self, project: Project) -> Project:
        async with self._sf() as s:
            o = project_to_orm(project)
            s.add(o)
            await s.commit()
            await s.refresh(o)
            return project_to_domain(o)

    async def get_project(self, project_id: str) -> Project | None:
        async with self._sf() as s:
            o = await s.get(ProjectORM, project_id)
            return project_to_domain(o) if o else None

    async def list_projects(self) -> list[Project]:
        async with self._sf() as s:
            rows = (await s.execute(
                select(ProjectORM).order_by(ProjectORM.updated_at.desc())
            )).scalars().all()
            return [project_to_domain(o) for o in rows]

    async def update_project(self, project: Project) -> Project:
        async with self._sf() as s:
            o = await s.get(ProjectORM, project.id)
            if o is None:
                raise LookupError(project.id)
            o.name = project.name
            o.genre = project.genre
            o.synopsis = project.synopsis
            o.style = project.style
            o.outline = project.outline
            o.updated_at = datetime.utcnow()
            await s.commit()
            await s.refresh(o)
            return project_to_domain(o)

    async def delete_project(self, project_id: str) -> None:
        async with self._sf() as s:
            o = await s.get(ProjectORM, project_id)
            if o:
                await s.delete(o)
                await s.commit()

    # ============================================================ Chapter
    async def list_chapters(self, project_id: str) -> list[Chapter]:
        async with self._sf() as s:
            rows = (await s.execute(
                select(ChapterORM)
                .where(ChapterORM.project_id == project_id)
                .order_by(ChapterORM.order_index)
            )).scalars().all()
            return [chapter_to_domain(o) for o in rows]

    async def get_chapter(self, chapter_id: str) -> Chapter | None:
        async with self._sf() as s:
            o = await s.get(ChapterORM, chapter_id)
            return chapter_to_domain(o) if o else None

    async def create_chapter(self, chapter: Chapter) -> Chapter:
        async with self._sf() as s:
            # 自动 order_index 放最后
            if chapter.order_index == 0:
                last = (await s.execute(
                    select(ChapterORM.order_index)
                    .where(ChapterORM.project_id == chapter.project_id)
                    .order_by(ChapterORM.order_index.desc())
                    .limit(1)
                )).scalar()
                chapter.order_index = (last or 0) + 1
            o = chapter_to_orm(chapter)
            s.add(o)
            await s.commit()
            await s.refresh(o)
            return chapter_to_domain(o)

    async def update_chapter(self, chapter: Chapter) -> Chapter:
        async with self._sf() as s:
            o = await s.get(ChapterORM, chapter.id)
            if o is None:
                raise LookupError(chapter.id)
            o.title = chapter.title
            o.summary = chapter.summary
            o.content = chapter.content
            o.order_index = chapter.order_index
            o.updated_at = datetime.utcnow()
            await s.commit()
            await s.refresh(o)
            return chapter_to_domain(o)

    async def delete_chapter(self, chapter_id: str) -> None:
        async with self._sf() as s:
            o = await s.get(ChapterORM, chapter_id)
            if o:
                await s.delete(o)
                await s.commit()

    async def reorder_chapters(self, project_id: str, ordered_ids: list[str]) -> None:
        async with self._sf() as s:
            for idx, cid in enumerate(ordered_ids, start=1):
                o = await s.get(ChapterORM, cid)
                if o and o.project_id == project_id:
                    o.order_index = idx
            await s.commit()

    # ============================================================ Character
    async def list_characters(self, project_id: str) -> list[Character]:
        async with self._sf() as s:
            rows = (await s.execute(
                select(CharacterORM).where(CharacterORM.project_id == project_id)
            )).scalars().all()
            return [character_to_domain(o) for o in rows]

    async def get_character(self, character_id: str) -> Character | None:
        async with self._sf() as s:
            o = await s.get(CharacterORM, character_id)
            return character_to_domain(o) if o else None

    async def upsert_character(self, character: Character) -> Character:
        async with self._sf() as s:
            o = await s.get(CharacterORM, character.id)
            if o is None:
                o = character_to_orm(character)
                s.add(o)
            else:
                o.name = character.name
                o.role = character.role
                o.profile = character.profile
            await s.commit()
            await s.refresh(o)
            return character_to_domain(o)

    async def delete_character(self, character_id: str) -> None:
        async with self._sf() as s:
            o = await s.get(CharacterORM, character_id)
            if o:
                await s.delete(o)
                await s.commit()

    # ============================================================ WorldEntry
    async def list_world_entries(self, project_id: str) -> list[WorldEntry]:
        async with self._sf() as s:
            rows = (await s.execute(
                select(WorldEntryORM).where(WorldEntryORM.project_id == project_id)
            )).scalars().all()
            return [world_to_domain(o) for o in rows]

    async def get_world_entry(self, entry_id: str) -> WorldEntry | None:
        async with self._sf() as s:
            o = await s.get(WorldEntryORM, entry_id)
            return world_to_domain(o) if o else None

    async def upsert_world_entry(self, entry: WorldEntry) -> WorldEntry:
        async with self._sf() as s:
            o = await s.get(WorldEntryORM, entry.id)
            if o is None:
                o = world_to_orm(entry)
                s.add(o)
            else:
                o.title = entry.title
                o.category = entry.category
                o.content = entry.content
            await s.commit()
            await s.refresh(o)
            return world_to_domain(o)

    async def delete_world_entry(self, entry_id: str) -> None:
        async with self._sf() as s:
            o = await s.get(WorldEntryORM, entry_id)
            if o:
                await s.delete(o)
                await s.commit()
