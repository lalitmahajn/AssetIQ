from __future__ import annotations

import logging
from fastapi import FastAPI

from common_core.request_id import RequestIdMiddleware
from common_core.logging_setup import configure_logging
from common_core.guardrails import validate_runtime_secrets
from common_core.config import settings
from apps.hq_backend import models  # noqa: F401

from apps.hq_backend.routers.health import router as health_router
from apps.hq_backend.routers.metrics import router as metrics_router
from apps.hq_backend.routers.receiver import router as receiver_router
from apps.hq_backend.routers.dashboard import router as dashboard_router
from apps.hq_backend.routers.reports import router as reports_router

log = logging.getLogger("assetiq.hq")

app = FastAPI(title="AssetIQ HQ Backend")
app.add_middleware(RequestIdMiddleware)

app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(receiver_router)
app.include_router(dashboard_router)
app.include_router(reports_router)


@app.on_event("startup")
def startup() -> None:
    configure_logging(component="hq_backend")
    validate_runtime_secrets()
    log.info("hq_started", extra={"hq_receiver": settings.hq_receiver_url})
