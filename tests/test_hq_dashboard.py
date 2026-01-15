from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.hq_backend.hq_backend.main import app
from common_core.db import HQSessionLocal
from apps.hq_backend.hq_backend.models import PlantRegistry, RollupDaily


def test_hq_health_and_ui():
    c = TestClient(app)
    assert c.get("/healthz").status_code == 200
    assert c.get("/readyz").status_code == 200
    r = c.get("/hq/ui")
    assert r.status_code == 200
    assert "AssetIQ HQ Dashboard" in r.text


def test_hq_summary_returns_data():
    db = HQSessionLocal()
    now = datetime.utcnow()
    try:
        if db.get(PlantRegistry, "PLANT_A") is None:
            db.add(
                PlantRegistry(
                    site_code="PLANT_A",
                    display_name="Plant A",
                    is_active=True,
                    last_seen_at_utc=now,
                    created_at_utc=now,
                    updated_at_utc=now,
                )
            )
        day = now.date().isoformat()
        existing = db.execute(select(RollupDaily).where(RollupDaily.site_code == "PLANT_A", RollupDaily.day_utc == day)).scalar_one_or_none()
        if existing is None:
            db.add(
                RollupDaily(
                    site_code="PLANT_A",
                    day_utc=day,
                    stops=2,
                    faults=1,
                    tickets_open=1,
                    sla_breaches=0,
                    downtime_minutes=25,
                    updated_at_utc=now,
                )
            )
        db.commit()
    finally:
        db.close()

    c = TestClient(app)
    resp = c.get("/hq/summary", params={"day_utc": day})
    assert resp.status_code == 200
    data = resp.json()
    assert data["day_utc"] == day
    assert any(x["site_code"] == "PLANT_A" for x in data["items"])
