from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from apps.plant_backend import (
    models,  # noqa: F401
    plc_service,
)
from apps.plant_backend.middleware_station import StationPolicyMiddleware
from apps.plant_backend.routers import (
    assets,
    efficiency,
    hq_proxy,
    insights_mock,
    masters_dynamic,
    realtime,
    reports,
    suggestions,
    ui_assets,
    ui_tickets,
)
from apps.plant_backend.routers.auth import router as auth_router
from apps.plant_backend.routers.backup import router as backup_router
from apps.plant_backend.routers.bootstrap import router as bootstrap_router
from apps.plant_backend.routers.health import router as health_router
from apps.plant_backend.routers.ingest import router as ingest_router
from apps.plant_backend.routers.master import router as master_router
from apps.plant_backend.routers.metrics import router as metrics_router
from apps.plant_backend.routers.plc import router as plc_router
from apps.plant_backend.routers.stations import router as stations_router
from apps.plant_backend.routers.stops import router as stops_router
from apps.plant_backend.routers.tickets import router as tickets_router
from apps.plant_backend.routers.ui_stop_queue import router as stop_queue_router
from common_core.config import settings
from common_core.db import PlantSessionLocal
from common_core.guardrails import validate_runtime_secrets
from common_core.logging_setup import configure_logging
from common_core.passwords import hash_pin
from common_core.request_id import RequestIdMiddleware

log = logging.getLogger("assetiq.plant")

app = FastAPI(title="AssetIQ Plant Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(StationPolicyMiddleware)

app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(auth_router)
app.include_router(bootstrap_router)
app.include_router(stations_router)
app.include_router(stops_router)
app.include_router(tickets_router)
app.include_router(ingest_router)
app.include_router(stop_queue_router)
app.include_router(plc_router)
app.include_router(insights_mock.router)
app.include_router(ui_tickets.router)
app.include_router(ui_assets.router)
app.include_router(realtime.router)
app.include_router(reports.router)
app.include_router(master_router)
app.include_router(hq_proxy.router)
app.include_router(assets.router)
app.include_router(masters_dynamic.router)
app.include_router(suggestions.router)
app.include_router(efficiency.router)
app.include_router(backup_router)


def _is_weak_pin(pin: str) -> bool:
    weak = {
        "0000",
        "1111",
        "2222",
        "3333",
        "4444",
        "5555",
        "6666",
        "7777",
        "8888",
        "9999",
        "1234",
        "12345",
        "123456",
        "000000",
        "111111",
    }
    return (not pin) or (pin.strip() in weak) or (len(pin) < 6)


def _bootstrap_admin_if_env_present() -> None:
    email = (os.environ.get("BOOTSTRAP_ADMIN_EMAIL") or "").strip().lower()
    pin = (os.environ.get("BOOTSTRAP_ADMIN_PIN") or "").strip()

    if not email and not pin:
        return
    if not email or not pin:
        raise RuntimeError("BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PIN must both be set")
    if _is_weak_pin(pin):
        raise RuntimeError(
            "BOOTSTRAP_ADMIN_PIN is too weak (min 6, block common pins like 1234/0000)"
        )
    if len(email) < 3:
        raise RuntimeError("BOOTSTRAP_ADMIN_EMAIL must be at least 3 characters")

    db = PlantSessionLocal()
    try:
        # If any user exists, do nothing (bootstrap only once).
        any_user = db.execute(models.User.__table__.select().limit(1)).first()
        if any_user:
            return
        db.add(models.User(id=email, pin_hash=hash_pin(pin), roles="admin,supervisor,maintenance"))
        db.commit()
        log.warning("bootstrap_admin_created", extra={"admin": email})
    finally:
        db.close()


def _bootstrap_masters() -> None:
    db = PlantSessionLocal()
    try:
        from datetime import datetime

        from sqlalchemy import select

        from apps.plant_backend.models import MasterType

        existing = db.execute(
            select(MasterType).where(MasterType.type_code == "STOP_REASON")
        ).scalar_one_or_none()
        if not existing:
            db.add(
                MasterType(
                    site_code=settings.plant_site_code,
                    type_code="STOP_REASON",
                    name="Stop Reasons",
                    description="Master list of downtime reasons",
                    is_active=True,
                    created_at_utc=datetime.utcnow(),
                )
            )
            db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup() -> None:
    configure_logging(component="plant_backend")
    validate_runtime_secrets()

    # NOTE: We no longer call Base.metadata.create_all(bind=plant_engine) here.
    # Schema initialization must be handled exclusively via Alembic migrations.
    # This prevents "Table already exists" errors during first-time setup.

    try:
        _bootstrap_admin_if_env_present()
        _bootstrap_masters()
    except Exception as e:
        # Tables might not exist yet if alembic hasn't run.
        # We log and continue so the app can start (healthz will pass),
        # allowing the user to run migrations via docker exec.
        log.warning("bootstrap_skipped_or_failed", extra={"error": str(e)})

    # Start PLC Polling Background Thread
    try:
        plc_service.start_polling_thread(PlantSessionLocal)
        log.info("plc_service_started")
    except Exception:
        log.error("plc_service_startup_failed", exc_info=True)

    log.info("plant_started", extra={"site_code": settings.plant_site_code})
