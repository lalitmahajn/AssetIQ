from __future__ import annotations
import sys
import logging
import json
from datetime import datetime
from sqlalchemy import select, func
from common_core.db import PlantSessionLocal
from apps.plant_backend.models import Ticket, TimelineEvent, EventOutbox
from common_core.config import settings

# Setup logging to console
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("backfill")

def backfill(target_date: str):
    """
    Force compute rollup for a specific YYYY-MM-DD date.
    Copied logic from rollup_agent.py but with parameterized date.
    """
    log.info(f"Starting backfill for {target_date}...")
    db = PlantSessionLocal()
    try:
        day_utc = target_date
        
        # 1. Tickets Open (OPEN/ACK/ACKNOWLEDGED) - Snapshot is always "now", but for backfill we might just take current state
        # Actually rollup agent snapshot "tickets_open" is "current state". For past days this is inaccurate but acceptable for this fix.
        tickets_open = db.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.status.in_(["OPEN", "ACKNOWLEDGED", "ACK"])
            )
        ) or 0

        # 2. SLA Breaches - also snapshot "now"
        now = datetime.utcnow()
        sla_breaches = db.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.status.in_(["OPEN", "ACKNOWLEDGED", "ACK"]),
                Ticket.sla_due_at_utc < now
            )
        ) or 0
        
        # 3. Stops & Downtime (Filter by the specific day)
        day_start = datetime.fromisoformat(day_utc)
        # End of day is next day
        # Actually logic in rollup_agent was `occurred_at_utc >= day_start`. 
        # Ideally it should be `day_start <= occurred < day_end`.
        # But let's stick to existing logic: >= day_start (starts at 00:00:00)
        # Wait, if we run this for Jan 13, and today is Jan 14, `occurred_at_utc >= Jan 13` includes Jan 14 events too!
        # The original rollup_agent is flawed if it treats "Today" as >= StartOfDay without an upper bound, but since it runs "Today", that's fine.
        # For backfill of Jan 13, we really want Jan 13 only.
        
        # Let's define a rough upper bound (next day)
        from datetime import timedelta
        day_end = day_start + timedelta(days=1)
        
        stops_rows = db.execute(
            select(TimelineEvent).where(
                TimelineEvent.event_type == "STOP",
                TimelineEvent.occurred_at_utc >= day_start,
                TimelineEvent.occurred_at_utc < day_end
            )
        ).scalars().all()
        
        stops_count = len(stops_rows)
        downtime_sec = 0
        
        # Aggregate by reason
        reason_map = {} # code -> {stops: 0, time_sec: 0}

        for s in stops_rows:
            d = s.payload_json.get("duration_seconds", 0)
            d_sec = int(d or 0)
            downtime_sec += d_sec
            
            rc = s.payload_json.get("reason_code", "UNKNOWN")
            if not rc: rc = "UNKNOWN"
            
            if rc not in reason_map:
                reason_map[rc] = {"stops": 0, "time_sec": 0}
            reason_map[rc]["stops"] += 1
            reason_map[rc]["time_sec"] += d_sec
            
        downtime_minutes = int((downtime_sec + 59) / 60)
        
        stop_reasons_list = []
        for rc, stats in reason_map.items():
            stop_reasons_list.append({
                "reason_code": rc,
                "stops": stats["stops"],
                "downtime_minutes": int((stats["time_sec"] + 59) / 60)
            })

        # 4. Faults
        faults_count = db.scalar(
            select(func.count(TimelineEvent.id)).where(
                TimelineEvent.event_type.in_(["PLC_FAULT", "FAULT"]),
                TimelineEvent.occurred_at_utc >= day_start,
                TimelineEvent.occurred_at_utc < day_end
            )
        ) or 0

        # 5. Construct Payload
        payload = {
            "day_utc": day_utc,
            "tickets_open": tickets_open,
            "sla_breaches": sla_breaches,
            "stops": stops_count,
            "downtime_minutes": downtime_minutes,
            "faults": faults_count,
            "stop_reasons": stop_reasons_list
        }
        
        log.info(f"Computed payload: {json.dumps(payload, indent=2)}")

        # 6. Outbox Logic
        site_code = settings.plant_site_code
        # Unique correlation ID to force processing
        timestamp_suffix = int(datetime.utcnow().timestamp())
        unique_correlation_id = f"rollup:{site_code}:{day_utc}:backfill:{timestamp_suffix}"

        new_event = EventOutbox(
            site_code=site_code,
            entity_type="rollup",
            entity_id=day_utc,
            payload_json=payload,
            correlation_id=unique_correlation_id,
            created_at_utc=datetime.utcnow()
        )
        db.add(new_event)
        db.commit()
        log.info(f"Successfully pushed backfill event to Outbox with CID: {unique_correlation_id}")
        return True
    except Exception as e:
        log.error(f"Backfill failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backfill_rollup.py YYYY-MM-DD")
        sys.exit(1)
    backfill(sys.argv[1])
