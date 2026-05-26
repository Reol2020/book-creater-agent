"""项目 / 章节 CRUD endpoints。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.application.project_service import ProjectService
from app.domain.models import Chapter, Character, Project, WorldEntry

from .dependencies import get_project_service
from .schemas import (
    ChapterCreate,
    ChapterOut,
    ChapterUpdate,
    CharacterIn,
    CharacterOut,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    ReorderIn,
    WorldEntryIn,
    WorldEntryOut,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _proj_out(p: Project) -> ProjectOut:
    return ProjectOut(
        id=p.id, name=p.name, genre=p.genre, synopsis=p.synopsis,
        style=p.style, outline=p.outline,
        created_at=p.created_at, updated_at=p.updated_at,
    )


def _chap_out(c: Chapter) -> ChapterOut:
    return ChapterOut(
        id=c.id, project_id=c.project_id, title=c.title, summary=c.summary,
        content=c.content, order_index=c.order_index,
        word_count=c.word_count,
        created_at=c.created_at, updated_at=c.updated_at,
    )


# ----------- Projects
@router.get("", response_model=list[ProjectOut])
async def list_projects(svc: ProjectService = Depends(get_project_service)):
    return [_proj_out(p) for p in await svc.list_()]


@router.post("", response_model=ProjectOut)
async def create_project(
    body: ProjectCreate,
    svc: ProjectService = Depends(get_project_service),
):
    try:
        p = await svc.create(
            body.name,
            genre=body.genre, synopsis=body.synopsis,
            style=body.style, outline=body.outline,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _proj_out(p)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, svc: ProjectService = Depends(get_project_service)):
    try:
        return _proj_out(await svc.get(project_id))
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    svc: ProjectService = Depends(get_project_service),
):
    try:
        existing = await svc.get(project_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    existing.name = body.name
    existing.genre = body.genre
    existing.synopsis = body.synopsis
    existing.style = body.style
    existing.outline = body.outline
    return _proj_out(await svc.update(existing))


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, svc: ProjectService = Depends(get_project_service)):
    await svc.delete(project_id)


# ----------- Chapters
@router.get("/{project_id}/chapters", response_model=list[ChapterOut])
async def list_chapters(project_id: str, svc: ProjectService = Depends(get_project_service)):
    return [_chap_out(c) for c in await svc.list_chapters(project_id)]


@router.post("/{project_id}/chapters", response_model=ChapterOut)
async def create_chapter(
    project_id: str,
    body: ChapterCreate,
    svc: ProjectService = Depends(get_project_service),
):
    chapter = Chapter(
        project_id=project_id,
        title=body.title, summary=body.summary,
        content=body.content, order_index=body.order_index,
    )
    return _chap_out(await svc.create_chapter(chapter))


@router.put("/{project_id}/chapters/{chapter_id}", response_model=ChapterOut)
async def update_chapter(
    project_id: str,
    chapter_id: str,
    body: ChapterUpdate,
    svc: ProjectService = Depends(get_project_service),
):
    chapter = Chapter(
        project_id=project_id,
        title=body.title, summary=body.summary,
        content=body.content, order_index=body.order_index,
    )
    chapter.id = chapter_id
    try:
        return _chap_out(await svc.update_chapter(chapter))
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.delete("/{project_id}/chapters/{chapter_id}", status_code=204)
async def delete_chapter(
    project_id: str,
    chapter_id: str,
    svc: ProjectService = Depends(get_project_service),
):
    await svc.delete_chapter(chapter_id)


@router.post("/{project_id}/chapters/reorder", status_code=204)
async def reorder_chapters(
    project_id: str,
    body: ReorderIn,
    svc: ProjectService = Depends(get_project_service),
):
    await svc.reorder_chapters(project_id, body.ordered_ids)


# ----------- Characters
def _char_out(c: Character) -> CharacterOut:
    return CharacterOut(
        id=c.id, project_id=c.project_id,
        name=c.name, role=c.role, profile=c.profile,
    )


@router.get("/{project_id}/characters", response_model=list[CharacterOut])
async def list_characters(project_id: str, svc: ProjectService = Depends(get_project_service)):
    return [_char_out(c) for c in await svc.list_characters(project_id)]


@router.post("/{project_id}/characters", response_model=CharacterOut)
async def upsert_character(
    project_id: str,
    body: CharacterIn,
    svc: ProjectService = Depends(get_project_service),
):
    c = Character(
        project_id=project_id,
        name=body.name, role=body.role, profile=body.profile,
    )
    if body.id:
        c.id = body.id
    return _char_out(await svc.upsert_character(c))


@router.delete("/{project_id}/characters/{character_id}", status_code=204)
async def delete_character(
    project_id: str,
    character_id: str,
    svc: ProjectService = Depends(get_project_service),
):
    await svc.delete_character(character_id)


# ----------- World Entries
def _world_out(w: WorldEntry) -> WorldEntryOut:
    return WorldEntryOut(
        id=w.id, project_id=w.project_id,
        title=w.title, category=w.category, content=w.content,
    )


@router.get("/{project_id}/world", response_model=list[WorldEntryOut])
async def list_world(project_id: str, svc: ProjectService = Depends(get_project_service)):
    return [_world_out(w) for w in await svc.list_world(project_id)]


@router.post("/{project_id}/world", response_model=WorldEntryOut)
async def upsert_world(
    project_id: str,
    body: WorldEntryIn,
    svc: ProjectService = Depends(get_project_service),
):
    w = WorldEntry(
        project_id=project_id,
        title=body.title, category=body.category, content=body.content,
    )
    if body.id:
        w.id = body.id
    return _world_out(await svc.upsert_world(w))


@router.delete("/{project_id}/world/{entry_id}", status_code=204)
async def delete_world(
    project_id: str,
    entry_id: str,
    svc: ProjectService = Depends(get_project_service),
):
    await svc.delete_world(entry_id)
