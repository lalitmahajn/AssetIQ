from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import func, select

from apps.plant_backend.models import EventOutbox, Ticket, TimelineEvent
from common_core.config import settings
from common_core.db import PlantSessionLocal

log = logging.getLogger("assetiq.rollup_agent")


def _utc_now() -> datetime:
    return datetime.utcnow()


def _utc_today_str() -> str:
    return datetime.utcnow().date().isoformat()


def compute_rollup_once() -> bool:
    db = PlantSessionLocal()
    try:
        day_utc = _utc_today_str()

        # 1. Tickets Open (OPEN/ACK/ACKNOWLEDGED)
        tickets_open = (
            db.scalar(
                select(func.count(Ticket.id)).where(
                    Ticket.status.in_(["OPEN", "ACKNOWLEDGED", "ACK"])
                )
            )
            or 0
        )

        # 2. SLA Breaches (Current Snapshot)
        now = _utc_now()
        sla_breaches = (
            db.scalar(
                select(func.count(Ticket.id)).where(
                    Ticket.status.in_(["OPEN", "ACKNOWLEDGED", "ACK"]), Ticket.sla_due_at_utc < now
                )
            )
            or 0
        )

        # 3. Stops & Downtime (Today's accumulation)
        # TimelineEvent in Plant DB does not have raw_duration_seconds column (it is in payload or computed).
        # We must aggregate in Python or use payload extraction if DB supports it.
        # Postgres JSON query: payload_json->>'duration_seconds'
        # For simplicity/compatibility, let's fetch all stops today and sum in python.
        day_start = datetime.fromisoformat(day_utc)
        stops_rows = (
            db.execute(
                select(TimelineEvent).where(
                    TimelineEvent.event_type == "STOP", TimelineEvent.occurred_at_utc >= day_start
                )
            )
            .scalars()
            .all()
        )

        stops_count = len(stops_rows)
        downtime_sec = 0

        # Aggregate by reason
        reason_map = {}  # code -> {stops: 0, time_sec: 0}

        for s in stops_rows:
            # duration might be in payload
            d = s.payload_json.get("duration_seconds", 0)
            d_sec = int(d or 0)
            downtime_sec += d_sec

            # reason
            rc = s.payload_json.get("reason_code", "UNKNOWN")
            if not rc:
                rc = "UNKNOWN"

            if rc not in reason_map:
                reason_map[rc] = {"stops": 0, "time_sec": 0}
            reason_map[rc]["stops"] += 1
            reason_map[rc]["time_sec"] += d_sec

        downtime_minutes = int((downtime_sec + 59) / 60)

        stop_reasons_list = []
        for rc, stats in reason_map.items():
            stop_reasons_list.append(
                {
                    "reason_code": rc,
                    "stops": stats["stops"],
                    "downtime_minutes": int((stats["time_sec"] + 59) / 60),
                }
            )

        # 4. Faults (Today's accumulation)
        # Assuming event_type='PLC_FAULT' or similar.
        # Let's count 'PLC_FAULT' and 'FAULT' to be safe.
        faults_count = (
            db.scalar(
                select(func.count(TimelineEvent.id)).where(
                    TimelineEvent.event_type.in_(["PLC_FAULT", "FAULT"]),
                    TimelineEvent.occurred_at_utc >= day_start,
                )
            )
            or 0
        )

        # 5. Construct Payload
        payload = {
            "day_utc": day_utc,
            "tickets_open": tickets_open,
            "sla_breaches": sla_breaches,
            "stops": stops_count,
            "downtime_minutes": downtime_minutes,
            "faults": faults_count,
            "stop_reasons": stop_reasons_list,
        }

        # 5. Outbox Logic
        site_code = settings.plant_site_code
        # correlation_id = f"rollup:{site_code}:{day_utc}" - Superseded by unique_correlation_id below

        # Check if we should suppress update?
        # For simplicity, we just push a new event. The Sync Agent handles duplicates if correlation_id matches?
        # Actually sync agent uses correlation_id for idempotency on HQ side too.
        # But wait, if HQ side sees same correlation_id, it might SKIP it.
        # HQ receiver: if db.get(AppliedCorrelation, item.correlation_id) is not None: skipped += 1

        # CRITICAL: If we use the SAME correlation_id, HQ will ignore subsequent updates for the day!
        # We need a unique correlation ID for *this specific update* of the day's rollup.
        # So we append timestamp/random to correlation_id, OR the HQ receiver logic for rollups allows re-application.

        # Checking HQ receiver:
        # if db.get(AppliedCorrelation, item.correlation_id) is not None: skipped
        # This means HQ enforces EXACTLY ONE processing per correlation_id.

        # So for partial updates throughout the day, we MUST generate a NEW correlation_id each time.
        # e.g. rollup:P01:2026-01-09:1000
        # However, RollupDaily table constraint is (site_code, day_utc).
        # _apply_rollup does an UPSERT logic (check existing, then update).

        # So we should suffix correlation_id with timestamp.
        timestamp_suffix = int(datetime.utcnow().timestamp())
        unique_correlation_id = f"rollup:{site_code}:{day_utc}:{timestamp_suffix}"

        # Add to outbox
        new_event = EventOutbox(
            site_code=site_code,
            entity_type="rollup",
            entity_id=day_utc,
            payload_json=payload,
            correlation_id=unique_correlation_id,
            created_at_utc=_utc_now(),
        )
        db.add(new_event)

        db.commit()
        return True
    except Exception as e:
        log.error("rollup_compute_failed", extra={"err": str(e)})
        return False
    finally:
        db.close()
