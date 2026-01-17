from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select

from apps.plant_backend.deps import require_perm
from apps.plant_backend.models import ReasonSuggestion
from apps.plant_backend.services import suggestion_approve
from common_core.db import PlantSessionLocal

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.get("/list")
def list_suggestions(status: str = "pending", user=Depends(require_perm("master.manage"))):
    db = PlantSessionLocal()
    try:
        q = (
            select(ReasonSuggestion)
            .where(ReasonSuggestion.status == status)
            .order_by(desc(ReasonSuggestion.count))
        )
        rows = db.execute(q).scalars().all()
        return [
            {
                "id": r.id,
                "suggested_name": r.suggested_name,
                "count": r.count,
                "status": r.status,
                "threshold": r.threshold,
            }
            for r in rows
        ]
    finally:
        db.close()


@router.post("/approve")
def approve(body: dict, user=Depends(require_perm("master.manage"))):
    sid = body.get("suggestion_id")
    code = body.get("item_code")
    if not sid or not code:
        raise HTTPException(status_code=400, detail="suggestion_id and item_code required")
    db = PlantSessionLocal()
    try:
        suggestion_approve(db, sid, code, user["sub"])
        db.commit()
        return {"ok": True}
    finally:
        db.close()
