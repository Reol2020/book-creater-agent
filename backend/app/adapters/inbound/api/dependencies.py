"""FastAPI 依赖注入辅助。

Container 在 lifespan 里挂到 app.state,这里提供细粒度的 Depends。
"""
from __future__ import annotations

from fastapi import Depends, Request

from app.application.agent_service import AgentService
from app.application.chat_service import ChatService
from app.application.context_builder import ProjectContextBuilder
from app.application.project_service import ProjectService
from app.application.settings_service import SettingsService
from app.config.container import Container


def get_container(request: Request) -> Container:
    container: Container | None = getattr(request.app.state, "container", None)
    if container is None:
        raise RuntimeError("Container 未初始化")
    return container


def get_project_service(c: Container = Depends(get_container)) -> ProjectService:
    return c.project_service


def get_chat_service(c: Container = Depends(get_container)) -> ChatService:
    return c.chat_service


def get_settings_service(c: Container = Depends(get_container)) -> SettingsService:
    return c.settings_service


def get_agent_service(c: Container = Depends(get_container)) -> AgentService:
    return c.agent_service


def get_context_builder(c: Container = Depends(get_container)) -> ProjectContextBuilder:
    return c.context_builder
