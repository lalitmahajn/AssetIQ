from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextvars import ContextVar
from typing import Any

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_ctx.get() or "",
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for k in ("site_code", "correlation_id", "entity_type", "entity_id", "component"):
            if hasattr(record, k):
                payload[k] = getattr(record, k)
        return json.dumps(payload, ensure_ascii=False)

def configure_logging(component: str) -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("httpx").setLevel(os.environ.get("HTTPX_LOG_LEVEL", "WARNING").upper())
    logging.getLogger("sqlalchemy.engine").setLevel(os.environ.get("SQL_LOG_LEVEL", "WARNING").upper())

    logging.getLogger(__name__).info("logging_configured", extra={"component": component})
