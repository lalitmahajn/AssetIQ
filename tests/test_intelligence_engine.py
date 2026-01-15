from datetime import datetime, timedelta

from apps.hq_backend.hq_backend.intelligence import compute_insights_from_aggregates


def test_insights_not_enough_data():
    out = compute_insights_from_aggregates(
        site_code="PLANT1",
        window_days=14,
        today_utc="2026-01-08",
        stop_reason_rows=[],
        rollup_rows=[],
        ticket_rows=[],
    )
    assert out == []


def test_repeated_stop_pattern_and_top_downtime():
    stop_reason_rows = [
        ("PLANT1", "2026-01-02", "MECH_JAM", 2, 30),
        ("PLANT1", "2026-01-03", "MECH_JAM", 1, 25),
        ("PLANT1", "2026-01-04", "MECH_JAM", 2, 70),
        ("PLANT1", "2026-01-05", "POWER", 1, 10),
    ]
    rollup_rows = [("2026-01-02", "PLANT1", 40, 3, 0, 1, 0)]
    ticket_rows = []

    out = compute_insights_from_aggregates(
        site_code="PLANT1",
        window_days=7,
        today_utc="2026-01-08",
        stop_reason_rows=stop_reason_rows,
        rollup_rows=rollup_rows,
        ticket_rows=ticket_rows,
    )
    types = {x.insight_type for x in out}
    assert "REPEATED_STOP_PATTERN" in types
    assert "TOP_DOWNTIME_CONTRIBUTORS" in types


def test_sla_trend_and_maint_delay():
    now = datetime(2026, 1, 8)
    ticket_rows = [
        ("T1", "A1", "OPEN", "P1", now - timedelta(days=1), now - timedelta(hours=1), None, None),
        ("T2", "A1", "RESOLVED", "P2", now - timedelta(days=2), now - timedelta(days=1), now - timedelta(days=2) + timedelta(hours=1), now - timedelta(hours=12)),
        ("T3", "A2", "RESOLVED", "P2", now - timedelta(days=9), now - timedelta(days=8), now - timedelta(days=9) + timedelta(hours=1), now - timedelta(days=7, hours=20)),
    ]
    out = compute_insights_from_aggregates(
        site_code="PLANT1",
        window_days=14,
        today_utc="2026-01-08",
        stop_reason_rows=[],
        rollup_rows=[("2026-01-07", "PLANT1", 10, 1, 1, 2, 0)],
        ticket_rows=ticket_rows,
    )
    types = {x.insight_type for x in out}
    assert "SLA_BREACH_TREND" in types
    assert "MAINTENANCE_DELAY_PATTERN" in types
