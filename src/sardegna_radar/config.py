"""Application configuration backed by Pydantic Settings."""

from __future__ import annotations

from pathlib import Path
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RadarSettings(BaseSettings):
    """Runtime settings for the Sardegna B2B Tender & Procurement Radar."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_path: Path = Field(
        default=Path("data/sardegna_radar.db"),
        validation_alias=AliasChoices("SARDEGNA_RADAR_DB_PATH", "db_path"),
    )
    min_alert_score: float = Field(
        default=45.0,
        ge=0.0,
        le=100.0,
        validation_alias=AliasChoices("SARDEGNA_RADAR_MIN_ALERT_SCORE", "min_alert_score"),
    )
    http_timeout_seconds: float = Field(
        default=15.0,
        gt=0.0,
        validation_alias=AliasChoices("SARDEGNA_RADAR_HTTP_TIMEOUT_SECONDS", "http_timeout_seconds"),
    )
    http_connect_timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        validation_alias=AliasChoices(
            "SARDEGNA_RADAR_HTTP_CONNECT_TIMEOUT_SECONDS",
            "http_connect_timeout_seconds",
        ),
    )
    http_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        validation_alias=AliasChoices("SARDEGNA_RADAR_HTTP_MAX_RETRIES", "http_max_retries"),
    )
    adaptive_storage_dir: Path = Field(
        default=Path("data/adaptive_selectors"),
        validation_alias=AliasChoices(
            "SARDEGNA_RADAR_ADAPTIVE_STORAGE_DIR",
            "adaptive_storage_dir",
        ),
    )

    telegram_bot_token: str = Field(
        default="",
        validation_alias=AliasChoices("TELEGRAM_BOT_TOKEN", "telegram_bot_token"),
    )
    telegram_chat_id: str = Field(
        default="",
        validation_alias=AliasChoices("TELEGRAM_CHAT_ID", "telegram_chat_id"),
    )

    company_name: str = Field(
        default="Sardegna Prefabbricati C.A.V. S.r.l.",
        validation_alias=AliasChoices("COMPANY_NAME", "company_name"),
    )
    company_piva: str = Field(
        default="00000000000",
        validation_alias=AliasChoices("COMPANY_PIVA", "company_piva"),
    )
    company_base_municipality: str = Field(
        default="Silanus",
        validation_alias=AliasChoices("COMPANY_BASE_MUNICIPALITY", "company_base_municipality"),
    )
    company_base_province: str = Field(
        default="NU",
        validation_alias=AliasChoices("COMPANY_BASE_PROVINCE", "company_base_province"),
    )

    @property
    def telegram_enabled(self) -> bool:
        """Return True when both Telegram Bot Token and Chat ID are configured."""
        return bool(self.telegram_bot_token.strip() and self.telegram_chat_id.strip())
