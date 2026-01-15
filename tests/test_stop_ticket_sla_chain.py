import os
from fastapi.testclient import TestClient
from apps.plant_backend.plant_backend.main import app

client = TestClient(app)

def _bootstrap():
    os.environ["BOOTSTRAP_TOKEN"] = "boot"
    client.post("/bootstrap/create-admin", headers={"X-Bootstrap-Token":"boot"}, json={"username":"admin","pin":"12345678","roles":"admin,maintenance"})
    r = client.post("/auth/login", json={"username":"admin","pin":"12345678"})
    return r.json()["token"]

def test_stop_to_ticket_chain():
    token = _bootstrap()
    r = client.post("/stops/manual-open", headers={"Authorization":f"Bearer {token}"}, json={"asset_id":"A1","reason":"manual stop"})
    assert r.status_code == 200
    data = r.json()
    assert data["ticket_id"].startswith("TCK_")
    r2 = client.post(f"/tickets/{data['ticket_id']}/ack", headers={"Authorization":f"Bearer {token}"})
    assert r2.status_code == 200
    r3 = client.post(f"/stops/{data['stop_id']}/resolve", headers={"Authorization":f"Bearer {token}"}, json={"resolution_text":"fixed"})
    assert r3.status_code == 200
