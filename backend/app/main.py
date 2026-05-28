"""FastAPI 入口。

打包成 exe 时 PyInstaller 会把 frontend/out 拷到 sys._MEIPASS/static/,
后端在这种情况下额外挂载静态文件 → 单 exe 同时承载 API 与 UI。
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.adapters.inbound.api import chat, health, projects, settings
from app.config.container import build_container, shutdown_container
from app.config.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = await build_container()
    app.state.container = container
    try:
        yield
    finally:
        await shutdown_container(container)


def _frontend_static_dir() -> Path | None:
    """寻找前端静态资源目录。

    优先级:
      1. 环境变量 FRONTEND_DIST(开发期手动指定)
      2. PyInstaller bundle 的 sys._MEIPASS/static
      3. 项目内 frontend/out(开发期跑过 build:static 后)
    找不到就返回 None,完全跳过静态托管(纯 API 模式)。
    """
    env = os.environ.get("FRONTEND_DIST")
    if env and Path(env).is_dir():
        return Path(env)

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        p = Path(meipass) / "static"
        if p.is_dir():
            return p

    here = Path(__file__).resolve()
    for candidate in (
        here.parents[2] / "frontend" / "out",  # repo root / frontend / out
        here.parents[1] / "frontend" / "out",
    ):
        if candidate.is_dir():
            return candidate
    return None


def _setup_logging(cfg) -> Path:
    """配置 root logger:控制台 + 滚动文件。

    返回最终落盘的日志文件路径(用于在启动日志里告诉用户去哪看)。
    所有 uvicorn / app.* / httpx 的日志都会走 root,统一到一个文件,
    便于排查 "AI 长时间思考中" 这类阻塞问题。
    """
    log_file = cfg.log_file.strip()
    if log_file:
        log_path = Path(log_file).expanduser().resolve()
    else:
        log_path = cfg.data_path / "logs" / "app.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, cfg.log_level.upper(), logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    root = logging.getLogger()
    # 重复 create_app 时清掉旧 handler,避免日志翻倍
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(level)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        filename=str(log_path),
        maxBytes=cfg.log_max_bytes,
        backupCount=cfg.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # uvicorn 默认有自己的 handler,移除让它们走 root
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True

    return log_path


def create_app() -> FastAPI:
    cfg = get_settings()
    log_path = _setup_logging(cfg)
    logging.getLogger(__name__).info("日志文件: %s", log_path)

    app = FastAPI(title=cfg.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(chat.router)
    app.include_router(settings.router)

    static_dir = _frontend_static_dir()
    if static_dir:
        # 必须在 API router 之后挂载,否则会吞掉 /api/*
        app.mount(
            "/",
            StaticFiles(directory=str(static_dir), html=True),
            name="frontend",
        )
        logging.getLogger(__name__).info("前端静态目录: %s", static_dir)
    else:
        logging.getLogger(__name__).info(
            "未找到前端静态资源,仅启用 API 模式 (开发期请单独跑 npm run dev)"
        )

    return app


app = create_app()
