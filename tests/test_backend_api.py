"""
Urban Intelligence Platform - Backend API Integration Tests
"""
import sys
import os
import pytest
import httpx

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import tempfile
_test_dir = tempfile.TemporaryDirectory(prefix="urban-tests-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_dir.name}/test.db"
os.environ["EVIDENCE_DIR"] = f"{_test_dir.name}/evidence"
from app.main import app
from app.db.session import init_db, async_session, close_db
from app.db.seed import seed_database
from app.core.security import create_access_token

def auth_headers():
    return {"Authorization": "Bearer " + create_access_token({"sub": "1", "role": "admin"})}


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    import asyncio
    async def _init():
        await init_db()
        async with async_session() as s:
            await seed_database(s)
    asyncio.run(_init())
    yield


@pytest.mark.asyncio
async def test_api_root():
    """Verify API root endpoint returns platform metadata."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=auth_headers()) as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "Urban Intelligence Platform"
        assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_auth_login():
    """Verify JWT authentication endpoint for seeded admin user."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=auth_headers()) as ac:
        response = await ac.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_get_buses():
    """Verify buses list endpoint."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=auth_headers()) as ac:
        response = await ac.get("/api/buses/")
        assert response.status_code == 200
        buses = response.json()
        assert len(buses) >= 10
        assert "bus_number" in buses[0]


@pytest.mark.asyncio
async def test_get_roads_and_maintenance():
    """Verify road segment health and maintenance queue."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=auth_headers()) as ac:
        res_roads = await ac.get("/api/roads/segments")
        assert res_roads.status_code == 200
        assert len(res_roads.json()) >= 4

        res_maint = await ac.get("/api/roads/maintenance-queue")
        assert res_maint.status_code == 200
        assert len(res_maint.json()) >= 1


@pytest.mark.asyncio
async def test_event_submission_and_retrieval():
    """Verify edge event upload and retrieval."""
    test_event = {
        "event_id": "test_evt_api_99",
        "event_type": "pothole",
        "severity": "high",
        "confidence": 0.91,
        "latitude": 17.4405,
        "longitude": 78.4985,
        "bus_id": 1,
        "description": "Integration test pothole detection",
        "is_simulated": True
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=auth_headers()) as ac:
        res_post = await ac.post("/api/events/", json=test_event)
        assert res_post.status_code in [200, 201]
        created_id = res_post.json()["event_id"]

        res_get = await ac.get("/api/events/")
        assert res_get.status_code == 200
        events = res_get.json()
        assert any(e["event_id"] == created_id for e in events)


@pytest.mark.asyncio
async def test_protected_operations_and_idempotent_ingestion():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        assert (await ac.get("/api/buses/")).status_code in (401, 403)
        assert (await ac.post("/api/auth/register", json={"username":"intruder","password":"longpassword","role":"admin"})).status_code in (401,403)
        ac.headers.update(auth_headers())
        payload = {"event_id":"retry-safe-event", "bus_id":1, "event_type":"pothole", "severity":"critical", "confidence":0.8, "latitude":17.43, "longitude":78.4, "is_simulated":True}
        first = await ac.post("/api/events/",json=payload)
        second = await ac.post("/api/events/",json=payload)
        assert first.status_code in (200,201), first.text
        assert second.json()["id"] == first.json()["id"]
        event_id = first.json()["id"]
        assert (await ac.patch(f"/api/events/{event_id}",json={"status":"resolved"})).status_code == 200
        assert next(e for e in (await ac.get("/api/events/")).json() if e["id"] == event_id)["status"] == "resolved"
        assert (await ac.post("/api/events/",json={**payload,"event_id":"invalid-gps","latitude":200})).status_code == 422
        import io
        from PIL import Image
        raw = io.BytesIO()
        Image.new("RGB",(20,20)).save(raw,format="PNG")
        uploaded = await ac.post(f"/api/events/{event_id}/evidence",files={"file":("test.png",raw.getvalue(),"image/png")})
        assert uploaded.status_code == 200, uploaded.text
        evidence = await ac.get(f"/api/events/{event_id}/evidence")
        assert evidence.status_code == 200
        assert evidence.headers["content-type"] == "image/jpeg"
        assert (await ac.get("/api/analytics/corridor-journeys")).status_code == 200
        assert (await ac.get("/api/system/models")).status_code == 200
