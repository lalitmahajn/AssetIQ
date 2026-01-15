from __future__ import annotations

import os
from fastapi.testclient import TestClient
from apps.plant_backend.plant_backend.main import app

client = TestClient(app)

def test_login_with_bootstrap_admin():
    os.environ["BOOTSTRAP_TOKEN"] = "boot"
    # create-admin endpoint creates the first admin in test DB
    r0 = client.post(
        "/bootstrap/create-admin",
        headers={"X-Bootstrap-Token": "boot"},
        json={"username":"admin@test.local","pin":"12345678","roles":"admin"},
    )
    assert r0.status_code in (200, 409)  # ok or already exists

    r = client.post("/auth/login", json={"username":"admin@test.local","pin":"12345678"})
    assert r.status_code == 200
    assert "token" in r.json()
