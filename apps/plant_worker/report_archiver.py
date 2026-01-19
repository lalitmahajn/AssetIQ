from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from common_core.vault_policy import (
    archive_days,
    cold_enabled,
    get_vault_root,
    hot_days,
    retention_days,
)


def _ensure(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def run_once() -> dict:
    root = Path(get_vault_root())
    hot = root / "hot"
    archive = root / "archive"
    cold = root / "cold"
    _ensure(hot)
    _ensure(archive)
    _ensure(cold)

    now = datetime.utcnow()
    hot_cut = now - timedelta(days=hot_days())
    arch_cut = now - timedelta(days=archive_days())
    purge_cut = now - timedelta(days=retention_days())

    moved_hot_to_archive = 0
    moved_archive_to_cold = 0
    purged_files = 0

    # 1. Hot -> Archive
    for p in hot.rglob("*"):
        if p.is_file() and datetime.utcfromtimestamp(p.stat().st_mtime) < hot_cut:
            rel = p.relative_to(hot)
            dst = archive / rel
            _ensure(dst.parent)
            shutil.move(str(p), str(dst))
            moved_hot_to_archive += 1

    # 2. Archive -> Cold
    if cold_enabled():
        for p in archive.rglob("*"):
            if p.is_file() and datetime.utcfromtimestamp(p.stat().st_mtime) < arch_cut:
                rel = p.relative_to(archive)
                dst = cold / rel
                _ensure(dst.parent)
                shutil.move(str(p), str(dst))
                moved_archive_to_cold += 1

    # 3. Purge old files (PDF, XLSX) from entire vault
    # Note: We don't touch the DB record (ReportRequest), only the physical files.
    for p in root.rglob("*"):
        if p.is_file():
            if p.suffix.lower() in [".pdf", ".xlsx", ".csv"]:
                mtime = datetime.utcfromtimestamp(p.stat().st_mtime)
                if mtime < purge_cut:
                    p.unlink()
                    purged_files += 1

    summary = {
        "ts_utc": now.isoformat(),
        "moved_hot_to_archive": moved_hot_to_archive,
        "moved_archive_to_cold": moved_archive_to_cold,
        "purged_files": purged_files,
    }
    with (root / "archive_manifest.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(summary) + "\n")
    return summary
