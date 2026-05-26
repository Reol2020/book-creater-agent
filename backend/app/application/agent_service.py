"""AgentService —— 工具调用 + 流式回复 的 agent loop。

事件序列(给前端 SSE):
  started        : agent 开始,包含已注入的 system prompt 摘要
  token          : 增量文本(LLM 思考性输出)
  tool_call      : LLM 决定调用工具(name + arguments + side_effect + need_confirm)
  confirm_required : 服务端等待前端确认(side_effect ∈ {update, delete} 且 policy=default)
  tool_result    : 工具执行完毕(ok / text / data)
  done           : 整个 turn 结束(原因:end_turn / max_iters / cancelled)
  error          : 出错

confirm_policy:
  - "auto"        : 全部自动执行
  - "default"     : create/read 自动;update/delete 需前端确认 (M1 暂时按"全自动"跑通,
                    confirm_required 留作 M2 引入双向 channel 时使用)
  - "confirm-all" : 全部需要确认
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.domain.models import AssistantTurn, LlmProfile, ToolCall
from app.ports.llm_provider import LlmProvider
from app.ports.llm_profile_repository import LlmProfileRepository
from app.skills import SkillContext, SkillRegistry

_log = logging.getLogger(__name__)

MAX_TOOL_ITERS = 8


@dataclass
class AgentRequest:
    messages: list[dict]
    system: str
    project_id: str
    confirm_policy: str = "default"


class NoActiveProfileError(RuntimeError):
    pass


class AgentService:
    def __init__(
        self,
        llm: LlmProvider,
        profiles: LlmProfileRepository,
        skills: SkillRegistry,
        project_service,  # 避免循环引用,松类型
    ) -> None:
        self._llm = llm
        self._profiles = profiles
        self._skills = skills
        self._project_service = project_service

    async def run(self, req: AgentRequest) -> AsyncIterator[dict]:
        profile = await self._profiles.get_active()
        if profile is None:
            raise NoActiveProfileError("尚未启用 LLM 配置,请到设置页添加并启用一个。")

        ctx = SkillContext(project_id=req.project_id, project_service=self._project_service)
        # provider-aware tools schema
        if profile.provider == "openai":
            tools = self._skills.openai_tools()
        else:
            tools = self._skills.anthropic_tools()

        yield {"event": "started", "data": {"provider": profile.provider, "model": profile.model}}

        messages = list(req.messages)
        for it in range(MAX_TOOL_ITERS):
            try:
                turn: AssistantTurn = await self._llm.chat_with_tools(
                    profile, messages, tools=tools, system=req.system,
                )
            except Exception as e:  # noqa: BLE001
                _log.exception("agent llm call failed")
                yield {"event": "error", "data": {"title": "调用失败", "detail": str(e)}}
                return

            if turn.text:
                # 简单粒度:整段 text 作为 token 流出去(SDK 的工具回合不流式)
                # 切成 ~40 字一段,前端渲染观感更好
                async for chunk in _chunkify(turn.text, size=40, delay=0.0):
                    yield {"event": "token", "data": {"text": chunk}}

            if not turn.tool_calls:
                yield {"event": "done", "data": {"reason": turn.stop_reason}}
                return

            # 把这轮 assistant 回合(含 tool_use)按 provider 形态写回 messages
            messages.append(_assistant_message(profile, turn))

            tool_results: list[dict] = []
            for call in turn.tool_calls:
                skill = self._skills.get(call.name)
                side = skill.side_effect if skill else "unknown"
                need_confirm = _need_confirm(side, req.confirm_policy)
                yield {
                    "event": "tool_call",
                    "data": {
                        "id": call.id, "name": call.name,
                        "arguments": call.arguments,
                        "side_effect": side,
                        "need_confirm": need_confirm,
                    },
                }
                # M1:即便 need_confirm,服务端也直接执行(前端可基于事件展示提示)。
                # M2 再引入双向 channel 实现真正阻塞确认。
                result = await self._skills.dispatch(call.name, call.arguments, ctx)
                yield {
                    "event": "tool_result",
                    "data": {
                        "id": call.id, "name": call.name,
                        "ok": result.ok, "text": result.text,
                        "result": result.data,
                        "affects": result.affects,
                    },
                }
                tool_results.append({"call": call, "result": result})

            messages.extend(_tool_results_messages(profile, tool_results))

        yield {"event": "done", "data": {"reason": "max_iters"}}


# --------------------------------------------------------------------- 辅助
async def _chunkify(text: str, *, size: int, delay: float) -> AsyncIterator[str]:
    for i in range(0, len(text), size):
        yield text[i:i + size]
        if delay:
            await asyncio.sleep(delay)


def _need_confirm(side: str, policy: str) -> bool:
    if policy == "auto":
        return False
    if policy == "confirm-all":
        return True
    # default: 改/删要确认,新增/读取自动
    return side in ("update", "delete")


def _assistant_message(profile: LlmProfile, turn: AssistantTurn) -> dict:
    """把 assistant 工具回合按 provider 协议写回 messages。"""
    if profile.provider == "anthropic":
        content: list[dict] = []
        if turn.text:
            content.append({"type": "text", "text": turn.text})
        for c in turn.tool_calls:
            content.append({
                "type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments,
            })
        return {"role": "assistant", "content": content}
    # openai
    return {
        "role": "assistant",
        "content": turn.text or "",
        "tool_calls": [
            {
                "id": c.id, "type": "function",
                "function": {"name": c.name, "arguments": _json_dumps(c.arguments)},
            }
            for c in turn.tool_calls
        ],
    }


def _tool_results_messages(profile: LlmProfile, results: list[dict]) -> list[dict]:
    """返回需要追加到 messages 的若干条消息。

    - Anthropic: 一条 user message,content 是多个 tool_result 块。
    - OpenAI: 每个工具调用一条独立的 role=tool 消息。
    """
    if profile.provider == "anthropic":
        return [{
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": r["call"].id,
                    "content": r["result"].text,
                    "is_error": not r["result"].ok,
                }
                for r in results
            ],
        }]
    return [
        {"role": "tool", "tool_call_id": r["call"].id, "content": r["result"].text}
        for r in results
    ]


def _json_dumps(obj) -> str:
    import json as _json
    return _json.dumps(obj, ensure_ascii=False)
