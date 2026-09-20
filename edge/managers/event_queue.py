"""Durable metadata queue with bounded exponential backoff and idempotent delivery."""
import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
import httpx

@dataclass
class EdgeQueueItem:
    queue_id: str
    payload: Dict[str, Any]
    priority: int
    retry_count: int = 0
    max_retries: int = 5  # Legacy cache compatibility; events are no longer discarded.
    created_at: float = 0
    next_attempt: float = 0
    evidence_file: Optional[str] = None
    server_event_id: Optional[int] = None
    last_error: Optional[str] = None

class EdgeEventQueue:
    def __init__(self, api_base_url="http://localhost:8000", api_token=None, cache_file="./edge_event_cache.json"):
        self.api_base_url = api_base_url.rstrip("/")
        self.api_token = api_token
        self.cache_file = cache_file
        self.queue = []
        self._sync_lock = asyncio.Lock()
        self._load_cache()

    def enqueue(self, payload, priority=3, evidence_file=None):
        payload = dict(payload)
        payload.setdefault("event_id", f"EDGE-{uuid.uuid4().hex}")
        item = EdgeQueueItem(payload["event_id"], payload, priority, created_at=time.time(), evidence_file=evidence_file)
        self.queue.append(item)
        self.queue.sort(key=lambda x: x.priority)
        self._save_cache()

    async def sync_batch(self, max_items=10):
        async with self._sync_lock:
            pending = [item for item in self.queue if item.next_attempt <= time.time()][:max_items]
            synced = 0
            headers = {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}
            async with httpx.AsyncClient(timeout=10, headers=headers) as client:
                for item in pending:
                    try:
                        if item.server_event_id is None:
                            response = await client.post(f"{self.api_base_url}/api/events/", json=item.payload)
                            response.raise_for_status()
                            item.server_event_id = response.json()["id"]
                            self._save_cache()
                        if item.evidence_file:
                            with open(item.evidence_file, "rb") as image:
                                response = await client.post(f"{self.api_base_url}/api/events/{item.server_event_id}/evidence", files={"file": ("evidence.jpg", image, "image/jpeg")})
                            response.raise_for_status()
                        self.queue.remove(item)
                        synced += 1
                    except (httpx.HTTPError, OSError, ValueError, KeyError) as error:
                        item.retry_count += 1
                        item.next_attempt = time.time() + min(300, 2 ** min(item.retry_count, 9))
                        item.last_error = type(error).__name__
                    self._save_cache()
            return synced

    def _save_cache(self):
        path = Path(self.cache_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8") as stream:
            json.dump([asdict(item) for item in self.queue], stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)

    def _load_cache(self):
        path = Path(self.cache_file)
        if path.exists():
            # Fail visibly on corruption, rather than replacing unsent evidence with an empty queue.
            self.queue = [EdgeQueueItem(**item) for item in json.loads(path.read_text())]
