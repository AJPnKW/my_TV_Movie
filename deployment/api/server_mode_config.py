"""Configuration helpers for server-mode API and workers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def repo_root() -> Path:
    env_root = os.environ.get("MYTV_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ServerModeConfig:
    repo_root: Path
    api_host: str
    api_port: int
    base_path: str
    postgres_dsn: str | None

    @classmethod
    def from_env(cls) -> "ServerModeConfig":
        return cls(
            repo_root=repo_root(),
            api_host=os.environ.get("MYTV_API_HOST", "127.0.0.1"),
            api_port=int(os.environ.get("MYTV_API_PORT", "8000")),
            base_path=os.environ.get("MYTV_API_BASE_PATH", "/api/v1").rstrip("/"),
            postgres_dsn=os.environ.get("MYTV_POSTGRES_DSN") or os.environ.get("DATABASE_URL"),
        )

    def data_path(self, *parts: str) -> Path:
        return self.repo_root.joinpath("data", *parts)

    def web_path(self, *parts: str) -> Path:
        return self.repo_root.joinpath("web", *parts)

    def schema_path(self) -> Path:
        return self.repo_root / "deployment" / "postgres" / "schema_v1.sql"
