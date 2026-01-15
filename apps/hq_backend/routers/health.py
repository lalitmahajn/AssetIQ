from __future__ import annotations
from fastapi import APIRouter
from sqlalchemy import text
from common_core.db import HQSessionLocal

router = APIRouter(tags=["health"])

@router.get("/health/live")
def live():
    return {"ok": True}

@router.get("/health/ready")
def ready():
    db = HQSessionLocal()
    try:
        db.execute(text("SELECT 1"))
    finally:
        db.close()
    return {"ok": True}


@router.get("/healthz")
def healthz():
    return live()

@router.get("/readyz")
def readyz():
    return ready()
