from apps.hq_backend import models
from common_core.db import HQSessionLocal
from common_core.passwords import hash_pin
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("reset_hq_admin")

def reset_hq_admin():
    username = (os.environ.get("HQ_BOOTSTRAP_ADMIN_USERNAME") or "admin").strip()
    pin = (os.environ.get("HQ_BOOTSTRAP_ADMIN_PIN") or "121212").strip()

    db = HQSessionLocal()
    try:
        u = db.query(models.HQUser).filter(models.HQUser.username == username).first()
        if not u:
            log.info(f"HQ User {username} not found, creating...")
            u = models.HQUser(
                username=username, 
                pin_hash=hash_pin(pin), 
                roles="admin",
                created_at_utc=datetime.utcnow()
            )
            db.add(u)
        else:
            log.info(f"HQ User {username} found, resetting PIN...")
            u.pin_hash = hash_pin(pin)
        db.commit()
        log.info(f"Successfully set PIN for HQ user: {username}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_hq_admin()
