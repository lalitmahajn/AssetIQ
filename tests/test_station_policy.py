from __future__ import annotations
from fastapi.testclient import TestClient
from apps.plant_backend.plant_backend.main import app

client = TestClient(app)

def test_station_mode_blocks_login():
    r = client.post("/auth/login", headers={"X-Station-Mode":"1"}, json={"username":"admin","pin":"1234"})
    assert r.status_code == 403

def test_station_mode_allows_ingest():
    r = client.post("/ingest/event", headers={"X-Station-Mode":"1"}, json={
        "event_type":"PLC_FAULT",
        "asset_id":"M1",
        "reason":"x",
        "occurred_at_utc":"2026-01-08T00:00:00Z",
        "source_id":"plc",
        "event_id":"e1"
    })
    assert r.status_code == 200
