"""业务模型 —— 纯 dataclass,零框架依赖。

ORM 实体(SQLAlchemy)在 adapters/outbound/persistence/sqlite/orm.py 定义,
通过 mapper 在 adapter 内部转换。这样换 ORM / 换数据库时 domain 完全不动。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


def _new_id() -> str:
    return uuid4().hex


def _now() -> datetime:
    return datetime.utcnow()


# ============================================================ Project & 内容
@dataclass
class Project:
    name: str
    genre: str = ""
    synopsis: str = ""
    style: str = ""
    outline: str = ""
    id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


@dataclass
class Chapter:
    project_id: str
    title: str = ""
    summary: str = ""
    content: str = ""
    order_index: int = 0
    id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @property
    def word_count(self) -> int:
        return len(self.content)


@dataclass
class Character:
    project_id: str
    name: str
    role: str = ""           # 主角 / 配角 / 反派 …
    profile: str = ""        # 长 markdown 描述
    id: str = field(default_factory=_new_id)


@dataclass
class WorldEntry:
    project_id: str
    title: str
    category: str = ""       # 设定 / 地理 / 势力 / 法术体系 …
    content: str = ""
    id: str = field(default_factory=_new_id)


# ============================================================ 知识库
class KnowledgeKind(str, Enum):
    DESIGN = "design"            # 用户/AI 自己写的构思、灵感、伏笔
    REFERENCE = "reference"      # 导入的外部作品片段


@dataclass
class KnowledgeItem:
    """向量库元数据 —— 真正的 embedding 由 KnowledgeStore 持久化。"""
    project_id: str
    kind: KnowledgeKind
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    source: str = ""             # 导入的文件名 / URL,用户笔记可空
    id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)


# ============================================================ LLM 配置
class LlmAuthType(str, Enum):
    API_KEY = "api_key"          # Anthropic 直连 → x-api-key
    BEARER = "bearer"            # 网关 → Authorization: Bearer xxx


@dataclass
class LlmProfile:
    """对应桌面版 LLMProfile。多套 profile,UI 里挑一个 active。"""
    name: str
    provider: str                # "anthropic" | "openai"
    model: str
    api_key: str = ""
    base_url: str = ""
    auth_type: LlmAuthType = LlmAuthType.API_KEY
    max_tokens: int = 16384
    temperature: float = 0.7
    extra_headers: dict[str, str] = field(default_factory=dict)
    verified_at: Optional[datetime] = None
    id: str = field(default_factory=_new_id)


# ============================================================ Agent 通信
@dataclass
class ToolCall:
    name: str
    arguments: dict
    id: str = field(default_factory=_new_id)


@dataclass
class ToolResult:
    ok: bool
    text: str
    side_effect: str = ""
    affects_tree: bool = False
    affects_doc: bool = False
    affects_meta: bool = False


@dataclass
class AssistantTurn:
    """LLM 一轮回复。文本 + 0..N 个工具调用。"""
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
