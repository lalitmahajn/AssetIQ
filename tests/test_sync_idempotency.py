import os, json, hmac, hashlib
from fastapi.testclient import TestClient
from apps.hq_backend.hq_backend.main import app

client = TestClient(app)

def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

def test_hq_receive_idempotent():
    secret = os.environ["SYNC_HMAC_SECRET"]
    payload = {"items":[{"site_code":"P01","entity_type":"rollup","entity_id":"x","payload":{"day_utc":"2026-01-08","asset_id":"A1","stops":1,"tickets_open":1,"faults":1},"correlation_id":"c1"}]}
    raw = json.dumps(payload,separators=(",",":")).encode("utf-8")
    sig = _sign(raw, secret)
    r1 = client.post("/sync/receive", data=raw, headers={"X-Signature":sig,"Content-Type":"application/json"})
    assert r1.status_code == 200
    r2 = client.post("/sync/receive", data=raw, headers={"X-Signature":sig,"Content-Type":"application/json"})
    assert r2.status_code == 200
    assert r2.json()["skipped"] >= 1
