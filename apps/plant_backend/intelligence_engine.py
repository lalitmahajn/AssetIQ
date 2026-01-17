from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from apps.plant_backend.models import StopQueue, Ticket
from common_core.db import PlantSessionLocal

log = logging.getLogger("assetiq.plant_intelligence")


@dataclass(frozen=True)
class Insight:
    insight_type: str
    title: str
    severity: str
    detail: dict[str, Any]
    site_code: str | None = None


def _utc_day(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _parse_day(day_utc: str) -> datetime:
    return datetime.strptime(day_utc, "%Y-%m-%d")


def compute_insights_from_aggregates(
    *,
    site_code: str,
    window_days: int,
    today_utc: str,
    stop_reason_rows: list[tuple[str, str, str, int, int]],
    rollup_rows: list[tuple[str, str, int, int, int, int, int]],
    ticket_rows: list[
        tuple[str, str, str, str, datetime, datetime | None, datetime | None, datetime | None]
    ],
) -> list[Insight]:
    insights: list[Insight] = []

    if not rollup_rows and not stop_reason_rows and not ticket_rows:
        return insights

    # 1) Repeated stop patterns
    reason_by_code: dict[str, dict[str, Any]] = {}
    for _sc, day, reason, stops, dt_min in stop_reason_rows:
        r = reason_by_code.setdefault(reason, {"stops": 0, "downtime_minutes": 0, "days": set()})
        r["stops"] += int(stops or 0)
        r["downtime_minutes"] += int(dt_min or 0)
        r["days"].add(day)

    repeated = []
    for reason, agg in reason_by_code.items():
        if agg["stops"] >= 5 and len(agg["days"]) >= 3:
            repeated.append((reason, agg["stops"], agg["downtime_minutes"], len(agg["days"])))
    repeated.sort(key=lambda x: (x[2], x[1]), reverse=True)

    for reason, stops, dtm, days_n in repeated[:3]:
        insights.append(
            Insight(
                insight_type="REPEATED_STOP_PATTERN",
                title=f"Pattern Observed: '{reason}' repeating",
                severity="HIGH" if dtm >= 180 else ("MEDIUM" if dtm >= 60 else "LOW"),
                detail={
                    "window_days": window_days,
                    "reason_code": reason,
                    "total_stops": stops,
                    "downtime_minutes": dtm,
                    "days_affected": days_n,
                    "note": "Repeated patterns are based on historical stop entries only.",
                },
                site_code=site_code,
            )
        )

    # 2) Top downtime contributors
    top_loss = []
    for reason, agg in reason_by_code.items():
        top_loss.append((reason, agg["downtime_minutes"], agg["stops"]))
    top_loss.sort(key=lambda x: x[1], reverse=True)
    if top_loss:
        top3 = [
            {"reason_code": r, "downtime_minutes": int(dm), "stops": int(s)}
            for r, dm, s in top_loss[:5]
        ]
        insights.append(
            Insight(
                insight_type="TOP_DOWNTIME_CONTRIBUTORS",
                title="Insight: Top downtime contributors (by reason)",
                severity="MEDIUM",
                detail={
                    "window_days": window_days,
                    "top": top3,
                    "note": "Based on aggregated downtime minutes.",
                },
                site_code=site_code,
            )
        )

    # 3) SLA breach trend
    half = max(1, window_days // 2)
    today_dt = _parse_day(today_utc)
    cut_dt = today_dt - timedelta(days=half)
    prev_cut_dt = today_dt - timedelta(days=window_days)

    def is_breached(
        created: datetime, due: datetime | None, resolved: datetime | None, as_of: datetime
    ) -> bool:
        if due is None:
            return False
        if resolved is not None:
            return resolved > due
        return as_of > due

    cur_breaches = 0
    prev_breaches = 0
    for _tid, _aid, _st, _prio, created, due, _ack, resolved in ticket_rows:
        if created >= cut_dt and is_breached(created, due, resolved, today_dt):
            cur_breaches += 1
        elif created >= prev_cut_dt and is_breached(created, due, resolved, cut_dt):
            prev_breaches += 1

    if (cur_breaches + prev_breaches) > 0:
        direction = (
            "up"
            if cur_breaches > prev_breaches
            else ("down" if cur_breaches < prev_breaches else "flat")
        )
        insights.append(
            Insight(
                insight_type="SLA_BREACH_TREND",
                title=f"Insight: SLA breach trend is {direction}",
                severity="HIGH"
                if cur_breaches >= 5
                else ("MEDIUM" if cur_breaches >= 2 else "LOW"),
                detail={
                    "window_days": window_days,
                    "recent_days": half,
                    "recent_breaches": cur_breaches,
                    "previous_breaches": prev_breaches,
                    "direction": direction,
                    "note": "Trend compares recent window vs previous window.",
                },
                site_code=site_code,
            )
        )

    return insights


def get_insights_for_plant(window_days: int = 14) -> list[Insight]:
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()
        start_dt = now - timedelta(days=window_days)

        # 1. Fetch Stops
        stops = (
            db.execute(select(StopQueue).where(StopQueue.opened_at_utc >= start_dt)).scalars().all()
        )

        stop_rows = []
        agg_stops = {}
        from common_core.config import settings

        site_code = settings.plant_site_code

        for s in stops:
            day = _utc_day(s.opened_at_utc)
            reason = s.reason or "Unknown"
            if s.closed_at_utc:
                dt_sec = (s.closed_at_utc - s.opened_at_utc).total_seconds()
            else:
                dt_sec = (now - s.opened_at_utc).total_seconds()
            k = (day, reason)
            if k not in agg_stops:
                agg_stops[k] = {"stops": 0, "duration": 0.0}
            agg_stops[k]["stops"] += 1
            agg_stops[k]["duration"] += dt_sec

        for (day, reason), v in agg_stops.items():
            dt_min = int(v["duration"] / 60)
            stop_rows.append((site_code, day, reason, v["stops"], dt_min))

        # 2. Fetch Tickets
        tickets = db.execute(
            select(
                Ticket.id,
                Ticket.asset_id,
                Ticket.status,
                Ticket.priority,
                Ticket.created_at_utc,
                Ticket.sla_due_at_utc,
                Ticket.acknowledged_at_utc,
                Ticket.resolved_at_utc,
            ).where(Ticket.created_at_utc >= start_dt)
        ).all()

        # 3. Compute
        # Using empty rollup_rows is acceptable as verified in code logic
        insights = compute_insights_from_aggregates(
            site_code=site_code,
            window_days=window_days,
            today_utc=now.strftime("%Y-%m-%d"),
            stop_reason_rows=stop_rows,
            rollup_rows=[],
            ticket_rows=tickets,
        )
        return insights

    except Exception as e:
        log.error("intelligence_failed", extra={"err": str(e)})
        return []
    finally:
        db.close()
