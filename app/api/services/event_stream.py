import asyncio
import json
import logging
from typing import AsyncGenerator
from sse_starlette.sse import ServerSentEvent

from app.database.connection import db_session
from app.database.repositories import PipelineRunEventRepository, PipelineRunRepository

logger = logging.getLogger("leadengine.api.events")


def read_stream_batch(run_id,last_id):
    # Each poll owns a short connection; blocking database IO stays off the
    # ASGI event loop, including when several browser monitors are open.
    with db_session() as conn:
        run=PipelineRunRepository(conn).get_by_id(run_id)
        if not run:return None,[]
        events=PipelineRunEventRepository(conn).list_by_run(run_id=run_id,after_id=last_id,limit=100)
        return run.status,events


async def stream_scan_events(run_id: int) -> AsyncGenerator[ServerSentEvent, None]:
    """Streams pipeline events for a specific scan as Server-Sent Events."""
    last_id = 0
    poll_interval = 2.0  # seconds; bounded polling across multiple open monitors
    idle_cycles = 0
    max_idle_cycles = 900  # 30 minutes of idle polling

    while idle_cycles < max_idle_cycles:
        events = []
        terminal_status = None

        status,events=await asyncio.to_thread(read_stream_batch,run_id,last_id)
        if status is None:
            yield ServerSentEvent(data=json.dumps({"error":f"Scan #{run_id} not found"}),event="error")
            break
        if status in ("COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED"):
            terminal_status=status

        if events:
            for evt in events:
                last_id = max(last_id, evt.id or 0)
                yield ServerSentEvent(
                    data=json.dumps(evt.model_dump()),
                    event="pipeline_event",
                    id=str(evt.id),
                )
            idle_cycles = 0
        else:
            idle_cycles += 1

        # If terminal status reached and all events yielded, send terminal event and complete
        if terminal_status and not events:
            yield ServerSentEvent(
                data=json.dumps({"status": terminal_status, "run_id": run_id}),
                event="pipeline_finished",
            )
            break

        await asyncio.sleep(poll_interval)
