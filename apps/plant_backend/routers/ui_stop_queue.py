from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from common_core.db import PlantSessionLocal
from apps.plant_backend.models import StopQueue
from apps.plant_backend.deps import require_perm
from apps.plant_backend.services import resolve_stop

router = APIRouter(prefix="/ui/stop-queue", tags=["ui-stop-queue"])

@router.get("/list")
def list_stops(status: str = "OPEN", limit: int = 50, offset: int = 0, user=Depends(require_perm("stop.view"))):
    db = PlantSessionLocal()
    try:
        q = select(StopQueue).order_by(StopQueue.opened_at_utc.desc()).limit(limit).offset(offset)
        if status.upper() == "OPEN":
            q = q.where(StopQueue.is_open.is_(True))
        elif status.upper() == "CLOSED":
            q = q.where(StopQueue.is_open.is_(False))
        rows = db.execute(q).scalars().all()
        items = [{
            "id": r.id,
            "site_code": r.site_code,
            "asset_id": r.asset_id,
            "reason": r.reason,
            "is_open": r.is_open,
            "opened_at_utc": r.opened_at_utc.isoformat(),
            "closed_at_utc": r.closed_at_utc.isoformat() if r.closed_at_utc else None,
        } for r in rows]
        return {"items": items, "page": {"limit": limit, "offset": offset, "returned": len(items)}}
    finally:
        db.close()

@router.post("/resolve")
def resolve(body: dict, request: Request, user=Depends(require_perm("stop.resolve"))):
    stop_queue_id = body.get("stop_queue_id", "")
    resolution_text = body.get("resolution_text", "Resolved")
    if not stop_queue_id:
        raise HTTPException(status_code=400, detail="stop_queue_id required")
    db = PlantSessionLocal()
    try:
        sq = resolve_stop(db, stop_id=stop_queue_id, resolution_text=resolution_text, actor_user_id=user["sub"] if user else "ui", request_id=getattr(request.state, "request_id", None))
        db.commit()
        from apps.plant_backend.runtime import sse_bus
        sse_bus.publish({"type":"STOP_RESOLVED", "stop_queue_id": sq.id})
        return {"ok": True, "id": sq.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
