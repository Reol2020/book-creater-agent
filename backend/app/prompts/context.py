"""ProjectContext —— 注入到每条 system prompt 里的项目快照。

由 B1 ProjectContextBuilder 按 token 预算切片填充。
此处只定义结构,不做检索/裁剪逻辑(单一职责)。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CharacterBrief:
    name: str
    role: str = ""
    profile: str = ""


@dataclass
class WorldBrief:
    title: str
    category: str = ""
    content: str = ""


@dataclass
class ChapterBrief:
    order_index: int
    title: str
    summary: str = ""
    content: str = ""  # 可能被截断


@dataclass
class ProjectContext:
    """注入 system prompt 的项目状态切片。所有字段都是已经裁剪后的安全长度。"""
    project_id: str = ""
    name: str = ""
    genre: str = ""
    style: str = ""
    synopsis: str = ""
    outline: str = ""
    characters: list[CharacterBrief] = field(default_factory=list)
    world: list[WorldBrief] = field(default_factory=list)
    recent_chapters: list[ChapterBrief] = field(default_factory=list)
    active_chapter: ChapterBrief | None = None
    # 检索回的额外片段(B2 RAG 填充)
    retrieved: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (
            self.synopsis or self.outline or self.characters
            or self.world or self.recent_chapters or self.active_chapter
        )
