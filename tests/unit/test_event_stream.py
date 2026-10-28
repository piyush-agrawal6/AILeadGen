import asyncio
import threading
import pytest
from app.api.services import event_stream


async def test_stream_database_poll_does_not_block_request_loop(monkeypatch):
    loop=asyncio.get_running_loop();started=asyncio.Event();release=threading.Event()
    def blocking_read(run_id,last_id):
        loop.call_soon_threadsafe(started.set)
        release.wait(1)
        return 'COMPLETED',[]
    monkeypatch.setattr(event_stream,'read_stream_batch',blocking_read)
    stream=event_stream.stream_scan_events(7);task=asyncio.create_task(anext(stream))
    try:
        await asyncio.wait_for(started.wait(),2)
        assert not task.done(), 'The database poll blocked the event loop until it returned'
        release.set();event=await task
        assert event.event=='pipeline_finished'
    finally:
        release.set();await stream.aclose()


async def test_missing_stream_run_returns_error(monkeypatch):
    monkeypatch.setattr(event_stream,'read_stream_batch',lambda *a:(None,[]))
    stream=event_stream.stream_scan_events(7)
    assert (await anext(stream)).event=='error'
    with pytest.raises(StopAsyncIteration):await anext(stream)
