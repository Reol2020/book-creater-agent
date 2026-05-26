"""项目状态修改类技能。所有写入都走 ProjectService -> Repo,保持单一写路径。

约定:
- 所有 skill 第一个参数都是 args dict(LLM 给的 JSON),第二个是 SkillContext。
- project_id 不在 args 里;统一从 ctx.project_id 拿,LLM 只关心业务字段。
- 返回 SkillResult.text 短一句话,LLM 看后会决定是否继续调下一个。
"""
from __future__ import annotations

from app.domain.models import Chapter, Character, WorldEntry

from .base import FunctionSkill, SkillContext, SkillResult, ToolSchema
from .registry import SkillRegistry


# ============================================================ Project meta
async def _set_project_field(field: str, args: dict, ctx: SkillContext) -> SkillResult:
    value = (args.get("value") or "").strip()
    project = await ctx.project_service.get(ctx.project_id)
    setattr(project, field, value)
    await ctx.project_service.update(project)
    return SkillResult(
        ok=True,
        text=f"已更新「{field}」({len(value)} 字)。",
        data={"field": field, "value": value},
        affects={"meta": True},
    )


def _meta_skill(name: str, field: str, label: str) -> FunctionSkill:
    return FunctionSkill(
        schema=ToolSchema(
            name=name,
            description=f"设置/覆盖项目的「{label}」字段。整段替换,不是追加。",
            parameters={
                "type": "object",
                "properties": {
                    "value": {"type": "string", "description": f"完整的{label}文本"},
                },
                "required": ["value"],
            },
        ),
        side_effect="update",
        handler=lambda a, c, _f=field: _set_project_field(_f, a, c),
    )


# ============================================================ Character
async def _upsert_character(args: dict, ctx: SkillContext) -> SkillResult:
    name = (args.get("name") or "").strip()
    if not name:
        return SkillResult(ok=False, text="人物名不能为空。")
    role = (args.get("role") or "").strip()
    profile = (args.get("profile") or "").strip()

    # 同名替换:先查列表
    existing = await ctx.project_service.list_characters(ctx.project_id)
    target = next((c for c in existing if c.name == name), None)
    if target:
        target.role = role or target.role
        target.profile = profile or target.profile
        saved = await ctx.project_service.upsert_character(target)
        verb = "更新"
    else:
        saved = await ctx.project_service.upsert_character(
            Character(project_id=ctx.project_id, name=name, role=role, profile=profile)
        )
        verb = "新增"
    return SkillResult(
        ok=True,
        text=f"已{verb}人物「{name}」。",
        data={"id": saved.id, "name": saved.name, "role": saved.role},
        affects={"tree": True},
    )


async def _delete_character(args: dict, ctx: SkillContext) -> SkillResult:
    cid = args.get("id")
    name = (args.get("name") or "").strip()
    if not cid and name:
        existing = await ctx.project_service.list_characters(ctx.project_id)
        target = next((c for c in existing if c.name == name), None)
        if not target:
            return SkillResult(ok=False, text=f"未找到人物「{name}」。")
        cid = target.id
    if not cid:
        return SkillResult(ok=False, text="需要 id 或 name 之一。")
    await ctx.project_service.delete_character(cid)
    return SkillResult(ok=True, text=f"已删除人物「{name or cid}」。", affects={"tree": True})


# ============================================================ World
async def _upsert_world(args: dict, ctx: SkillContext) -> SkillResult:
    title = (args.get("title") or "").strip()
    if not title:
        return SkillResult(ok=False, text="世界观条目标题不能为空。")
    category = (args.get("category") or "").strip()
    content = (args.get("content") or "").strip()

    existing = await ctx.project_service.list_world(ctx.project_id)
    target = next((w for w in existing if w.title == title), None)
    if target:
        target.category = category or target.category
        target.content = content or target.content
        saved = await ctx.project_service.upsert_world(target)
        verb = "更新"
    else:
        saved = await ctx.project_service.upsert_world(
            WorldEntry(project_id=ctx.project_id, title=title, category=category, content=content)
        )
        verb = "新增"
    return SkillResult(
        ok=True,
        text=f"已{verb}世界观条目「{title}」。",
        data={"id": saved.id, "title": saved.title, "category": saved.category},
        affects={"tree": True},
    )


async def _delete_world(args: dict, ctx: SkillContext) -> SkillResult:
    eid = args.get("id")
    title = (args.get("title") or "").strip()
    if not eid and title:
        existing = await ctx.project_service.list_world(ctx.project_id)
        target = next((w for w in existing if w.title == title), None)
        if not target:
            return SkillResult(ok=False, text=f"未找到世界观条目「{title}」。")
        eid = target.id
    if not eid:
        return SkillResult(ok=False, text="需要 id 或 title 之一。")
    await ctx.project_service.delete_world(eid)
    return SkillResult(ok=True, text=f"已删除世界观条目「{title or eid}」。", affects={"tree": True})


async def _list_world(args: dict, ctx: SkillContext) -> SkillResult:
    items = await ctx.project_service.list_world(ctx.project_id)
    return SkillResult(
        ok=True,
        text=f"项目目前有 {len(items)} 条世界观条目。",
        data={"items": [{"id": w.id, "title": w.title, "category": w.category} for w in items]},
    )


# ============================================================ Chapter
async def _add_chapter(args: dict, ctx: SkillContext) -> SkillResult:
    title = (args.get("title") or "").strip()
    summary = (args.get("summary") or "").strip()
    content = (args.get("content") or "").strip()
    existing = await ctx.project_service.list_chapters(ctx.project_id)
    order_index = len(existing) + 1
    saved = await ctx.project_service.create_chapter(
        Chapter(
            project_id=ctx.project_id,
            title=title or f"第 {order_index} 章",
            summary=summary,
            content=content,
            order_index=order_index,
        )
    )
    return SkillResult(
        ok=True,
        text=f"已新增章节「{saved.title}」({len(content)} 字)。",
        data={"id": saved.id, "order_index": saved.order_index, "title": saved.title},
        affects={"tree": True, "doc": True},
    )


async def _update_chapter(args: dict, ctx: SkillContext) -> SkillResult:
    cid = args.get("id")
    if not cid:
        # 允许通过 order_index 定位
        idx = args.get("order_index")
        chapters = await ctx.project_service.list_chapters(ctx.project_id)
        target = next((c for c in chapters if c.order_index == idx), None) if idx else None
        if not target:
            return SkillResult(ok=False, text="需要 id 或有效的 order_index。")
        cid = target.id
    chapters = await ctx.project_service.list_chapters(ctx.project_id)
    target = next((c for c in chapters if c.id == cid), None)
    if not target:
        return SkillResult(ok=False, text=f"未找到章节 {cid}。")
    if "title" in args and args["title"] is not None:
        target.title = args["title"].strip()
    if "summary" in args and args["summary"] is not None:
        target.summary = args["summary"].strip()
    if "content" in args and args["content"] is not None:
        target.content = args["content"]
    saved = await ctx.project_service.update_chapter(target)
    return SkillResult(
        ok=True,
        text=f"已更新章节「{saved.title}」。",
        data={"id": saved.id, "title": saved.title, "word_count": saved.word_count},
        affects={"doc": True},
    )


async def _read_chapter(args: dict, ctx: SkillContext) -> SkillResult:
    chapters = await ctx.project_service.list_chapters(ctx.project_id)
    cid = args.get("id")
    idx = args.get("order_index")
    target = None
    if cid:
        target = next((c for c in chapters if c.id == cid), None)
    elif idx:
        target = next((c for c in chapters if c.order_index == idx), None)
    if not target:
        return SkillResult(ok=False, text="未找到对应章节。")
    return SkillResult(
        ok=True,
        text=f"读取章节「{target.title}」共 {target.word_count} 字。",
        data={
            "id": target.id, "order_index": target.order_index,
            "title": target.title, "summary": target.summary, "content": target.content,
        },
    )


async def _list_chapters(args: dict, ctx: SkillContext) -> SkillResult:
    chapters = await ctx.project_service.list_chapters(ctx.project_id)
    return SkillResult(
        ok=True,
        text=f"项目共 {len(chapters)} 个章节。",
        data={"items": [
            {"id": c.id, "order_index": c.order_index, "title": c.title, "word_count": c.word_count}
            for c in chapters
        ]},
    )


# ============================================================ 注册入口
def register_project_skills(reg: SkillRegistry) -> None:
    # ---- meta
    for name, field, label in [
        ("set_synopsis", "synopsis", "简介"),
        ("set_outline", "outline", "大纲"),
        ("set_style", "style", "文风"),
        ("set_genre", "genre", "题材"),
    ]:
        reg.register(_meta_skill(name, field, label))

    # ---- character
    reg.register(FunctionSkill(
        schema=ToolSchema(
            name="upsert_character",
            description="新增或更新人物。同名条目会被覆盖。",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "人物名称"},
                    "role": {"type": "string", "description": "主角 / 配角 / 反派 等"},
                    "profile": {"type": "string", "description": "人物详细描述,markdown"},
                },
                "required": ["name"],
            },
        ),
        side_effect="update",
        handler=_upsert_character,
    ))
    reg.register(FunctionSkill(
        schema=ToolSchema(
            name="delete_character",
            description="按 id 或 name 删除人物。",
            parameters={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                },
            },
        ),
        side_effect="delete",
        handler=_delete_character,
    ))

    # ---- world
    reg.register(FunctionSkill(
        schema=ToolSchema(
            name="upsert_world",
            description="新增或更新世界观条目(地点/势力/能力体系等)。同标题覆盖。",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "category": {"type": "string", "description": "设定 / 地理 / 势力 / 法术体系 …"},
                    "content": {"type": "string"},
                },
                "required": ["title"],
            },
        ),
        side_effect="update",
        handler=_upsert_world,
    ))
    reg.register(FunctionSkill(
        schema=ToolSchema(
            name="delete_world",
            description="按 id 或 title 删除世界观条目。",
            parameters={
                "type": "object",
                "properties": {"id": {"type": "string"}, "title": {"type": "string"}},
            },
        ),
        side_effect="delete",
        handler=_delete_world,
    ))
    reg.register(FunctionSkill(
        schema=ToolSchema(
            name="list_world",
            description="列出当前项目所有世界观条目。",
            parameters={"type": "object", "properties": {}},
        ),
        side_effect="read",
        handler=_list_world,
    ))

    # ---- chapter
    reg.register(FunctionSkill(
        schema=ToolSchema(
            name="add_chapter",
            description="在末尾新增一章。order_index 自动分配。",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "content": {"type": "string", "description": "章节正文"},
                },
            },
        ),
        side_effect="create",
        handler=_add_chapter,
    ))
    reg.register(FunctionSkill(
        schema=ToolSchema(
            name="update_chapter",
            description="更新章节标题/摘要/正文。需提供 id 或 order_index。",
            parameters={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "order_index": {"type": "integer"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
        ),
        side_effect="update",
        handler=_update_chapter,
    ))
    reg.register(FunctionSkill(
        schema=ToolSchema(
            name="read_chapter",
            description="读取章节正文。需提供 id 或 order_index。",
            parameters={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "order_index": {"type": "integer"},
                },
            },
        ),
        side_effect="read",
        handler=_read_chapter,
    ))
    reg.register(FunctionSkill(
        schema=ToolSchema(
            name="list_chapters",
            description="列出当前项目所有章节(不含正文)。",
            parameters={"type": "object", "properties": {}},
        ),
        side_effect="read",
        handler=_list_chapters,
    ))
