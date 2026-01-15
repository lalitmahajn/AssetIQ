import os
from fastapi.testclient import TestClient
from apps.plant_backend.plant_backend.main import app

client = TestClient(app)

def test_health_ready_endpoints():
    r = client.get("/healthz")
    assert r.status_code == 200
    r2 = client.get("/readyz")
    assert r2.status_code == 200
