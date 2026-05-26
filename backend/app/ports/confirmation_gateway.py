"""危险工具确认通道。

桌面版用 threading.Event + Qt Signal 阻塞 worker。web 版改成异步 Future:
  - agent_loop 调 request(tool_call) 拿到一个 Future
  - SSE 推 confirm_required 到前端
  - 前端弹模态,用户点击后 POST /api/agent/confirm/{id}
  - 路由层 fulfill(id, decision) 唤醒 Future
  - agent_loop 继续

接口故意不绑 SSE,这样以后可以接 CLI / WebSocket / 自动批准策略。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.models import ToolCall


@dataclass
class ConfirmationDecision:
    approved: bool
    edited_args: dict


class ConfirmationGateway(Protocol):
    async def request(self, session_id: str, tool_call: ToolCall) -> ConfirmationDecision:
        """挂起等待用户决策。超时由实现层定。"""
        ...

    def fulfill(self, session_id: str, request_id: str, decision: ConfirmationDecision) -> bool:
        """前端回执 → 唤醒 request。返回 True 表示成功匹配到等待中的请求。"""
        ...
