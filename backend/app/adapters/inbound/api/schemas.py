"""Pydantic DTO —— HTTP 边界,不要把它们泄漏到 application 层。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models import LlmAuthType


# ============================================================ Project
class ProjectCreate(BaseModel):
    name: str
    genre: str = ""
    synopsis: str = ""
    style: str = ""
    outline: str = ""


class ProjectUpdate(BaseModel):
    name: str
    genre: str = ""
    synopsis: str = ""
    style: str = ""
    outline: str = ""


class ProjectOut(BaseModel):
    id: str
    name: str
    genre: str
    synopsis: str
    style: str
    outline: str
    created_at: datetime
    updated_at: datetime


# ============================================================ Chapter
class ChapterCreate(BaseModel):
    title: str = ""
    summary: str = ""
    content: str = ""
    order_index: int = 0


class ChapterUpdate(BaseModel):
    title: str = ""
    summary: str = ""
    content: str = ""
    order_index: int = 0


class ChapterOut(BaseModel):
    id: str
    project_id: str
    title: str
    summary: str
    content: str
    order_index: int
    word_count: int
    created_at: datetime
    updated_at: datetime


class ReorderIn(BaseModel):
    ordered_ids: list[str]


# ============================================================ Character
class CharacterIn(BaseModel):
    id: str | None = None
    name: str
    role: str = ""
    profile: str = ""


class CharacterOut(BaseModel):
    id: str
    project_id: str
    name: str
    role: str
    profile: str


# ============================================================ WorldEntry
class WorldEntryIn(BaseModel):
    id: str | None = None
    title: str
    category: str = ""
    content: str = ""


class WorldEntryOut(BaseModel):
    id: str
    project_id: str
    title: str
    category: str
    content: str


# ============================================================ Chat (M0)
class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str


class ChatStreamIn(BaseModel):
    messages: list[ChatMessage]
    system: str | None = None
    project_id: str | None = None
    confirm_policy: str = "default"  # default | auto | confirm-all


# ============================================================ LLM Profile
class LlmProfileIn(BaseModel):
    name: str
    provider: str
    model: str
    api_key: str = ""
    base_url: str = ""
    auth_type: LlmAuthType = LlmAuthType.API_KEY
    max_tokens: int = 16384
    temperature: float = 0.7
    extra_headers: dict[str, str] = Field(default_factory=dict)
    id: str | None = None


class LlmProfileOut(BaseModel):
    id: str
    name: str
    provider: str
    model: str
    api_key: str
    base_url: str
    auth_type: LlmAuthType
    max_tokens: int
    temperature: float
    extra_headers: dict[str, str] = Field(default_factory=dict)
    verified_at: datetime | None = None


# 用于 import 接口:把任意来源的文本(JSON / curl)解析成 draft profile
class ProfileImportIn(BaseModel):
    text: str
    fallback_name: str = ""


class ProfileTestStartIn(BaseModel):
    """临时测试一个未保存的 profile,或测试已保存 profile 的某次草稿。"""
    profile: LlmProfileIn
