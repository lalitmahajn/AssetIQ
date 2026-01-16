from __future__ import annotations

import argparse
from datetime import datetime
from common_core.db import HQSessionLocal
from common_core.passwords import hash_pin
from apps.hq_backend.models import HQUser

def main():
    parser = argparse.ArgumentParser(description="Create a new HQ user.")
    parser.add_argument("--username", required=True, help="Username for the new user")
    parser.add_argument("--pin", required=True, help="PIN for the new user (min 6 chars)")
    parser.add_argument("--roles", default="admin", help="Comma-separated roles (default: admin)")
    
    args = parser.parse_args()
    
    db = HQSessionLocal()
    try:
        # Check if user already exists
        existing = db.get(HQUser, args.username)
        if existing:
            print(f"Error: User '{args.username}' already exists.")
            return

        user = HQUser(
            username=args.username,
            pin_hash=hash_pin(args.pin),
            roles=args.roles,
            created_at_utc=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        print(f"User '{args.username}' created successfully.")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
