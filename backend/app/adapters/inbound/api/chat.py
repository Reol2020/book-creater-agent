"""SSE 流式聊天端点。

- /api/chat/stream       : M0 纯文本流式(无工具)
- /api/chat/agent-stream : M1 Agent loop,带工具调用 + 项目上下文注入
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.application.agent_service import AgentRequest, AgentService
from app.application.agent_service import NoActiveProfileError as AgentNoProfile
from app.application.chat_service import ChatService, NoActiveProfileError
from app.application.context_builder import ProjectContextBuilder
from app.prompts import render as render_prompt

from .dependencies import get_agent_service, get_chat_service, get_context_builder
from .schemas import ChatStreamIn

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _sse(event: str, data: dict) -> bytes:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


@router.post("/stream")
async def chat_stream(
    body: ChatStreamIn,
    svc: ChatService = Depends(get_chat_service),
):
    msgs = [m.model_dump() for m in body.messages]

    async def gen():
        try:
            async for token in svc.stream(msgs, system=body.system):
                yield _sse("token", {"text": token})
            yield _sse("done", {})
        except NoActiveProfileError as e:
            yield _sse("error", {"title": "未启用 LLM 配置", "detail": str(e)})
        except Exception as e:  # noqa: BLE001
            _log.exception("chat stream failed")
            yield _sse("error", {"title": "调用失败", "detail": str(e)})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/agent-stream")
async def agent_stream(
    body: ChatStreamIn,
    agent: AgentService = Depends(get_agent_service),
    ctx_builder: ProjectContextBuilder = Depends(get_context_builder),
):
    """Agent 模式:LLM 可调用项目工具,system prompt 由项目上下文动态构建。"""
    if not body.project_id:
        raise HTTPException(400, "agent-stream 需要 project_id")

    msgs = [m.model_dump() for m in body.messages]
    prompt_name = "system_creator"  # 后续可由 body 指定

    last_user = next((m for m in reversed(msgs) if m.get("role") == "user"), None)
    rag_query = (last_user or {}).get("content") if last_user else None

    async def gen():
        try:
            project_ctx = await ctx_builder.build(body.project_id, query=rag_query)
            system = render_prompt(prompt_name, project_ctx)
            req = AgentRequest(
                messages=msgs,
                system=system,
                project_id=body.project_id,
                confirm_policy=body.confirm_policy or "default",
            )
            async for ev in agent.run(req):
                yield _sse(ev["event"], ev.get("data", {}))
        except AgentNoProfile as e:
            yield _sse("error", {"title": "未启用 LLM 配置", "detail": str(e)})
        except LookupError as e:
            yield _sse("error", {"title": "项目不存在", "detail": str(e)})
        except Exception as e:  # noqa: BLE001
            _log.exception("agent stream failed")
            yield _sse("error", {"title": "调用失败", "detail": str(e)})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
