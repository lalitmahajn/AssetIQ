from __future__ import annotations
from fastapi.testclient import TestClient
from apps.plant_backend.plant_backend.main import app

client = TestClient(app)

def test_health_ready():
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json().get("ok") is True
