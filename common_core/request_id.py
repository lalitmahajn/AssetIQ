from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from common_core.logging_setup import request_id_ctx


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = rid
        token = request_id_ctx.set(rid)
        try:
            resp: Response = await call_next(request)
            resp.headers["X-Request-Id"] = rid
            return resp
        finally:
            request_id_ctx.reset(token)
