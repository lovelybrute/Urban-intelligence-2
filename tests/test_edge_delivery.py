"""Exercise offline recovery, recorded-video execution and GPS validity."""
import asyncio
from types import SimpleNamespace
import httpx
import numpy as np
import cv2
import pytest
from edge.managers.event_queue import EdgeEventQueue
from edge.run_video import GPSLog, run

@pytest.mark.asyncio
async def test_queue_keeps_failed_events_and_recovers(tmp_path, monkeypatch):
    original = httpx.AsyncClient
    calls = []
    def unavailable(request):
        calls.append(request)
        return httpx.Response(503)
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(unavailable), **kwargs))
    cache = str(tmp_path / 'queue.json')
    queue = EdgeEventQueue(cache_file=cache)
    queue.enqueue({'event_type':'pothole'})
    event_id = queue.queue[0].payload['event_id']
    for _ in range(7):
        queue.queue[0].next_attempt = 0
        assert await queue.sync_batch() == 0
    restored = EdgeEventQueue(cache_file=cache)
    assert restored.queue[0].retry_count == 7
    assert restored.queue[0].payload['event_id'] == event_id
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(lambda request: httpx.Response(201,json={'id':42})), **kwargs))
    restored.queue[0].next_attempt = 0
    assert await restored.sync_batch() == 1
    assert not EdgeEventQueue(cache_file=cache).queue

@pytest.mark.asyncio
async def test_recorded_video_without_weights_is_explicitly_unvalidated(tmp_path):
    video = str(tmp_path/'recording.avi')
    writer = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*'MJPG'), 10, (160,120))
    assert writer.isOpened()
    for _ in range(20):
        writer.write(np.zeros((120,160,3),dtype=np.uint8))
    writer.release()
    gps = tmp_path/'gps.csv'
    gps.write_text('seconds,latitude,longitude,speed_kmh\n0,17.43,78.4,20\n')
    assert GPSLog(gps).at(11) is None
    result = await run(SimpleNamespace(video=video,gps=str(gps),start_time='2026-09-20T10:00:00+05:30',road_weights=None,traffic_weights=None,api='http://localhost:8000',queue=str(tmp_path/'queue.json'),stride=2,sample_seconds=10,save_evidence=False,sync=False,bus_id=1,camera_position='front'))
    assert result['processed_frames'] == 10
    assert result['accuracy'] == 'NOT MEASURED'
    assert result['road_mode'] == 'opencv_heuristic_unvalidated'
