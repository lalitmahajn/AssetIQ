from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from common_core.config import settings
from common_core.db import HQSessionLocal
from apps.hq_backend.models import (
    AppliedCorrelation,
    DeadLetter,
    RollupDaily,
    EmailQueue,
    PlantRegistry,
    TicketSnapshot,
    TimelineEventHQ,
)
from apps.hq_backend.schema_validate import validate_entity

router = APIRouter(prefix="/sync", tags=["sync"])


def _now() -> datetime:
    return datetime.utcnow()


def _verify_signature(raw: bytes, sig: str) -> None:
    expected = hmac.new(settings.sync_hmac_secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=401, detail="invalid_signature")


class SyncItem(BaseModel):
    site_code: str = Field(..., min_length=1, max_length=16)
    entity_type: str = Field(..., min_length=1, max_length=32)
    entity_id: str = Field(..., min_length=1, max_length=64)
    payload: Dict[str, Any]
    correlation_id: str = Field(..., min_length=1, max_length=128)


class BatchPayload(BaseModel):
    items: List[SyncItem]


@router.post("/receive")
async def receive(request: Request) -> Dict[str, Any]:
    raw = await request.body()
    sig = request.headers.get("X-Signature", "")
    if not sig:
        raise HTTPException(status_code=401, detail="missing_signature")
    _verify_signature(raw, sig)

    try:
        data = json.loads(raw.decode("utf-8"))
        batch = BatchPayload.model_validate(data)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_payload")

    db = HQSessionLocal()
    applied = 0
    skipped = 0
    failed = 0
    now = _now()
    try:
        for item in batch.items:
            # idempotency gate
            if db.get(AppliedCorrelation, item.correlation_id) is not None:
                skipped += 1
                continue

            try:
                validate_entity(item.entity_type, {**item.payload, "site_code": item.site_code, "entity_id": item.entity_id})
            except Exception as e:
                _dead_letter(db, item, now, f"schema_invalid: {str(e)[:200]}")
                failed += 1
                continue

            try:
                _upsert_plant(db, item.site_code, now)

                if item.entity_type == "rollup":
                    _apply_rollup(db, item, now)
                elif item.entity_type == "ticket":
                    _apply_ticket(db, item, now)
                elif item.entity_type == "timeline_event":
                    _apply_timeline_event(db, item, now)
                else:
                    # Unknown types are not applied in Phase-2 (visibility only)
                    pass

                db.add(AppliedCorrelation(correlation_id=item.correlation_id, created_at_utc=now))
                applied += 1
            except Exception as e:
                _dead_letter(db, item, now, f"apply_failed: {str(e)[:200]}")
                failed += 1

        db.commit()
        return {"applied": applied, "skipped": skipped, "failed": failed}
    finally:
        db.close()


def _dead_letter(db, item: SyncItem, now: datetime, error: str) -> None:
    db.add(
        DeadLetter(
            site_code=item.site_code,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            correlation_id=item.correlation_id,
            payload_json=json.dumps(item.payload, separators=(",", ":"), ensure_ascii=False),
            error=error,
            created_at_utc=now,
        )
    )
    # Alert IT via email queue (HQ side)
    db.add(
        EmailQueue(
            to_email=settings.email_it,
            subject=f"AssetIQ HQ dead-letter ({item.site_code})",
            body=f"Sync item moved to dead-letter. Type={item.entity_type} Entity={item.entity_id} Correlation={item.correlation_id} Error={error}",
            status="PENDING",
            created_at_utc=now,
            sent_at_utc=None,
        )
    )


def _upsert_plant(db, site_code: str, now: datetime) -> None:
    plant = db.get(PlantRegistry, site_code)
    if plant is None:
        db.add(
            PlantRegistry(
                site_code=site_code,
                display_name=site_code,
                is_active=True,
                last_seen_at_utc=now,
                created_at_utc=now,
                updated_at_utc=now,
            )
        )
    else:
        plant.last_seen_at_utc = now
        plant.updated_at_utc = now


def _apply_rollup(db, item: SyncItem, now: datetime) -> None:
    p = item.payload
    day_utc = str(p.get("day_utc", ""))[:10]
    if not day_utc:
        raise ValueError("missing day_utc")
    existing = db.execute(
        select(RollupDaily).where(RollupDaily.site_code == item.site_code, RollupDaily.day_utc == day_utc)
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            RollupDaily(
                site_code=item.site_code,
                day_utc=day_utc,
                stops=int(p.get("stops", 0)),
                faults=int(p.get("faults", 0)),
                tickets_open=int(p.get("tickets_open", 0)),
                sla_breaches=int(p.get("sla_breaches", 0)),
                downtime_minutes=int(p.get("downtime_minutes", 0)),
                updated_at_utc=now,
            )
        )
    else:
        existing.stops = int(p.get("stops", existing.stops or 0))
        existing.faults = int(p.get("faults", existing.faults or 0))
        existing.tickets_open = int(p.get("tickets_open", existing.tickets_open or 0))
        existing.sla_breaches = int(p.get("sla_breaches", existing.sla_breaches or 0))
        existing.downtime_minutes = int(p.get("downtime_minutes", existing.downtime_minutes or 0))
        existing.updated_at_utc = now
        
    # Process Stop Reasons (Nested List)
    stop_reasons = p.get("stop_reasons", [])
    print(f"DEBUG: Processing rollup. Site={item.site_code} Day={day_utc} ReasonsCount={len(stop_reasons)} PayloadReasons={stop_reasons}", flush=True)
    
    if stop_reasons and isinstance(stop_reasons, list):
        from apps.hq_backend.models import StopReasonDaily
        for sr in stop_reasons:
            reason_code = str(sr.get("reason_code", "UNKNOWN"))[:64]
            # Upsert StopReasonDaily
            # Constraint is usually (site_code, day_utc, reason_code)
            sr_existing = db.execute(
                select(StopReasonDaily).where(
                    StopReasonDaily.site_code == item.site_code,
                    StopReasonDaily.day_utc == day_utc,
                    StopReasonDaily.reason_code == reason_code
                )
            ).scalar_one_or_none()
            
            if sr_existing is None:
                db.add(StopReasonDaily(
                    site_code=item.site_code,
                    day_utc=day_utc,
                    reason_code=reason_code,
                    stops=int(sr.get("stops", 0)),
                    downtime_minutes=int(sr.get("downtime_minutes", 0))
                ))
            else:
                sr_existing.stops = int(sr.get("stops", 0))
                sr_existing.downtime_minutes = int(sr.get("downtime_minutes", 0))



def _apply_ticket(db, item: SyncItem, now: datetime) -> None:
    p = item.payload
    ticket_id = item.entity_id
    existing = db.execute(
        select(TicketSnapshot).where(TicketSnapshot.site_code == item.site_code, TicketSnapshot.ticket_id == ticket_id)
    ).scalar_one_or_none()

    def _dt(v: Optional[str]) -> Optional[datetime]:
        if not v:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return None

    if existing is None:
        db.add(
            TicketSnapshot(
                site_code=item.site_code,
                ticket_id=ticket_id,
                asset_id=str(p.get("asset_id", "")),
                title=str(p.get("title", ""))[:256],
                status=str(p.get("status", "OPEN"))[:32],
                priority=str(p.get("priority", "MEDIUM"))[:32],
                created_at_utc=_dt(p.get("created_at_utc")) or now,
                sla_due_at_utc=_dt(p.get("sla_due_at_utc")),
                acknowledged_at_utc=_dt(p.get("acknowledged_at_utc")),
                resolved_at_utc=_dt(p.get("resolved_at_utc")),
                updated_at_utc=now,
            )
        )
    else:
        existing.asset_id = str(p.get("asset_id", existing.asset_id))
        existing.title = str(p.get("title", existing.title))[:256]
        existing.status = str(p.get("status", existing.status))[:32]
        existing.priority = str(p.get("priority", existing.priority))[:32]
        existing.sla_due_at_utc = _dt(p.get("sla_due_at_utc")) or existing.sla_due_at_utc
        existing.acknowledged_at_utc = _dt(p.get("acknowledged_at_utc")) or existing.acknowledged_at_utc
        existing.resolved_at_utc = _dt(p.get("resolved_at_utc")) or existing.resolved_at_utc
        existing.updated_at_utc = now


def _apply_timeline_event(db, item: SyncItem, now: datetime) -> None:
    p = item.payload
    event_id = item.entity_id

    def _dt(v: Optional[str]) -> datetime:
        if not v:
            return now
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return now

    existing = db.execute(
        select(TimelineEventHQ).where(TimelineEventHQ.site_code == item.site_code, TimelineEventHQ.event_id == event_id)
    ).scalar_one_or_none()

    if existing is None:
        db.add(
            TimelineEventHQ(
                site_code=item.site_code,
                event_id=event_id,
                event_type=str(p.get("event_type", ""))[:32],
                occurred_at_utc=_dt(p.get("occurred_at_utc")),
                asset_id=(str(p.get("asset_id"))[:128] if p.get("asset_id") is not None else None),
                reason_code=(str(p.get("reason_code"))[:64] if p.get("reason_code") is not None else None),
                duration_seconds=int(p.get("duration_seconds", 0) or 0),
                payload_json=p,
            )
        )
    else:
        # keep append-only semantics; only allow filling missing optional fields
        if not existing.reason_code and p.get("reason_code"):
            existing.reason_code = str(p.get("reason_code"))[:64]
        if not existing.asset_id and p.get("asset_id"):
            existing.asset_id = str(p.get("asset_id"))[:128]
        if not existing.duration_seconds and p.get("duration_seconds"):
            existing.duration_seconds = int(p.get("duration_seconds") or 0)
