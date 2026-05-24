from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SO_", env_file=".env", extra="ignore")

    slicer_bin: str = "/usr/bin/snapmaker-orca"
    slicer_resources_dir: str = "/usr/share/snapmaker-orca/resources"
    work_dir: str = "/var/lib/snapmaker-orca-api/work"
    db_url: str = "sqlite+aiosqlite:///./snapmaker_orca_api.db"

    host: str = "0.0.0.0"
    port: int = 8090
    cors_origins: str = "http://localhost:5173"

    slice_timeout_sec: int = 600
    max_upload_mb: int = 256

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def work_path(self) -> Path:
        p = Path(self.work_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def uploads_path(self) -> Path:
        p = self.work_path / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def jobs_path(self) -> Path:
        p = self.work_path / "jobs"
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
