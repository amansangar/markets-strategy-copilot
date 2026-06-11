from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_REPO_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[3])).resolve()
LATEST_SUPPORTED_OPENAI_MODEL = "gpt-5.5"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=DEFAULT_REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Markets Strategy Copilot API"
    app_env: str = "development"
    database_url: str = "sqlite:///./markets_strategy_copilot.db"
    openai_api_key: str | None = None
    polygon_api_key: str | None = None
    newsapi_api_key: str | None = None
    apca_api_key_id: str | None = None
    apca_api_secret_key: str | None = None
    fred_api_key: str | None = None
    sec_user_agent: str | None = None
    finnhub_api_key: str | None = None
    alphavantage_api_key: str | None = None
    fmp_api_key: str | None = None
    twelvedata_api_key: str | None = None
    marketaux_api_key: str | None = None
    eodhd_api_key: str | None = None
    next_public_clerk_publishable_key: str | None = None
    clerk_secret_key: str | None = None
    resend_api_key: str | None = None
    resend_from_email: str | None = None
    live_default_mode: str = "demo"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])
    openai_model: str = "latest"
    demo_seed: int = 22044744
    project_root: Path | None = None
    data_dir: Path | None = None
    artefacts_dir: Path | None = None

    @property
    def repo_root(self) -> Path:
        if self.project_root:
            return Path(self.project_root)
        if self.data_dir:
            return self.data_dir.parent
        return DEFAULT_REPO_ROOT

    @property
    def resolved_openai_model(self) -> str:
        """Map beginner-friendly aliases to real OpenAI API model IDs."""

        model = (self.openai_model or "").strip()
        if not model or model.lower() in {"latest", "auto", "default"}:
            return LATEST_SUPPORTED_OPENAI_MODEL
        return model

    @property
    def resolved_data_dir(self) -> Path:
        if self.data_dir:
            return Path(self.data_dir)
        return self.repo_root / "data"

    @property
    def resolved_artefacts_dir(self) -> Path:
        if self.artefacts_dir:
            return Path(self.artefacts_dir)
        return self.repo_root / "artefacts"

    def ensure_dirs(self) -> None:
        self.resolved_artefacts_dir.mkdir(parents=True, exist_ok=True)
        (self.resolved_artefacts_dir / "exports").mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
