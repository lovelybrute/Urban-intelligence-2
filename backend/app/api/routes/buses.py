"""
Urban Intelligence Platform - Buses API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.db.session import get_db
from app.models.models import Bus, Camera, GPSPoint, BusStatus, CameraStatus
from app.schemas.schemas import BusResponse, BusTelemetry
from app.core.security import get_current_user
from datetime import datetime, timezone

router = APIRouter(prefix="/api/buses", tags=["Fleet Management"])


@router.get("/", response_model=List[BusResponse])
async def get_buses(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all buses, optionally filtered by status."""
    query = select(Bus)
    if status:
        query = query.where(Bus.status == status)
    query = query.order_by(Bus.bus_number)

    result = await db.execute(query)
    buses = result.scalars().all()

    response = []
    for bus in buses:
        # Get cameras for this bus
        cam_result = await db.execute(select(Camera).where(Camera.bus_id == bus.id))
        cams = cam_result.scalars().all()
        cam_data = [{"id": c.id, "position": c.position.value, "status": c.status.value} for c in cams]

        bus_dict = {
            "id": bus.id,
            "bus_number": bus.bus_number,
            "registration": bus.registration,
            "route_id": bus.route_id,
            "status": bus.status.value,
            "current_latitude": bus.current_latitude,
            "current_longitude": bus.current_longitude,
            "current_speed": bus.current_speed,
            "current_heading": bus.current_heading,
            "last_telemetry": bus.last_telemetry,
            "is_simulated": bus.is_simulated,
            "cameras": cam_data,
        }
        response.append(BusResponse(**bus_dict))

    return response


@router.get("/{bus_id}", response_model=BusResponse)
async def get_bus(bus_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific bus by ID."""
    result = await db.execute(select(Bus).where(Bus.id == bus_id))
    bus = result.scalar_one_or_none()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")

    cam_result = await db.execute(select(Camera).where(Camera.bus_id == bus.id))
    cams = cam_result.scalars().all()
    cam_data = [{"id": c.id, "position": c.position.value, "status": c.status.value} for c in cams]

    return BusResponse(
        id=bus.id,
        bus_number=bus.bus_number,
        registration=bus.registration,
        route_id=bus.route_id,
        status=bus.status.value,
        current_latitude=bus.current_latitude,
        current_longitude=bus.current_longitude,
        current_speed=bus.current_speed,
        current_heading=bus.current_heading,
        last_telemetry=bus.last_telemetry,
        is_simulated=bus.is_simulated,
        cameras=cam_data,
    )


@router.post("/telemetry")
async def update_telemetry(
    telemetry: BusTelemetry,
    db: AsyncSession = Depends(get_db),
):
    """Update bus GPS telemetry."""
    result = await db.execute(select(Bus).where(Bus.id == telemetry.bus_id))
    bus = result.scalar_one_or_none()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")

    bus.current_latitude = telemetry.latitude
    bus.current_longitude = telemetry.longitude
    bus.current_speed = telemetry.speed
    bus.current_heading = telemetry.heading
    bus.last_telemetry = telemetry.timestamp or datetime.now(timezone.utc)
    bus.status = BusStatus.ACTIVE

    # Store GPS point
    gps = GPSPoint(
        bus_id=bus.id,
        latitude=telemetry.latitude,
        longitude=telemetry.longitude,
        speed=telemetry.speed,
        heading=telemetry.heading,
        is_simulated=telemetry.is_simulated,
        timestamp=telemetry.timestamp or datetime.now(timezone.utc),
    )
    db.add(gps)

    return {"status": "ok", "bus_id": bus.id}


@router.get("/{bus_id}/gps-trail")
async def get_gps_trail(
    bus_id: int,
    limit: int = Query(default=100, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Get recent GPS trail for a bus."""
    result = await db.execute(
        select(GPSPoint)
        .where(GPSPoint.bus_id == bus_id)
        .order_by(GPSPoint.timestamp.desc())
        .limit(limit)
    )
    points = result.scalars().all()
    return [
        {
            "latitude": p.latitude,
            "longitude": p.longitude,
            "speed": p.speed,
            "heading": p.heading,
            "timestamp": p.timestamp.isoformat() if p.timestamp else None,
        }
        for p in reversed(points)
    ]
