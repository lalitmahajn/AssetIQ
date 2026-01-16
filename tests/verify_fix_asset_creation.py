import os
import sys
from fastapi.testclient import TestClient

# Add root to sys.path
sys.path.append(os.getcwd())

from apps.plant_backend.main import app

client = TestClient(app)

def _bootstrap():
    # Use a mock bootstrap or similar if needed. 
    # Based on test_stop_ticket_sla_chain.py, they use /bootstrap/create-admin
    os.environ["BOOTSTRAP_TOKEN"] = "boot"
    client.post("/bootstrap/create-admin", headers={"X-Bootstrap-Token":"boot"}, json={"username":"admin","pin":"12121212","roles":"admin,maintenance"})
    r = client.post("/auth/login", json={"username":"admin","pin":"12121212"})
    return r.json().get("token")

def test_asset_creation_fix():
    token = _bootstrap()
    if not token:
        print("Failed to get auth token")
        return
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test Payload matching UI form
    payload = {
        "id": "AST-FIX-001",
        "name": "Fixed Asset",
        "asset_type": "MACHINE",
        "description": "Verifying the fix"
    }
    
    print(f"Testing /master/assets/create with: {payload}")
    r = client.post("/master/assets/create", headers=headers, json=payload)
    
    print(f"Response Status: {r.status_code}")
    print(f"Response Body: {r.text}")
    
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["id"] == "AST-FIX-001"
    
    # Verify it can be listed
    r_list = client.get("/master/assets/list", headers=headers)
    assert r_list.status_code == 200
    assets = r_list.json()
    assert any(a["id"] == "AST-FIX-001" for a in assets)
    
    print("Verification Successful!")

if __name__ == "__main__":
    try:
        test_asset_creation_fix()
    except Exception as e:
        print(f"Verification Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
