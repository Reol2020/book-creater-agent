"""SkillRegistry —— 注册 + 查询 + LLM tools schema 转换。"""
from __future__ import annotations

from typing import Any

from .base import FunctionSkill, Skill, SkillContext, SkillResult


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.schema.name] = skill

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def names(self) -> list[str]:
        return list(self._skills.keys())

    # ------------------------------------------------------- LLM 适配
    def anthropic_tools(self) -> list[dict[str, Any]]:
        """Anthropic Messages API 的 tools 字段格式。"""
        return [
            {
                "name": s.schema.name,
                "description": s.schema.description,
                "input_schema": s.schema.parameters,
            }
            for s in self._skills.values()
        ]

    def openai_tools(self) -> list[dict[str, Any]]:
        """OpenAI Chat Completions / Responses 的 tools 字段格式。"""
        return [
            {
                "type": "function",
                "function": {
                    "name": s.schema.name,
                    "description": s.schema.description,
                    "parameters": s.schema.parameters,
                },
            }
            for s in self._skills.values()
        ]

    # ------------------------------------------------------- 执行
    async def dispatch(self, name: str, args: dict, ctx: SkillContext) -> SkillResult:
        skill = self.get(name)
        if skill is None:
            return SkillResult(ok=False, text=f"未知工具:{name}")
        try:
            return await skill.execute(args or {}, ctx)
        except Exception as e:  # noqa: BLE001
            return SkillResult(ok=False, text=f"{name} 执行失败:{e}")


def build_default_registry() -> SkillRegistry:
    """组装项目内置技能集合。"""
    from .project_skills import register_project_skills

    reg = SkillRegistry()
    register_project_skills(reg)
    return reg


__all__ = ["SkillRegistry", "build_default_registry", "FunctionSkill", "SkillContext", "SkillResult"]
