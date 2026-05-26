"""Skills (tools) 注册表。

Agent loop 通过 SkillRegistry 拿到:
- LLM 端 tools schema(Anthropic / OpenAI 两种格式)
- 服务端 dispatch:根据工具名 + 参数 -> ToolResult
"""
from __future__ import annotations

from .base import Skill, SkillContext, SkillResult, ToolSchema
from .registry import SkillRegistry, build_default_registry

__all__ = [
    "Skill",
    "SkillContext",
    "SkillResult",
    "ToolSchema",
    "SkillRegistry",
    "build_default_registry",
]
