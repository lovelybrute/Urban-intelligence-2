"""
Urban Intelligence Platform - Events API Routes
"""
import uuid
from math import radians, cos, sin, asin, sqrt
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from app.db.session import get_db
from app.models.models import (
    Event, EventCluster, RoadDefect, Alert, Bus, Camera, TrafficObservation, CongestionLevel,
    EventType, Severity, EventStatus, AlertCategory, AlertStatus
)
from app.schemas.schemas import EventCreate, EventResponse, EventUpdate
from app.core.config import settings

router = APIRouter(prefix="/api/events", tags=["Event Management"])


def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two GPS coordinates."""
    R = 6371000  # Earth radius in meters
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))


async def find_or_create_cluster(db: AsyncSession, event: Event) -> Optional[int]:
    """
    Spatial+temporal deduplication: find existing cluster or create new one.
    If a similar event exists within DEDUP_RADIUS_METERS and DEDUP_TIME_WINDOW,
    add to that cluster instead of creating a duplicate.
    """
    # Look for recent clusters of the same type nearby
    time_window = datetime.now(timezone.utc) - timedelta(seconds=settings.EDGE_DEDUP_TIME_WINDOW_SECONDS)
    result = await db.execute(
        select(EventCluster).where(
            and_(
                EventCluster.event_type == event.event_type,
                EventCluster.last_observed >= time_window,
            )
        )
    )
    clusters = result.scalars().all()

    for cluster in clusters:
        distance = haversine(
            event.latitude, event.longitude,
            cluster.center_latitude, cluster.center_longitude
        )
        if distance <= settings.EDGE_DEDUP_RADIUS_METERS:
            # Update existing cluster
            cluster.observation_count += 1
            cluster.last_observed = datetime.now(timezone.utc)
            # Repetition is not independent model validation. Retain the strongest
            # supplied detector score without inventing corroboration confidence.
            cluster.aggregate_confidence = max(cluster.aggregate_confidence, event.confidence)
            if event.bus_id:
                bus_ids = list(cluster.bus_ids or [])
                if event.bus_id not in bus_ids:
                    bus_ids.append(event.bus_id)
                    cluster.bus_ids = list(bus_ids)
            return cluster.id

    # Create new cluster
    new_cluster = EventCluster(
        cluster_id=f"CLU-{uuid.uuid4().hex[:8].upper()}",
        event_type=event.event_type,
        center_latitude=event.latitude,
        center_longitude=event.longitude,
        aggregate_confidence=event.confidence,
        severity=event.severity,
        bus_ids=[event.bus_id] if event.bus_id else [],
    )
    db.add(new_cluster)
    await db.flush()
    return new_cluster.id


@router.post("/", response_model=EventResponse)
async def create_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new detection event from edge AI."""
    if event_data.event_id:
        existing = (await db.execute(select(Event).where(Event.event_id == event_data.event_id))).scalar_one_or_none()
        if existing:
            if existing.bus_id != event_data.bus_id:
                raise HTTPException(status_code=409, detail="Event ID belongs to a different bus")
            return existing
    if not await db.get(Bus, event_data.bus_id):
        raise HTTPException(status_code=404, detail="Bus not registered")
    if event_data.camera_id:
        camera = await db.get(Camera, event_data.camera_id)
        if not camera or camera.bus_id != event_data.bus_id:
            raise HTTPException(status_code=422, detail="Camera does not belong to this bus")
    event = Event(
        event_id=event_data.event_id or f"EVT-{uuid.uuid4().hex}",
        timestamp=event_data.timestamp or datetime.now(timezone.utc),
        event_type=event_data.event_type,
        severity=event_data.severity,
        confidence=event_data.confidence,
        latitude=event_data.latitude,
        longitude=event_data.longitude,
        bus_id=event_data.bus_id,
        camera_id=event_data.camera_id,
        description=event_data.description,
        ai_reasoning=event_data.ai_reasoning,
        is_simulated=event_data.is_simulated,
        extra_metadata=event_data.metadata,
    )

    # Deduplication
    cluster_id = await find_or_create_cluster(db, event)
    event.cluster_id = cluster_id

    db.add(event)
    await db.flush()

    metadata = event_data.metadata or {}
    if event.event_type == EventType.CONGESTION and "vehicle_count" in metadata:
        count = metadata.get("vehicle_count")
        breakdown = metadata.get("vehicle_breakdown", {})
        density = metadata.get("estimated_density")
        level = metadata.get("congestion_level", "low")
        if not isinstance(count, int) or count < 0 or not isinstance(breakdown, dict) or any(not isinstance(v, int) or v < 0 for v in breakdown.values()) or level not in {c.value for c in CongestionLevel} or (density is not None and (not isinstance(density, (float, int)) or not 0 <= density <= 1)):
            raise HTTPException(422, "Invalid traffic observation metadata")
        db.add(TrafficObservation(event_id=event.id, vehicle_count=count, vehicle_breakdown=breakdown,
            estimated_density=density, congestion_level=level, average_speed=None))

    # Auto-generate alerts for high-severity events
    sev_str = event.severity.value if hasattr(event.severity, 'value') else str(event.severity)
    type_str = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)

    if sev_str in ["critical", "high"]:
        alert_category = AlertCategory.CRITICAL if sev_str == "critical" else AlertCategory.HIGH
        alert = Alert(
            alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
            category=alert_category,
            title=f"{type_str.replace('_', ' ').title()} Detected",
            description=event.description,
            event_id=event.id,
            status=AlertStatus.ACTIVE,
        )
        db.add(alert)

    await db.flush()
    await db.refresh(event)
    return event


@router.get("/", response_model=List[EventResponse])
async def get_events(
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    hours: int = Query(default=24, le=168),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get events with filters."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = select(Event).where(Event.timestamp >= since)

    if event_type:
        query = query.where(Event.event_type == event_type)
    if severity:
        query = query.where(Event.severity == severity)
    if status:
        query = query.where(Event.status == status)

    query = query.order_by(Event.timestamp.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/map-data")
async def get_map_events(
    hours: int = Query(default=24, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Get events formatted for GIS map display."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(Event)
        .where(Event.timestamp >= since)
        .order_by(Event.timestamp.desc())
        .limit(500)
    )
    events = result.scalars().all()

    return [
        {
            "id": e.id,
            "event_id": e.event_id,
            "type": e.event_type.value,
            "severity": e.severity.value,
            "confidence": e.confidence,
            "lat": e.latitude,
            "lng": e.longitude,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "bus_id": e.bus_id,
            "status": e.status.value,
            "description": e.description,
            "is_simulated": e.is_simulated,
            "ai_reasoning": e.ai_reasoning,
        }
        for e in events
    ]


@router.get("/clusters")
async def get_event_clusters(
    event_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get deduplicated event clusters."""
    query = select(EventCluster)
    if event_type:
        query = query.where(EventCluster.event_type == event_type)
    query = query.order_by(EventCluster.last_observed.desc()).limit(200)

    result = await db.execute(query)
    clusters = result.scalars().all()

    return [
        {
            "id": c.id,
            "cluster_id": c.cluster_id,
            "type": c.event_type.value,
            "severity": c.severity.value,
            "confidence": c.aggregate_confidence,
            "lat": c.center_latitude,
            "lng": c.center_longitude,
            "observation_count": c.observation_count,
            "first_observed": c.first_observed.isoformat() if c.first_observed else None,
            "last_observed": c.last_observed.isoformat() if c.last_observed else None,
            "bus_count": len(c.bus_ids) if c.bus_ids else 0,
            "status": c.status.value,
        }
        for c in clusters
    ]


@router.get("/stats")
async def get_event_stats(
    hours: int = Query(default=24, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Get event statistics for the dashboard."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Count by type
    result = await db.execute(
        select(Event.event_type, func.count(Event.id))
        .where(Event.timestamp >= since)
        .group_by(Event.event_type)
    )
    by_type = {row[0].value: row[1] for row in result.all()}

    # Count by severity
    result = await db.execute(
        select(Event.severity, func.count(Event.id))
        .where(Event.timestamp >= since)
        .group_by(Event.severity)
    )
    by_severity = {row[0].value: row[1] for row in result.all()}

    # Total
    result = await db.execute(
        select(func.count(Event.id)).where(Event.timestamp >= since)
    )
    total = result.scalar() or 0

    return {
        "total": total,
        "by_type": by_type,
        "by_severity": by_severity,
        "period_hours": hours,
    }


@router.patch("/{event_id}")
async def update_event(
    event_id: int,
    update: EventUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update event status/severity."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if update.status:
        event.status = update.status
    if update.severity:
        event.severity = update.severity
    if update.description:
        event.description = update.description

    return {"status": "updated", "event_id": event.id, "persisted": True}
