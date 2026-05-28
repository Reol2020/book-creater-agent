"""应用配置 (pydantic-settings)。

所有运行期配置都从环境变量 / .env 读取,domain / application 层不直接看见。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    # ---------- App ----------
    app_name: str = Field(default="book-creater-agent", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    # ---------- Logging ----------
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="", alias="LOG_FILE")  # 留空则用 data_dir/logs/app.log
    log_max_bytes: int = Field(default=5_000_000, alias="LOG_MAX_BYTES")
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")

    # ---------- Storage ----------
    data_dir: str = Field(default="./data", alias="DATA_DIR")

    # ---------- Embedding (M2 用,先占位) ----------
    embedding_provider: str = Field(default="local", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="BAAI/bge-small-zh-v1.5", alias="EMBEDDING_MODEL")

    # ---------- Default LLM (可被 LlmProfile 覆盖) ----------
    default_llm_provider: str = Field(default="anthropic", alias="LLM_PROVIDER")
    default_llm_model: str = Field(default="claude-sonnet-4-5", alias="LLM_MODEL")

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def sqlite_url(self) -> str:
        return f"sqlite+aiosqlite:///{(self.data_path / 'app.db').as_posix()}"

    @property
    def chroma_path(self) -> Path:
        p = self.data_path / "chroma"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
