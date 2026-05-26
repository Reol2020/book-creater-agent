"""桌面启动入口。

用法:
  - 开发:`python -m app.launcher`
  - 打包:PyInstaller 用这个文件做 entry,生成 BookCreaterAgent.exe

行为:
  1. 把工作目录切到 exe 所在目录,这样 data/ 落在用户能看到的地方
  2. 在浏览器里打开 http://127.0.0.1:<port>
  3. 跑 uvicorn(默认 127.0.0.1:8765,只听本机,不开放外网)
"""
from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def _runtime_dir() -> Path:
    """exe 所在目录(用户感知的安装位置);开发模式下退化为当前 cwd。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def _is_port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind((host, port))
        except OSError:
            return False
    return True


def _pick_port(host: str, preferred: int) -> int:
    # 偏好端口被占就向后递增,最多 50 次
    for p in range(preferred, preferred + 50):
        if _is_port_free(host, p):
            return p
    raise RuntimeError(f"找不到可用端口(尝试 {preferred}..{preferred + 50})")


def _open_browser_later(url: str, delay: float = 1.5) -> None:
    def _go():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass

    threading.Thread(target=_go, daemon=True).start()


def main() -> None:
    rt = _runtime_dir()
    os.chdir(rt)

    # 让 DATA_DIR 默认落到 exe 同级 data/(可被 .env 覆盖)
    os.environ.setdefault("DATA_DIR", str(rt / "data"))
    # 单实例下不需要 CORS,但保留 localhost 以便开发者本机调试
    os.environ.setdefault("CORS_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000")

    host = os.environ.get("APP_HOST", DEFAULT_HOST)
    preferred_port = int(os.environ.get("APP_PORT", DEFAULT_PORT))
    port = _pick_port(host, preferred_port)
    url = f"http://{host}:{port}"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("launcher")
    log.info("=" * 60)
    log.info("Book Creater Agent")
    log.info("正在启动,稍后将自动打开浏览器: %s", url)
    log.info("数据目录: %s", os.environ["DATA_DIR"])
    log.info("关闭此窗口即可退出程序")
    log.info("=" * 60)

    _open_browser_later(url)

    # 延迟 import,避免在 PyInstaller 解析时太早触发 settings 解析
    import uvicorn

    from app.main import app

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
