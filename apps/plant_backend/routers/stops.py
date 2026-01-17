from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from apps.plant_backend.security_deps import require_roles
from apps.plant_backend.services import open_stop, resolve_stop
from common_core.db import PlantSessionLocal

log = logging.getLogger("assetiq.stops")
router = APIRouter(prefix="/stops", tags=["stops"])


class ManualStopIn(BaseModel):
    asset_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=2000)


@router.post("/manual-open")
def manual_open(
    body: ManualStopIn,
    request: Request,
    claims=Depends(require_roles("maintenance", "supervisor", "admin")),
):
    db = PlantSessionLocal()
    try:
        res = open_stop(
            db,
            body.asset_id,
            body.reason,
            claims.get("sub"),
            None,
            getattr(request.state, "request_id", None),
        )
        db.commit()
        from apps.plant_backend.runtime import sse_bus

        sse_bus.publish(
            {
                "type": "STOP_OPEN",
                "asset_id": body.asset_id,
                "reason": body.reason,
                "stop_id": res["stop_id"],
            }
        )
        return {"ok": True, **res}
    except Exception as e:
        db.rollback()
        log.exception("manual_open_failed")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


class ResolveIn(BaseModel):
    resolution_text: str = Field(min_length=1, max_length=2000)


@router.post("/{stop_id}/resolve")
def resolve(
    stop_id: str,
    body: ResolveIn,
    request: Request,
    claims=Depends(require_roles("maintenance", "supervisor", "admin")),
):
    db = PlantSessionLocal()
    try:
        sq = resolve_stop(
            db,
            stop_id,
            body.resolution_text,
            claims.get("sub"),
            getattr(request.state, "request_id", None),
        )
        db.commit()
        from apps.plant_backend.runtime import sse_bus

        sse_bus.publish({"type": "STOP_RESOLVE", "stop_id": stop_id, "asset_id": sq.asset_id})
        return {
            "ok": True,
            "stop_id": sq.id,
            "closed_at_utc": (sq.closed_at_utc.isoformat() + "Z") if sq.closed_at_utc else None,
        }
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        log.exception("resolve_failed")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
