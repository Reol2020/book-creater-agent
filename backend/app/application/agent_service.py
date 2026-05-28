"""AgentService —— 工具调用 + 流式回复 的 agent loop。

事件序列(给前端 SSE):
  started        : agent 开始,包含已注入的 system prompt 摘要
  token          : 增量文本(LLM 思考性输出)
  tool_call      : LLM 决定调用工具(name + arguments + side_effect + need_confirm)
  tool_progress  : LLM 正在生成 tool_use 块的 input(长章节正文等),活体心跳
  heartbeat      : 上游静默 > _HEARTBEAT_SEC 时发,告诉前端"后端还活着,在等上游"。
                   Mify 网关会把 input_json_delta 缓冲成几个大块,中间静默 30~60s 也是常态。
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
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.domain.models import AssistantTurn, LlmProfile, ToolCall
from app.ports.llm_provider import LlmProvider
from app.ports.llm_profile_repository import LlmProfileRepository
from app.skills import SkillContext, SkillRegistry

_log = logging.getLogger(__name__)

MAX_TOOL_ITERS = 8

# 上游(LLM/网关)静默超过这个秒数,主动发 heartbeat,前端据此知道后端没死。
# 4s 是个折中:小于 5s 让用户感觉响应及时,又不会与正常的 tool_progress(~0.8s 间隔)
# 抢资源(只有真静默时 timeout 才会触发)。
_HEARTBEAT_SEC = 4.0


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

        _log.info(
            "agent.run start project=%s provider=%s model=%s msgs=%d tools=%d",
            req.project_id, profile.provider, profile.model,
            len(req.messages), len(tools),
        )
        yield {"event": "started", "data": {"provider": profile.provider, "model": profile.model}}

        messages = list(req.messages)
        for it in range(MAX_TOOL_ITERS):
            _log.info("agent.iter %d/%d → calling llm (stream)", it + 1, MAX_TOOL_ITERS)
            turn: AssistantTurn | None = None

            # 用 queue + 后台 task 把 LLM 流和心跳计时器解耦,这样可以在上游
            # 静默时主动发心跳,而不会因为 wait_for 超时取消上游 stream(那会把
            # SDK 的 HTTP body 读一起 cancel,验证过)。
            queue: asyncio.Queue = asyncio.Queue()
            sentinel = object()

            async def _consume():
                try:
                    async for ev in self._llm.chat_with_tools_stream(
                        profile, messages, tools=tools, system=req.system,
                    ):
                        await queue.put(ev)
                except Exception as e:  # noqa: BLE001
                    await queue.put(("__exc__", e))
                finally:
                    await queue.put(sentinel)

            consumer = asyncio.create_task(_consume())
            silence_started_at = time.monotonic()
            try:
                while True:
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_SEC)
                    except asyncio.TimeoutError:
                        # 上游静默 ≥ _HEARTBEAT_SEC,发心跳告诉前端"还活着"
                        silent_for = time.monotonic() - silence_started_at
                        yield {
                            "event": "heartbeat",
                            "data": {"silent_seconds": round(silent_for, 1)},
                        }
                        continue
                    silence_started_at = time.monotonic()
                    if item is sentinel:
                        break
                    if isinstance(item, tuple) and item and item[0] == "__exc__":
                        raise item[1]
                    ev = item
                    if ev["type"] == "text_delta":
                        yield {"event": "token", "data": {"text": ev["text"]}}
                    elif ev["type"] == "tool_progress":
                        yield {
                            "event": "tool_progress",
                            "data": {
                                "id": ev.get("id"),
                                "name": ev.get("name"),
                                "chars": ev.get("chars", 0),
                                "phase": ev.get("phase", "delta"),
                            },
                        }
                    elif ev["type"] == "final":
                        turn = ev["turn"]
            except Exception as e:  # noqa: BLE001
                _log.exception("agent llm call failed")
                # 等 consumer task 自然结束,避免 generator 提前关闭报警
                if not consumer.done():
                    consumer.cancel()
                yield {"event": "error", "data": {"title": "调用失败", "detail": str(e)}}
                return
            finally:
                # 正常路径下 consumer 已经结束并写入 sentinel,这里 await 应当立即返回
                if not consumer.done():
                    try:
                        await asyncio.wait_for(consumer, timeout=0.5)
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        consumer.cancel()

            if turn is None:
                yield {"event": "error", "data": {"title": "调用失败", "detail": "LLM 未返回 final"}}
                return

            _log.info(
                "agent.iter %d returned text=%d tools=%d stop=%s",
                it + 1, len(turn.text or ""),
                len(turn.tool_calls), turn.stop_reason,
            )

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
