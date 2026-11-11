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
        default=Path("data/radar.db"),
        validation_alias=AliasChoices("SARDEGNA_RADAR_DB_PATH", "db_path"),
    )
    min_alert_score: float = Field(
        default=45.0,
        ge=0.0,
        le=100.0,
        validation_alias=AliasChoices("SARDEGNA_RADAR_MIN_ALERT_SCORE", "min_alert_score"),
    )
    http_timeout_seconds: float = Field(
        default=20.0,
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

    # Telegram Bot API
    telegram_bot_token: str = Field(
        default="",
        validation_alias=AliasChoices("TELEGRAM_BOT_TOKEN", "telegram_bot_token"),
    )
    telegram_chat_id: str = Field(
        default="",
        validation_alias=AliasChoices("TELEGRAM_CHAT_ID", "telegram_chat_id"),
    )

    # Dual-Ready Supabase Postgres (used automatically when configured)
    supabase_url: str = Field(
        default="",
        validation_alias=AliasChoices("SUPABASE_URL", "supabase_url"),
    )
    supabase_service_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "SUPABASE_SERVICE_ROLE_KEY",
            "SUPABASE_KEY",
            "supabase_service_key",
        ),
    )

    # Optional lightweight OpenAI-compatible LLM refiner for ambiguous CME descriptions
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY", "llm_api_key"),
    )
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "llm_base_url"),
    )
    llm_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("LLM_MODEL", "llm_model"),
    )

    # Configurable Company Ground Truth (Sardinian Precast Concrete & Construction Supplier)
    company_name: str = Field(
        default="Sardinian Precast Concrete & Construction Supplier",
        validation_alias=AliasChoices("COMPANY_NAME", "company_name"),
    )
    company_piva: str = Field(
        default="00000000000",
        validation_alias=AliasChoices("COMPANY_PIVA", "company_piva"),
    )
    company_rea: str = Field(
        default="NU-00000",
        validation_alias=AliasChoices("COMPANY_REA", "company_rea"),
    )
    company_albo_artigiani: str = Field(
        default="NU-00000",
        validation_alias=AliasChoices("COMPANY_ALBO_ARTIGIANI", "company_albo_artigiani"),
    )
    company_ateco_primary: str = Field(
        default="23.61.0",
        validation_alias=AliasChoices("COMPANY_ATECO_PRIMARY", "company_ateco_primary"),
    )
    company_base_municipality: str = Field(
        default="Nuoro",
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

    @property
    def supabase_enabled(self) -> bool:
        """Return True when Supabase URL and Service Key are configured."""
        return bool(self.supabase_url.strip() and self.supabase_service_key.strip())

    @property
    def llm_enabled(self) -> bool:
        """Return True when an optional LLM API key is configured for CME refinement."""
        return bool(self.llm_api_key.strip())
