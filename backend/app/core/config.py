from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ClinicVoice API Settings loaded from environment or .env file."""
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[3] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "local"
    DEBUG: bool = True
    APP_NAME: str = "ClinicVoice API"

    # Database & Redis
    DATABASE_URL: str = "postgresql+asyncpg://clinicvoice:clinicvoice_pass@localhost:5432/clinicvoice_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # S3 Object Storage
    OBJECT_STORAGE_ENDPOINT: str = "http://localhost:9000"
    OBJECT_STORAGE_BUCKET: str = "clinicvoice-recordings"
    OBJECT_STORAGE_KEY: str = "minioadmin"
    OBJECT_STORAGE_SECRET: str = "minioadmin"

    # Security
    JWT_SECRET: str = "insecure_dev_jwt_secret_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    INTERNAL_SERVICE_TOKEN: str = "dev_internal_service_token_123"

    # LiveKit
    LIVEKIT_URL: str = "ws://localhost:7880"
    LIVEKIT_API_KEY: str = "devkey"
    LIVEKIT_API_SECRET: str = "secret"
    LIVEKIT_SIP_DOMAIN: str = "voiceagent-6aqqbru4.sip.livekit.cloud"

    # AI & Speech Providers
    SARVAM_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_PROVIDER: str = "gemini"

    # Telephony (Exotel)
    EXOTEL_SID: str = ""
    EXOTEL_API_KEY: str = ""
    EXOTEL_API_TOKEN: str = ""


settings = Settings()
