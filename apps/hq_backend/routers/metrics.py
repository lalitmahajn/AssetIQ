from fastapi import APIRouter
from sqlalchemy import select, func
from common_core.db import HQSessionLocal
from apps.hq_backend.models import DeadLetter
router = APIRouter(tags=["metrics"])

@router.get("/metrics")
def metrics():
    db = HQSessionLocal()
    try:
        dead = db.execute(select(func.count()).select_from(DeadLetter)).scalar_one()
        return f"assetiq_dead_letter_total {dead}\n"
    finally:
        db.close()
