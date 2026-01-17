from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from apps.plant_backend.runtime import sse_bus
from common_core.realtime.sse_heartbeat import with_heartbeat

router = APIRouter(prefix="/realtime", tags=["realtime"])


@router.get("/stop-events")
async def stop_events(request: Request):
    last_id = request.headers.get("Last-Event-ID") or request.query_params.get("lastEventId")
    sub = sse_bus.subscribe(last_event_id=last_id)

    async def gen():
        async for chunk in with_heartbeat(sub, interval_s=15.0):
            yield chunk

    return StreamingResponse(gen(), media_type="text/event-stream")
