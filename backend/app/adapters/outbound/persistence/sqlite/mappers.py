"""ORM ↔ domain dataclass 双向映射。

domain 不依赖 ORM,所有转换发生在 adapter 内部。这样换 ORM 时改这一处即可。
"""
from __future__ import annotations

from app.domain.models import (
    Chapter,
    Character,
    LlmAuthType,
    LlmProfile,
    Project,
    WorldEntry,
)

from .orm import (
    ChapterORM,
    CharacterORM,
    LlmProfileORM,
    ProjectORM,
    WorldEntryORM,
)


def project_to_domain(o: ProjectORM) -> Project:
    return Project(
        id=o.id,
        name=o.name,
        genre=o.genre,
        synopsis=o.synopsis,
        style=o.style,
        outline=o.outline,
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


def project_to_orm(p: Project) -> ProjectORM:
    return ProjectORM(
        id=p.id,
        name=p.name,
        genre=p.genre,
        synopsis=p.synopsis,
        style=p.style,
        outline=p.outline,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def chapter_to_domain(o: ChapterORM) -> Chapter:
    return Chapter(
        id=o.id,
        project_id=o.project_id,
        title=o.title,
        summary=o.summary,
        content=o.content,
        order_index=o.order_index,
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


def chapter_to_orm(c: Chapter) -> ChapterORM:
    return ChapterORM(
        id=c.id,
        project_id=c.project_id,
        title=c.title,
        summary=c.summary,
        content=c.content,
        order_index=c.order_index,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def character_to_domain(o: CharacterORM) -> Character:
    return Character(
        id=o.id,
        project_id=o.project_id,
        name=o.name,
        role=o.role,
        profile=o.profile,
    )


def character_to_orm(c: Character) -> CharacterORM:
    return CharacterORM(
        id=c.id,
        project_id=c.project_id,
        name=c.name,
        role=c.role,
        profile=c.profile,
    )


def world_to_domain(o: WorldEntryORM) -> WorldEntry:
    return WorldEntry(
        id=o.id,
        project_id=o.project_id,
        title=o.title,
        category=o.category,
        content=o.content,
    )


def world_to_orm(w: WorldEntry) -> WorldEntryORM:
    return WorldEntryORM(
        id=w.id,
        project_id=w.project_id,
        title=w.title,
        category=w.category,
        content=w.content,
    )


def llm_profile_to_domain(o: LlmProfileORM) -> LlmProfile:
    return LlmProfile(
        id=o.id,
        name=o.name,
        provider=o.provider,
        model=o.model,
        api_key=o.api_key,
        base_url=o.base_url,
        auth_type=LlmAuthType(o.auth_type),
        max_tokens=o.max_tokens,
        temperature=o.temperature,
        extra_headers=dict(o.extra_headers or {}),
        verified_at=o.verified_at,
    )


def llm_profile_to_orm(p: LlmProfile, *, is_active: bool = False) -> LlmProfileORM:
    return LlmProfileORM(
        id=p.id,
        name=p.name,
        provider=p.provider,
        model=p.model,
        api_key=p.api_key,
        base_url=p.base_url,
        auth_type=p.auth_type.value,
        max_tokens=p.max_tokens,
        temperature=p.temperature,
        extra_headers=dict(p.extra_headers or {}),
        verified_at=p.verified_at,
        is_active=is_active,
    )
