from __future__ import annotations

from common_core.config import settings


def get_vault_root() -> str:
    return settings.report_vault_root


def hot_days() -> int:
    return int(settings.report_hot_days)


def archive_days() -> int:
    return int(settings.report_archive_days)


def cold_enabled() -> bool:
    return bool(settings.report_cold_enabled)
