from __future__ import annotations

from common_core.config import settings


class ConfigError(RuntimeError):
    pass


def _must_set(name: str, value: str, min_len: int = 32) -> None:
    if not value:
        raise ConfigError(f"{name} is required")
    if value.strip().upper() == "CHANGE_ME":
        raise ConfigError(f"{name} must not be CHANGE_ME")
    if len(value) < min_len:
        raise ConfigError(f"{name} must be at least {min_len} chars")


def validate_runtime_secrets() -> None:
    _must_set("JWT_SECRET", settings.jwt_secret, 32)
    _must_set("SYNC_HMAC_SECRET", settings.sync_hmac_secret, 32)
    _must_set("STATION_SECRET_ENC_KEY", settings.station_secret_enc_key, 32)
