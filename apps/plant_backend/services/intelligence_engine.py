from __future__ import annotations

from typing import List, Tuple, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func

from common_core.db import PlantSessionLocal
from apps.plant_backend.models import StopQueue, Ticket
from apps.hq_backend.intelligence import compute_insights_from_aggregates, Insight

def get_insights_for_plant(window_days: int = 14) -> List[Insight]:
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()
        start_dt = now - timedelta(days=window_days)
        
        # 1. Fetch Stops (Closed only for downtime calc, or all?)
        # Intelligence logic expects: (site_code, day_utc, reason_code, stops, downtime_minutes)
        # We aggregate from StopQueue
        stops = db.execute(
            select(StopQueue).where(StopQueue.opened_at_utc >= start_dt)
        ).scalars().all()
        
        # Aggregate in Python
        stop_rows = []
        # Key: (day, reason) -> {stops, duration}
        agg_stops = {}
        
        from common_core.config import settings
        site_code = settings.plant_site_code
        
        for s in stops:
            day = s.opened_at_utc.strftime("%Y-%m-%d")
            reason = s.reason or "Unknown"
            
            # Duration
            if s.closed_at_utc:
                dt_sec = (s.closed_at_utc - s.opened_at_utc).total_seconds()
            else:
                # If open, count duration until now
                dt_sec = (now - s.opened_at_utc).total_seconds()
            
            # Bucket
            k = (day, reason)
            if k not in agg_stops:
                agg_stops[k] = {"stops": 0, "duration": 0.0}
            agg_stops[k]["stops"] += 1
            agg_stops[k]["duration"] += dt_sec
            
        for (day, reason), v in agg_stops.items():
            dt_min = int(v["duration"] / 60)
            stop_rows.append((site_code, day, reason, v["stops"], dt_min))
            
        # 2. Fetch Tickets
        # Intelligence expects: (ticket_id, asset_id, status, priority, created_at_utc, sla_due_at_utc, acknowledged_at_utc, resolved_at_utc)
        tickets = db.execute(
            select(
                Ticket.id, Ticket.asset_id, Ticket.status, Ticket.priority,
                Ticket.created_at_utc, Ticket.sla_due_at_utc,
                Ticket.acknowledged_at_utc, Ticket.resolved_at_utc
            ).where(Ticket.created_at_utc >= start_dt)
        ).all()
        
        # 3. Rollups
        # Expected: (day_utc, site_code, downtime_minutes, stops, sla_breaches, tickets_open, faults)
        # We can construct strictly necessary fields or just fake it if insights don't use rollups heavily?
        # Actually `compute_insights_from_aggregates` checks `if not rollup_rows ... return empty`.
        # So we MUST provide at least dummy rollup rows to pass the check.
        # But wait, logic uses `rollup_rows` NOT for insights generation (except global ranking which is HQ only).
        # Let's check `intelligence.py` logic again.
        # Ah, logic primarily uses `stop_reason_rows` (Pattern 1, 2) and `ticket_rows` (Pattern 3, 4).
        # It does NOT seems to use `rollup_rows` for local insights?
        # Check source:
        # P1: Repeated stop -> uses stop_reason_rows
        # P2: Top downtime -> uses stop_reason_rows
        # P3: SLA trend -> uses ticket_rows
        # P4: Maint delay -> uses ticket_rows
        # So `rollup_rows` is effectively unused for local patterns!
        # But the guard clause `if not rollup_rows and not stop_reason_rows and not ticket_rows: return`
        # So passing empty rollup_rows is fine if we have others.
        
        rollup_rows = []
        
        # 4. Compute
        insights = compute_insights_from_aggregates(
            site_code=site_code,
            window_days=window_days,
            today_utc=now.strftime("%Y-%m-%d"),
            stop_reason_rows=stop_rows,
            rollup_rows=rollup_rows,
            ticket_rows=tickets
        )
        return insights
        
    finally:
        db.close()
