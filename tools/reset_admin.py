from apps.plant_backend import models
from common_core.db import PlantSessionLocal
from common_core.passwords import hash_pin
import os
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("reset_admin")

def reset_admin():
    email = (os.environ.get("BOOTSTRAP_ADMIN_EMAIL") or "admin").strip().lower()
    pin = (os.environ.get("BOOTSTRAP_ADMIN_PIN") or "121212").strip()

    db = PlantSessionLocal()
    try:
        u = db.query(models.User).filter(models.User.id == email).first()
        if not u:
            log.info(f"User {email} not found, creating...")
            u = models.User(id=email, pin_hash=hash_pin(pin), roles="admin,supervisor,maintenance")
            db.add(u)
        else:
            log.info(f"User {email} found, resetting PIN...")
            u.pin_hash = hash_pin(pin)
        db.commit()
        log.info(f"Successfully set PIN for user: {email}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin()
