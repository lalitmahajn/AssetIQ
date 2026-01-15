from __future__ import annotations
import asyncio
from typing import AsyncIterator
from common_core.realtime.sse_bus import SseEvent

async def with_heartbeat(it: AsyncIterator[SseEvent], interval_s: float = 15.0) -> AsyncIterator[str]:
    while True:
        try:
            ev = await asyncio.wait_for(it.__anext__(), timeout=interval_s)
            yield f"id: {ev.id}\n"
            yield f"data: {ev.data_json}\n\n"
        except asyncio.TimeoutError:
            yield ": hb\n\n"
        except StopAsyncIteration:
            return
