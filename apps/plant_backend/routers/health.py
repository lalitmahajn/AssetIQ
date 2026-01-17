from __future__ import annotations

import os

from fastapi import APIRouter
from sqlalchemy import text

from common_core.config import settings
from common_core.db import PlantSessionLocal

router = APIRouter(tags=["health"])


@router.get("/health/live")
def live():
    return {"ok": True}


@router.get("/health/ready")
def ready():
    db = PlantSessionLocal()
    try:
        db.execute(text("SELECT 1"))
    finally:
        db.close()

    root = settings.report_vault_root
    os.makedirs(root, exist_ok=True)
    test_path = os.path.join(root, ".write_check")
    with open(test_path, "w", encoding="utf-8") as f:
        f.write("ok")
    import contextlib

    with contextlib.suppress(OSError):
        os.remove(test_path)
    return {"ok": True, "site_code": settings.plant_site_code}


@router.get("/healthz")
def healthz():
    return live()


@router.get("/readyz")
def readyz():
    return ready()
