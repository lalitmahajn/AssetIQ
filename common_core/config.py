from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    plant_site_code: str = Field(default="P01", alias="PLANT_SITE_CODE")

    plant_db_url: str = Field(
        default="postgresql+psycopg2://assetiq:assetiq@postgres:5432/assetiq_plant",
        alias="PLANT_DB_URL",
    )
    hq_db_url: str = Field(
        default="postgresql+psycopg2://assetiq:assetiq@postgres:5432/assetiq_hq",
        alias="HQ_DB_URL",
    )

    # Required secrets (NO DEFAULTS)
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    sync_hmac_secret: str = Field(..., alias="SYNC_HMAC_SECRET")
    station_secret_enc_key: str = Field(..., alias="STATION_SECRET_ENC_KEY")

    # JWT config
    jwt_issuer: str = Field(default="assetiq", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="assetiq_users", alias="JWT_AUDIENCE")
    jwt_ttl_minutes: int = Field(default=480, alias="JWT_TTL_MINUTES")

    # Optional: allow rotation
    sync_hmac_secret_prev: str = Field(default="", alias="SYNC_HMAC_SECRET_PREV")
    sync_hmac_kid: str = Field(default="k1", alias="SYNC_HMAC_KID")

    # HQ receiver url for Plant -> HQ sync (HQ optional)
    hq_receiver_url: str = Field(
        default="http://hq_backend:8001/sync/receive", alias="HQ_RECEIVER_URL"
    )

    # Email / SMTP
    smtp_host: str = Field(default="smtp", alias="SMTP_HOST")
    smtp_port: int = Field(default=25, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_pass: str = Field(default="", alias="SMTP_PASS")
    smtp_from: str = Field(default="assetiq@example.com", alias="SMTP_FROM")

    email_maintenance: str = Field(default="maintenance@example.com", alias="EMAIL_MAINTENANCE")
    email_supervisor: str = Field(default="supervisor@example.com", alias="EMAIL_SUPERVISOR")
    email_it: str = Field(default="it@example.com", alias="EMAIL_IT")

    report_vault_root: str = Field(default="/data/report_vault", alias="REPORT_VAULT_ROOT")
    report_hot_days: int = Field(default=30, alias="REPORT_HOT_DAYS")
    report_archive_days: int = Field(default=180, alias="REPORT_ARCHIVE_DAYS")
    report_cold_enabled: bool = Field(default=True, alias="REPORT_COLD_ENABLED")
    report_retention_days: int = Field(default=30, alias="REPORT_RETENTION_DAYS")

    # Phase-3 Intelligence (HQ add-on)
    enable_intelligence: bool = Field(default=False, alias="ENABLE_INTELLIGENCE")
    intelligence_window_days: int = Field(default=14, alias="INTELLIGENCE_WINDOW_DAYS")

    # Optional: HQ email digest for insights (opt-in)
    enable_intelligence_digest: bool = Field(default=False, alias="ENABLE_INTELLIGENCE_DIGEST")
    intelligence_digest_to: str = Field(default="", alias="INTELLIGENCE_DIGEST_TO")


settings = Settings()
