from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select

from common_core.db import HQSessionLocal

from .models import InsightDaily, RollupDaily, StopReasonDaily, TicketSnapshot


@dataclass(frozen=True)
class Insight:
    insight_type: str
    title: str
    severity: str  # LOW/MEDIUM/HIGH
    detail: dict[str, Any]
    site_code: str | None = None


def _utc_day(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _parse_day(day_utc: str) -> datetime:
    return datetime.strptime(day_utc, "%Y-%m-%d")


def _is_weak_pin(pin: str) -> bool:
    weak = {"0000", "1111", "1234", "2222", "3333", "4444", "5555", "6666", "7777", "8888", "9999"}
    return pin in weak


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
    """
    Pure function: compute deterministic, explainable insights from pre-aggregated rows.

    stop_reason_rows tuples:
      (site_code, day_utc, reason_code, stops, downtime_minutes)

    rollup_rows tuples:
      (day_utc, site_code, downtime_minutes, stops, sla_breaches, tickets_open, faults)

    ticket_rows tuples:
      (ticket_id, asset_id, status, priority, created_at_utc, sla_due_at_utc, acknowledged_at_utc, resolved_at_utc)
    """
    insights: list[Insight] = []

    # If insufficient data in window, return empty (UI will show "Not enough data yet")
    if not rollup_rows and not stop_reason_rows and not ticket_rows:
        return insights

    # 1) Repeated stop patterns (7-day window within configured window)
    # Rule: show top reasons with stops >= 5 AND present on >= 3 distinct days.
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

    # 2) Top downtime contributors (reasons)
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

    # 3) SLA breach trend (compare last half vs prior half)
    # Deterministic rule: compute SLA breaches in last N/2 days vs previous N/2 days.
    half = max(1, window_days // 2)
    today_dt = _parse_day(today_utc)
    cut_dt = today_dt - timedelta(days=half)
    prev_cut_dt = today_dt - timedelta(days=window_days)

    def is_breached(
        created: datetime, due: datetime | None, resolved: datetime | None, as_of: datetime
    ) -> bool:
        if due is None:
            return False
        # breached if resolved after due OR still unresolved after due (as_of)
        if resolved is not None:
            return resolved > due
        return as_of > due

    cur_breaches = 0
    prev_breaches = 0
    for _tid, _aid, _st, _prio, created, due, _ack, resolved in ticket_rows:
        if created >= cut_dt:
            if is_breached(created, due, resolved, today_dt):
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
                    "note": "Trend compares recent window vs previous window. No prediction.",
                },
                site_code=site_code,
            )
        )

    # 4) Maintenance delay patterns (ack delays)
    ack_delays_min: list[int] = []
    unresolved = 0
    unacked = 0
    for _tid, _aid, status, _prio, created, _due, ack, resolved in ticket_rows:
        if status in ("OPEN", "ACK", "ACKNOWLEDGED") and resolved is None:
            unresolved += 1
        if ack is None:
            unacked += 1
        else:
            delta = ack - created
            ack_delays_min.append(max(0, int(delta.total_seconds() // 60)))

    if ticket_rows:
        ack_delays_min.sort()
        median = ack_delays_min[len(ack_delays_min) // 2] if ack_delays_min else None

        # deterministic thresholds
        # MEDIUM: median ack delay > 30 min; HIGH: > 120 min or many unacked
        sev = "LOW"
        if (median is not None and median > 120) or (unacked >= 5):
            sev = "HIGH"
        elif (median is not None and median > 30) or (unacked >= 2):
            sev = "MEDIUM"

        insights.append(
            Insight(
                insight_type="MAINTENANCE_DELAY_PATTERN",
                title="Pattern Observed: Maintenance response delay",
                severity=sev,
                detail={
                    "window_days": window_days,
                    "median_ack_delay_minutes": median,
                    "tickets_unacknowledged": unacked,
                    "tickets_unresolved": unresolved,
                    "note": "Delay is based on ticket acknowledge timestamps only.",
                },
                site_code=site_code,
            )
        )

    return insights


def recompute_and_store_daily_insights(day_utc: str, window_days: int = 14) -> int:
    """Compute insights for all plants and store as daily snapshots for UI/reports."""
    db = HQSessionLocal()
    created = 0
    try:
        # gather distinct plants from rollups
        sites = [r[0] for r in db.execute(select(RollupDaily.site_code).distinct()).all()]
        if not sites:
            return 0

        today_dt = _parse_day(day_utc)
        start_dt = today_dt - timedelta(days=window_days - 1)
        start_day = _utc_day(start_dt)

        # delete existing insights for that day (deterministic refresh)
        db.execute(InsightDaily.__table__.delete().where(InsightDaily.day_utc == day_utc))
        db.commit()

        for site in sites:
            # stop reasons
            sr_rows = db.execute(
                select(
                    StopReasonDaily.site_code,
                    StopReasonDaily.day_utc,
                    StopReasonDaily.reason_code,
                    StopReasonDaily.stops,
                    StopReasonDaily.downtime_minutes,
                ).where(
                    and_(
                        StopReasonDaily.site_code == site,
                        StopReasonDaily.day_utc >= start_day,
                        StopReasonDaily.day_utc <= day_utc,
                    )
                )
            ).all()

            # rollups
            ru_rows = db.execute(
                select(
                    RollupDaily.day_utc,
                    RollupDaily.site_code,
                    RollupDaily.downtime_minutes,
                    RollupDaily.stops,
                    RollupDaily.sla_breaches,
                    RollupDaily.tickets_open,
                    RollupDaily.faults,
                ).where(
                    and_(
                        RollupDaily.site_code == site,
                        RollupDaily.day_utc >= start_day,
                        RollupDaily.day_utc <= day_utc,
                    )
                )
            ).all()

            # tickets
            tk_rows = db.execute(
                select(
                    TicketSnapshot.ticket_id,
                    TicketSnapshot.asset_id,
                    TicketSnapshot.status,
                    TicketSnapshot.priority,
                    TicketSnapshot.created_at_utc,
                    TicketSnapshot.sla_due_at_utc,
                    TicketSnapshot.acknowledged_at_utc,
                    TicketSnapshot.resolved_at_utc,
                ).where(
                    and_(
                        TicketSnapshot.site_code == site, TicketSnapshot.created_at_utc >= start_dt
                    )
                )
            ).all()

            insights = compute_insights_from_aggregates(
                site_code=site,
                window_days=window_days,
                today_utc=day_utc,
                stop_reason_rows=sr_rows,
                rollup_rows=ru_rows,
                ticket_rows=tk_rows,
            )
            for ins in insights:
                db.add(
                    InsightDaily(
                        day_utc=day_utc,
                        site_code=ins.site_code,
                        insight_type=ins.insight_type,
                        title=ins.title,
                        severity=ins.severity,
                        detail_json=ins.detail,
                        created_at_utc=datetime.utcnow(),
                    )
                )
                created += 1

        # global insights: SLA ranking and downtime ranking (top 5)
        # downtime in window
        agg = db.execute(
            select(
                RollupDaily.site_code,
                func.sum(RollupDaily.downtime_minutes),
                func.sum(RollupDaily.sla_breaches),
            )
            .where(and_(RollupDaily.day_utc >= start_day, RollupDaily.day_utc <= day_utc))
            .group_by(RollupDaily.site_code)
        ).all()
        if agg:
            dt_rank = sorted(
                [(a[0], int(a[1] or 0)) for a in agg], key=lambda x: x[1], reverse=True
            )[:5]
            sla_rank = sorted(
                [(a[0], int(a[2] or 0)) for a in agg], key=lambda x: x[1], reverse=True
            )[:5]
            db.add(
                InsightDaily(
                    day_utc=day_utc,
                    site_code=None,
                    insight_type="GLOBAL_DOWNTIME_RANKING",
                    title="Insight: Downtime ranking (top plants)",
                    severity="MEDIUM",
                    detail_json={
                        "window_days": window_days,
                        "top": [{"site_code": s, "downtime_minutes": m} for s, m in dt_rank],
                    },
                    created_at_utc=datetime.utcnow(),
                )
            )
            db.add(
                InsightDaily(
                    day_utc=day_utc,
                    site_code=None,
                    insight_type="GLOBAL_SLA_BREACH_RANKING",
                    title="Insight: SLA breach ranking (top plants)",
                    severity="MEDIUM",
                    detail_json={
                        "window_days": window_days,
                        "top": [{"site_code": s, "sla_breaches": b} for s, b in sla_rank],
                    },
                    created_at_utc=datetime.utcnow(),
                )
            )
            created += 2

        db.commit()
        return created
    finally:
        db.close()
