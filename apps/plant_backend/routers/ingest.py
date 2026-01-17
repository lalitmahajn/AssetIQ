from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from apps.plant_backend.models import IngestDedup
from apps.plant_backend.services import open_stop
from common_core.db import PlantSessionLocal

router = APIRouter(prefix="/ingest", tags=["ingest"])
log = logging.getLogger("assetiq.ingest")


class IngestEvent(BaseModel):
    event_type: str = Field(min_length=1, max_length=64)
    asset_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(default="", max_length=2000)
    occurred_at_utc: str = Field(min_length=10, max_length=40)
    source_id: str = Field(min_length=1, max_length=64)
    event_id: str = Field(min_length=1, max_length=128)


@router.post("/event")
def ingest_event(body: IngestEvent, request: Request):
    db = PlantSessionLocal()
    try:
        exists = db.execute(
            select(IngestDedup).where(
                IngestDedup.source_id == body.source_id, IngestDedup.event_id == body.event_id
            )
        ).scalar_one_or_none()
        if exists:
            return {"ok": True, "dedup": True}

        db.add(
            IngestDedup(
                source_id=body.source_id, event_id=body.event_id, created_at_utc=datetime.utcnow()
            )
        )

        if body.event_type in ("PLC_FAULT", "TECH_STOP"):
            res = open_stop(
                db,
                body.asset_id,
                body.reason or body.event_type,
                None,
                body.source_id,
                getattr(request.state, "request_id", None),
            )
            from apps.plant_backend.runtime import sse_bus

            sse_bus.publish(
                {
                    "type": "STOP_OPEN",
                    "stop_id": res["stop_id"],
                    "asset_id": body.asset_id,
                    "reason": body.reason,
                }
            )

        db.commit()
        return {"ok": True, "dedup": False}
    except Exception as e:
        db.rollback()
        log.exception("ingest_failed")
        raise HTTPException(status_code=400, detail="INGEST_FAILED") from e
    finally:
        db.close()
