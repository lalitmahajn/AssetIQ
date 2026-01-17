from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from common_core.vault_policy import archive_days, cold_enabled, get_vault_root, hot_days


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

    moved_hot_to_archive = 0
    moved_archive_to_cold = 0

    for p in hot.rglob("*"):
        if p.is_file() and datetime.utcfromtimestamp(p.stat().st_mtime) < hot_cut:
            rel = p.relative_to(hot)
            dst = archive / rel
            _ensure(dst.parent)
            shutil.move(str(p), str(dst))
            moved_hot_to_archive += 1

    if cold_enabled():
        for p in archive.rglob("*"):
            if p.is_file() and datetime.utcfromtimestamp(p.stat().st_mtime) < arch_cut:
                rel = p.relative_to(archive)
                dst = cold / rel
                _ensure(dst.parent)
                shutil.move(str(p), str(dst))
                moved_archive_to_cold += 1

    summary = {
        "ts_utc": now.isoformat(),
        "moved_hot_to_archive": moved_hot_to_archive,
        "moved_archive_to_cold": moved_archive_to_cold,
    }
    with (root / "archive_manifest.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(summary) + "\n")
    return summary
