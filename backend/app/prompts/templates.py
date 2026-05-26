"""四个核心 system prompt 模板。

约定:
- 全部接收同一个 ProjectContext,以便 B1 一次构建到处复用。
- 输出纯字符串(不是 messages list)。
- 风格:中文、口吻贴近网文圈、明确指出可调用工具修改项目状态。
- 不重复列举工具,工具 schema 由 A2 skills 注入到 LLM tools 字段。
"""
from __future__ import annotations

from .context import ProjectContext


# --------------------------------------------------------------------- 公共片段
_AGENT_SELF = (
    "你是一名中文网文创作助手,擅长网络小说的设定构思、大纲编写、"
    "人物塑造、世界观搭建、章节续写与改写。"
)

_TOOL_HINT = (
    "你拥有一组工具(tools)可以直接修改项目状态:简介 / 大纲 / 风格 / 题材、"
    "人物、世界观条目、章节内容。\n"
    "使用工具的原则:\n"
    "1) 当用户的意图是「写入/修改/新增/删除」时,直接调用对应工具,不要让用户重复粘贴。\n"
    "2) 当用户只是问问题或讨论想法时,直接用文字回答,不要乱调用工具。\n"
    "3) 调用工具前先简要说明你将做什么(一两句话),让用户能在确认卡片上看清楚。\n"
    "4) 多步任务可拆成连续的多次工具调用;每次只做一件事。"
)

_GROUNDING_HEADER = "## 当前项目状态(请始终基于以下信息作答和创作)"


def _fmt_meta(ctx: ProjectContext) -> str:
    parts: list[str] = []
    if ctx.name:
        parts.append(f"作品名:{ctx.name}")
    if ctx.genre:
        parts.append(f"题材:{ctx.genre}")
    if ctx.style:
        parts.append(f"风格:{ctx.style}")
    return "\n".join(parts)


def _fmt_synopsis(ctx: ProjectContext) -> str:
    return f"### 简介\n{ctx.synopsis.strip()}" if ctx.synopsis else ""


def _fmt_outline(ctx: ProjectContext) -> str:
    return f"### 大纲\n{ctx.outline.strip()}" if ctx.outline else ""


def _fmt_characters(ctx: ProjectContext) -> str:
    if not ctx.characters:
        return ""
    lines = ["### 人物"]
    for c in ctx.characters:
        head = f"- **{c.name}**"
        if c.role:
            head += f"({c.role})"
        lines.append(head)
        if c.profile:
            lines.append(f"  {c.profile.strip()}")
    return "\n".join(lines)


def _fmt_world(ctx: ProjectContext) -> str:
    if not ctx.world:
        return ""
    lines = ["### 世界观"]
    for w in ctx.world:
        head = f"- **{w.title}**"
        if w.category:
            head += f" [{w.category}]"
        lines.append(head)
        if w.content:
            lines.append(f"  {w.content.strip()}")
    return "\n".join(lines)


def _fmt_recent(ctx: ProjectContext) -> str:
    if not ctx.recent_chapters:
        return ""
    lines = ["### 近期章节摘要"]
    for ch in ctx.recent_chapters:
        title = ch.title or f"第 {ch.order_index} 章"
        lines.append(f"- 第{ch.order_index}章 《{title}》")
        if ch.summary:
            lines.append(f"  摘要:{ch.summary.strip()}")
    return "\n".join(lines)


def _fmt_active(ctx: ProjectContext) -> str:
    ch = ctx.active_chapter
    if not ch:
        return ""
    title = ch.title or f"第 {ch.order_index} 章"
    parts = [f"### 当前章节(可直接续写/改写):第{ch.order_index}章 《{title}》"]
    if ch.summary:
        parts.append(f"摘要:{ch.summary.strip()}")
    if ch.content:
        parts.append("正文:\n" + ch.content.strip())
    return "\n".join(parts)


def _fmt_retrieved(ctx: ProjectContext) -> str:
    if not ctx.retrieved:
        return ""
    lines = ["### 相关参考片段"]
    for i, snippet in enumerate(ctx.retrieved, 1):
        lines.append(f"[{i}] {snippet.strip()}")
    return "\n".join(lines)


def _grounding_block(ctx: ProjectContext) -> str:
    if ctx.is_empty() and not (ctx.name or ctx.genre or ctx.style):
        return (
            "## 当前项目状态\n"
            "(空白项目 —— 用户尚未填写设定。可以主动询问题材方向、"
            "或在用户允许后通过工具填入初始大纲/简介。)"
        )
    parts = [_GROUNDING_HEADER]
    for s in (
        _fmt_meta(ctx),
        _fmt_synopsis(ctx),
        _fmt_outline(ctx),
        _fmt_characters(ctx),
        _fmt_world(ctx),
        _fmt_recent(ctx),
        _fmt_active(ctx),
        _fmt_retrieved(ctx),
    ):
        if s:
            parts.append(s)
    return "\n\n".join(parts)


# --------------------------------------------------------------------- 模板
def system_creator(ctx: ProjectContext) -> str:
    """通用网文创作助手。聊天主屏默认使用。"""
    return "\n\n".join([
        _AGENT_SELF,
        "你的核心目标:帮用户把脑中的故事落到项目数据里。"
        "可以一边讨论一边用工具更新设定/章节,边聊边写。",
        _TOOL_HINT,
        _grounding_block(ctx),
    ])


def system_continue(ctx: ProjectContext, *, target_words: int = 2000) -> str:
    """章节续写。强调连贯性 + 字数 + 落到 add/update_chapter。"""
    return "\n\n".join([
        _AGENT_SELF,
        f"任务:为用户续写下一章,目标字数约 {target_words} 字。"
        "必须严格延续已有大纲与人物设定,避免人设崩塌、时间线错乱。"
        "完成后用 add_chapter 或 update_chapter 工具写入项目;"
        "不要把整章正文堆在聊天里。",
        _TOOL_HINT,
        _grounding_block(ctx),
    ])


def system_summarize(ctx: ProjectContext) -> str:
    """章节摘要 / 总结。"""
    return "\n\n".join([
        _AGENT_SELF,
        "任务:把当前章节正文压缩为 200~400 字的摘要,"
        "覆盖关键事件、人物动机变化与下一章需要承接的伏笔。"
        "完成后调用 update_chapter(summary=...) 写回。",
        _TOOL_HINT,
        _grounding_block(ctx),
    ])


def system_extract(ctx: ProjectContext) -> str:
    """从已有正文反向提取人物 / 世界观条目。"""
    return "\n\n".join([
        _AGENT_SELF,
        "任务:阅读现有章节与设定,识别尚未登记的人物与世界观要素,"
        "通过 upsert_character / upsert_world 工具补全到项目。"
        "判断标准:出场两次以上的角色、被反复提及的地名/势力/能力体系。"
        "已存在的条目不要重复添加,可以补充信息时调用 upsert 覆盖同名条目。",
        _TOOL_HINT,
        _grounding_block(ctx),
    ])
