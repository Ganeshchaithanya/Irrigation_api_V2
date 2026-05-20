"""Server‑Sent Events (SSE) notification endpoint.

This is a minimal placeholder that can be expanded later. It returns a
simple infinite async generator that yields a JSON‑encoded heartbeat
message every few seconds. The route is mounted under the same API
prefix as the other routers.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse as EventSourceResponse
import asyncio
import json

router = APIRouter(prefix="/notifications", tags=["Notifications"])

async def event_generator(request: Request):
    """Yield a heartbeat event every 5 seconds until the client disconnects.

    In a real implementation you would subscribe to a message broker or
    database change stream and push actual notifications.
    """
    while True:
        # If the client closed the connection, stop the generator.
        if await request.is_disconnected():
            break
        payload = {"type": "heartbeat", "message": "alive"}
        yield f"data: {json.dumps(payload)}\n\n"
        await asyncio.sleep(5)

@router.get("/stream", response_class=EventSourceResponse)
async def stream_notifications(request: Request):
    """SSE endpoint that streams notification events.

    Clients can connect with `EventSource` in JavaScript:
    ```js
    const evtSource = new EventSource('/api/v1/notifications/stream');
    evtSource.onmessage = (e) => console.log('notification', JSON.parse(e.data));
    ```
    """
    return EventSourceResponse(event_generator(request))
