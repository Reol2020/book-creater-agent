"""文件存储接口 —— 导入文件 / 备份 / 大附件。"""
from __future__ import annotations

from typing import Protocol


class FileStorage(Protocol):
    async def save_bytes(self, key: str, data: bytes) -> str:
        """保存,返回可重新读取的引用(本地实现就是路径)。"""
        ...

    async def read_bytes(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...
