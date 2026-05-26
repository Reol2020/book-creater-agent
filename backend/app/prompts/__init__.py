"""Prompt 库。

设计:
- ProjectContext 是所有系统提示词共享的「项目快照」结构,B1 ContextBuilder 负责生成。
- 每个模板都是 (ctx: ProjectContext, **kwargs) -> str 的纯函数,易测、好替换。
- registry 用名字索引,Agent / 服务层通过 render(name, ctx, **kw) 调用,不直接 import 模板。
"""
from __future__ import annotations

from .context import ProjectContext
from .templates import (
    system_continue,
    system_creator,
    system_extract,
    system_summarize,
)

_REGISTRY = {
    "system_creator": system_creator,
    "system_continue": system_continue,
    "system_summarize": system_summarize,
    "system_extract": system_extract,
}


def render(name: str, ctx: ProjectContext, **kwargs) -> str:
    fn = _REGISTRY.get(name)
    if fn is None:
        raise KeyError(f"unknown prompt: {name}")
    return fn(ctx, **kwargs)


def list_prompts() -> list[str]:
    return list(_REGISTRY.keys())


__all__ = ["ProjectContext", "render", "list_prompts"]
