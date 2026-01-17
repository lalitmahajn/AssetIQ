from __future__ import annotations

import logging
import os
from datetime import datetime

from fastapi import FastAPI

from apps.hq_backend.models import Base, HQUser
from apps.hq_backend.routers.auth import router as auth_router
from apps.hq_backend.routers.dashboard import router as dashboard_router
from apps.hq_backend.routers.health import router as health_router
from apps.hq_backend.routers.metrics import router as metrics_router
from apps.hq_backend.routers.receiver import router as receiver_router
from apps.hq_backend.routers.reports import router as reports_router
from common_core.config import settings
from common_core.db import HQSessionLocal, hq_engine
from common_core.guardrails import validate_runtime_secrets
from common_core.logging_setup import configure_logging
from common_core.passwords import hash_pin
from common_core.request_id import RequestIdMiddleware

log = logging.getLogger("assetiq.hq")

app = FastAPI(title="AssetIQ HQ Backend")
app.add_middleware(RequestIdMiddleware)

app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(receiver_router)
app.include_router(dashboard_router)
app.include_router(reports_router)
app.include_router(auth_router)


def bootstrap_admin():
    """Create initial HQ admin if table is empty"""
    username = os.environ.get("HQ_BOOTSTRAP_ADMIN_USERNAME")
    pin = os.environ.get("HQ_BOOTSTRAP_ADMIN_PIN")
    if not username or not pin:
        return

    db = HQSessionLocal()
    try:
        # Check if table has any users
        count = db.query(HQUser).count()
        if count == 0:
            log.info("bootstrapping_hq_admin", extra={"username": username})
            admin = HQUser(
                username=username,
                pin_hash=hash_pin(pin),
                roles="admin",
                created_at_utc=datetime.utcnow(),
            )
            db.add(admin)
            db.commit()
    except Exception as e:
        log.error("bootstrap_failed", extra={"error": str(e)})
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def startup() -> None:
    configure_logging(component="hq_backend")
    # ensure table exists (simple case, alembic is preferred for prod)
    Base.metadata.create_all(hq_engine, tables=[HQUser.__table__])
    bootstrap_admin()
    validate_runtime_secrets()
    log.info("hq_started", extra={"hq_receiver": settings.hq_receiver_url})
