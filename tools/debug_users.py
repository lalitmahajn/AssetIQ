from apps.hq_backend.models import HQUser
from common_core.db import HQSessionLocal
from common_core.passwords import verify_pin
import sys

def check_users():
    db = HQSessionLocal()
    try:
        users = db.query(HQUser).all()
        print(f"Found {len(users)} users.")
        for u in users:
            is_valid_123456 = verify_pin("123456", u.pin_hash)
            print(f"User: '{u.username}', Roles: {u.roles}, HashPrefix: {u.pin_hash[:10]}..., Verify(123456): {is_valid_123456}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()
