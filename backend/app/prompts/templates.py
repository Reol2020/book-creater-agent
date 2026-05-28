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

_PLAN_MODE = (
    "## 对话原则(非常重要)\n"
    "你工作在 plan 模式 —— 默认要先沟通,再动笔。绝不能让用户长时间盯着「思考中」。\n"
    "\n"
    "**重活前先 plan**:遇到「写一章 / 写大纲 / 大改写 / 设计一个新人物或世界观」这类需要"
    "生成大段内容的请求时,**禁止直接动笔写正文**。先用 1-2 段简短文字做这几件事:\n"
    "  a) 结合前文(已有大纲、上一章结尾、既定人设)给出 1-2 条具体建议或观察;\n"
    "  b) 抛 2-3 个发展方向 / 节奏 / 视角 / 关键事件的选项,标号让用户挑;\n"
    "  c) 询问还需要确认的关键信息(目标字数、是否引入新角色等),最多问 1-2 个最关键的。\n"
    "  然后停下来等用户回复,**这一轮不要调用任何写章节/写大纲的工具**。\n"
    "\n"
    "**确认后再动笔**:用户回复选择或说「就按这个来 / 直接开始 / 你定」之后,**写之前**先用一句话"
    "复述方案(\"好的,我按 X 思路开写第 N 章,目标 ~M 字,重点是 …\"),再调用写入工具。\n"
    "\n"
    "**例外:续写 skill / 明确指令直接写**\n"
    "  - 系统使用「续写」专用 prompt(system_continue)进入时,可直接动笔(那是用户主动点了"
    "「续写下一章」按钮,等同于已确认)。\n"
    "  - 用户明确说「不用问了直接写 / 跳过讨论 / 你看着办」,也可直接写,但仍要先一句话说明意图。\n"
    "\n"
    "**轻活直接做**:小修小补类(改个名字、删一个条目、调整一句简介、补一个人物字段)不需要 plan,"
    "按 _TOOL_HINT 直接调工具即可。\n"
    "\n"
    "**永远先发声**:不管是讨论、提问还是动笔,本轮的第一段输出必须是给用户看的文字 —— "
    "禁止「沉默思考很久后突然蹦出一整章」。"
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
        "做法是「先聊清楚,再动笔」—— 重活之前一定要和用户对齐方向、给出选项、"
        "拿到确认,然后才调用写入类工具。轻活可以边聊边改。",
        _PLAN_MODE,
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
