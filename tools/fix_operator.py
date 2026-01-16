from apps.hq_backend.models import HQUser
from common_core.db import HQSessionLocal
from common_core.passwords import hash_pin
from datetime import datetime
import sys

def fix_operator():
    db = HQSessionLocal()
    try:
        # Delete existing operator if any to ensure clean slate
        u = db.get(HQUser, "operator")
        if u:
            print(f"Deleting existing operator user found with roles: {u.roles}")
            db.delete(u)
            db.commit()
        
        # Create fresh operator
        print("Creating new 'operator' user...")
        new_user = HQUser(
            username="operator",
            pin_hash=hash_pin("123456"),
            roles="user",
            created_at_utc=datetime.utcnow()
        )
        db.add(new_user)
        db.commit()
        print("SUCCESS: User 'operator' created with PIN '123456'")
        
        # Verify immediately
        v = db.get(HQUser, "operator")
        if v:
            print(f"VERIFICATION: User '{v.username}' exists in DB.")
        else:
            print("VERIFICATION FAILED: User not found after commit!")
            
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_operator()
