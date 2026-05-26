"""SQLite + SQLAlchemy async engine 和 session factory。"""
from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class Database:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False 让连接可以跨 task 用;async + WAL 模式天然支持并发读
        url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
        self.engine = create_async_engine(url, echo=False, future=True)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def init(self) -> None:
        # 启用 WAL,支持并发读
        async with self.engine.begin() as conn:
            await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
            await conn.exec_driver_sql("PRAGMA foreign_keys=ON;")
            from app.adapters.outbound.persistence.sqlite.orm import Base
            await conn.run_sync(Base.metadata.create_all)
            # 轻量列迁移:把后期新增的列补到旧库上(SQLite 没有 IF NOT EXISTS,需先查)
            await self._migrate_add_columns(conn)

    async def _migrate_add_columns(self, conn) -> None:
        """对已存在的表追加新增列。无 ORM 升级框架时的过渡方案。"""
        new_columns: dict[str, list[tuple[str, str]]] = {
            "llm_profile": [
                ("extra_headers", "JSON DEFAULT '{}'"),
                ("verified_at", "DATETIME"),
            ],
        }
        for table, cols in new_columns.items():
            existing = {
                row[1]
                for row in (await conn.exec_driver_sql(f"PRAGMA table_info({table})")).all()
            }
            for col_name, col_type in cols:
                if col_name not in existing:
                    await conn.exec_driver_sql(
                        f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"
                    )

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as s:
            yield s

    async def dispose(self) -> None:
        await self.engine.dispose()
