"""Skill 抽象。

每个 Skill 包含:
- name / description / json_schema(给 LLM 看)
- side_effect 分类(给前端确认卡片决定 default-confirm 还是 auto)
- execute(args, ctx) -> SkillResult
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal, Protocol


SideEffect = Literal["create", "update", "delete", "read", "compose"]


@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema(顶层 type=object)


@dataclass
class SkillContext:
    """Skill 执行时拿到的服务句柄。所有 skill 都共享同一组依赖。"""
    project_id: str
    project_service: Any           # ProjectService
    # 可继续扩展:knowledge_store / llm / ...


@dataclass
class SkillResult:
    ok: bool
    text: str                      # 给 LLM 看的执行回执(简短描述)
    data: dict[str, Any] = field(default_factory=dict)   # 结构化结果(给前端 Card 渲染)
    affects: dict[str, bool] = field(default_factory=dict)  # tree/doc/meta 等


class Skill(Protocol):
    schema: ToolSchema
    side_effect: SideEffect

    async def execute(self, args: dict, ctx: SkillContext) -> SkillResult: ...


# 简化版:用函数 + 元数据组合代替写一堆 class
@dataclass
class FunctionSkill:
    schema: ToolSchema
    side_effect: SideEffect
    handler: Callable[[dict, SkillContext], Awaitable[SkillResult]]

    async def execute(self, args: dict, ctx: SkillContext) -> SkillResult:
        return await self.handler(args, ctx)
