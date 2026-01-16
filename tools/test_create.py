from apps.hq_backend.routers.auth import create_user, CreateUserIn
from common_core.db import HQSessionLocal
from apps.hq_backend.models import HQUser
from common_core.passwords import verify_pin
import sys

# Mock Depends
class MockAdmin:
    pass

def test_flow():
    # 1. Create User
    body = CreateUserIn(username="ui_test", pin="123456", roles="user")
    print("Attempting to create user 'ui_test' with pin '123456'...")
    try:
        create_user(body, admin={"sub": "admin", "roles": ["admin"]})
        print("Creation function returned successfully.")
    except Exception as e:
        print(f"Creation failed: {e}")
        return

    # 2. Verify in DB
    db = HQSessionLocal()
    u = db.get(HQUser, "ui_test")
    if not u:
        print("User not found in DB!")
    else:
        print(f"User found. Hash: {u.pin_hash}")
        if verify_pin("123456", u.pin_hash):
            print("VERIFICATION SUCCESS: PIN matches.")
        else:
            print("VERIFICATION FAILED: PIN does not match.")
    db.close()

if __name__ == "__main__":
    test_flow()
