"""项目用例。"""
from __future__ import annotations

from app.domain.models import Chapter, Character, Project, WorldEntry
from app.ports.project_repository import ProjectRepository


class ProjectService:
    def __init__(self, repo: ProjectRepository) -> None:
        self._repo = repo

    # ----------- Project
    async def create(self, name: str, **kwargs) -> Project:
        project = Project(name=name.strip(), **kwargs)
        if not project.name:
            raise ValueError("项目名不能为空")
        return await self._repo.create_project(project)

    async def list_(self) -> list[Project]:
        return await self._repo.list_projects()

    async def get(self, project_id: str) -> Project:
        p = await self._repo.get_project(project_id)
        if p is None:
            raise LookupError(f"项目不存在: {project_id}")
        return p

    async def update(self, project: Project) -> Project:
        return await self._repo.update_project(project)

    async def delete(self, project_id: str) -> None:
        await self._repo.delete_project(project_id)

    # ----------- Chapter
    async def list_chapters(self, project_id: str) -> list[Chapter]:
        return await self._repo.list_chapters(project_id)

    async def create_chapter(self, chapter: Chapter) -> Chapter:
        return await self._repo.create_chapter(chapter)

    async def update_chapter(self, chapter: Chapter) -> Chapter:
        return await self._repo.update_chapter(chapter)

    async def delete_chapter(self, chapter_id: str) -> None:
        await self._repo.delete_chapter(chapter_id)

    async def reorder_chapters(self, project_id: str, ordered_ids: list[str]) -> None:
        await self._repo.reorder_chapters(project_id, ordered_ids)

    # ----------- Character
    async def list_characters(self, project_id: str) -> list[Character]:
        return await self._repo.list_characters(project_id)

    async def upsert_character(self, character: Character) -> Character:
        return await self._repo.upsert_character(character)

    async def delete_character(self, character_id: str) -> None:
        await self._repo.delete_character(character_id)

    # ----------- World
    async def list_world(self, project_id: str) -> list[WorldEntry]:
        return await self._repo.list_world_entries(project_id)

    async def upsert_world(self, entry: WorldEntry) -> WorldEntry:
        return await self._repo.upsert_world_entry(entry)

    async def delete_world(self, entry_id: str) -> None:
        await self._repo.delete_world_entry(entry_id)
