# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置。

跑法: pyinstaller --clean build.spec
要求: frontend/out 已经构建好(由 build_release.bat 负责)。
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve()                # backend/
REPO = ROOT.parent                             # repo root
FRONTEND_OUT = REPO / "frontend" / "out"

# ---------- 数据文件 ----------
datas = []
if FRONTEND_OUT.is_dir():
    # 把 out/ 整体作为 static/ 拷进 bundle (sys._MEIPASS/static/)
    datas.append((str(FRONTEND_OUT), "static"))

# 第三方库的 data files / 隐藏依赖
for pkg in ("anthropic", "openai",
            "pydantic", "pydantic_core", "fastapi", "starlette",
            "uvicorn", "sqlalchemy", "aiosqlite", "httpx", "httpcore",
            "h11", "anyio", "certifi"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        # binaries/hiddenimports 通过下面的列表汇总
    except Exception:
        pass

# ---------- 隐藏依赖 ----------
hiddenimports = []
for pkg in (
    "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.protocols", "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto", "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "aiosqlite",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.aiosqlite",
    "anthropic", "openai",
    "app.main", "app.launcher",
):
    hiddenimports.append(pkg)

# 收集子模块,避免动态 import 漏掉
for pkg in ("anthropic", "openai", "uvicorn", "sqlalchemy"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass


a = Analysis(
    [str(ROOT / "app" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PIL", "PySide6", "PyQt5", "PyQt6"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BookCreaterAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,                 # 第一版保留控制台,方便看日志;稳定后改 False
    disable_windowed_traceback=False,
    icon=None,                    # 后续可以加 app.ico
)
