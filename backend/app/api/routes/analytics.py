"""
Urban Intelligence Platform - Alerts, Analytics, Roads & System API Routes
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from app.db.session import get_db
from app.models.models import (
    Alert, AlertStatus, AlertCategory, Event, EventType, Severity,
    Bus, BusStatus, Camera, CameraStatus, RoadSegment, RoadCondition,
    MaintenanceItem, Route, RouteDelay, TrafficObservation,
    ModelVersion, AuditLog
)
from app.schemas.schemas import (
    AlertResponse, AlertUpdate, DashboardStats, RoadSegmentResponse, SystemHealth
)
from app.core.security import get_current_user

# =============================================================================
# ALERTS ROUTER
# =============================================================================
alerts_router = APIRouter(prefix="/api/alerts", tags=["Alert Management"])


@alerts_router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get alerts with filters."""
    query = select(Alert)
    if category:
        query = query.where(Alert.category == category)
    if status:
        query = query.where(Alert.status == status)
    query = query.order_by(Alert.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@alerts_router.patch("/{alert_id}")
async def update_alert(
    alert_id: int,
    update: AlertUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update alert status (acknowledge, assign, resolve, mark false positive)."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if update.status:
        alert.status = update.status
        if update.status == AlertStatus.ACKNOWLEDGED.value:
            alert.acknowledged_at = datetime.now(timezone.utc)
        elif update.status == AlertStatus.RESOLVED.value:
            alert.resolved_at = datetime.now(timezone.utc)
    if update.assigned_to is not None:
        alert.assigned_to = update.assigned_to
    if update.resolution_notes:
        alert.resolution_notes = update.resolution_notes

    return {"status": "updated", "alert_id": alert.id, "persisted": True}


@alerts_router.get("/stats")
async def get_alert_stats(db: AsyncSession = Depends(get_db)):
    """Get alert statistics."""
    result = await db.execute(
        select(Alert.category, Alert.status, func.count(Alert.id))
        .group_by(Alert.category, Alert.status)
    )
    rows = result.all()

    stats = {"by_category": {}, "by_status": {}, "total": 0}
    for cat, stat, count in rows:
        cat_val = cat.value if hasattr(cat, 'value') else str(cat)
        stat_val = stat.value if hasattr(stat, 'value') else str(stat)
        stats["by_category"][cat_val] = stats["by_category"].get(cat_val, 0) + count
        stats["by_status"][stat_val] = stats["by_status"].get(stat_val, 0) + count
        stats["total"] += count

    return stats


# =============================================================================
# ROADS ROUTER
# =============================================================================
roads_router = APIRouter(prefix="/api/roads", tags=["Road Intelligence"])


@roads_router.get("/segments", response_model=List[RoadSegmentResponse])
async def get_road_segments(
    condition: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get road segments with condition data."""
    query = select(RoadSegment)
    if condition:
        query = query.where(RoadSegment.condition == condition)
    query = query.order_by(RoadSegment.condition_score.asc())

    result = await db.execute(query)
    return result.scalars().all()


@roads_router.get("/condition-map")
async def get_road_condition_map(db: AsyncSession = Depends(get_db)):
    """Get road condition data for GIS visualization."""
    result = await db.execute(select(RoadSegment))
    segments = result.scalars().all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "condition": s.condition.value,
            "score": s.condition_score,
            "defects": s.defect_count,
            "observations": s.observation_count,
            "start": [s.start_latitude, s.start_longitude],
            "end": [s.end_latitude, s.end_longitude],
            "last_assessed": s.last_assessed.isoformat() if s.last_assessed else None,
        }
        for s in segments
    ]


@roads_router.get("/maintenance-queue")
async def get_maintenance_queue(db: AsyncSession = Depends(get_db)):
    """Get prioritized maintenance queue."""
    result = await db.execute(
        select(MaintenanceItem).order_by(MaintenanceItem.priority_score.desc())
    )
    items = result.scalars().all()

    return [
        {
            "id": m.id,
            "title": m.title,
            "description": m.description,
            "defect_type": m.defect_type,
            "severity": m.severity.value if m.severity else None,
            "priority_score": m.priority_score,
            "observations": m.observation_count,
            "lat": m.latitude,
            "lng": m.longitude,
            "status": m.status,
        }
        for m in items
    ]


# =============================================================================
# ANALYTICS ROUTER
# =============================================================================
analytics_router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@analytics_router.get("/dashboard")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get command center dashboard statistics."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Active buses
    result = await db.execute(
        select(func.count(Bus.id)).where(Bus.status == BusStatus.ACTIVE)
    )
    active_buses = result.scalar() or 0

    # Total buses
    result = await db.execute(select(func.count(Bus.id)))
    total_buses = result.scalar() or 0

    # Events today
    result = await db.execute(
        select(func.count(Event.id)).where(Event.timestamp >= today_start)
    )
    events_today = result.scalar() or 0

    # Critical alerts
    result = await db.execute(
        select(func.count(Alert.id)).where(
            and_(Alert.category == AlertCategory.CRITICAL, Alert.status == AlertStatus.ACTIVE)
        )
    )
    critical_alerts = result.scalar() or 0

    # Road defect events today
    road_defect_types = [
        EventType.POTHOLE, EventType.CRACK, EventType.DAMAGED_ROAD,
        EventType.WATERLOGGING, EventType.DEBRIS, EventType.ROAD_HAZARD,
    ]
    result = await db.execute(
        select(func.count(Event.id)).where(
            and_(Event.event_type.in_(road_defect_types), Event.timestamp >= today_start)
        )
    )
    road_defects = result.scalar() or 0

    # Congestion zones
    result = await db.execute(
        select(func.count(Event.id)).where(
            and_(Event.event_type == EventType.CONGESTION, Event.timestamp >= today_start)
        )
    )
    congestion_zones = result.scalar() or 0

    # Safety incidents
    safety_types = [EventType.PEDESTRIAN_RISK, EventType.INCIDENT, EventType.HIT_AND_RUN, EventType.RASH_DRIVING]
    result = await db.execute(
        select(func.count(Event.id)).where(
            and_(Event.event_type.in_(safety_types), Event.timestamp >= today_start)
        )
    )
    safety_incidents = result.scalar() or 0

    # Online cameras
    result = await db.execute(
        select(func.count(Camera.id)).where(Camera.status == CameraStatus.ONLINE)
    )
    cameras_online = result.scalar() or 0

    coverage = round((active_buses / max(total_buses, 1)) * 100, 1)

    return {
        "active_buses": active_buses,
        "total_buses": total_buses,
        "events_today": events_today,
        "critical_alerts": critical_alerts,
        "road_defects": road_defects,
        "congestion_zones": congestion_zones,
        "safety_incidents": safety_incidents,
        "cameras_online": cameras_online,
        "fleet_coverage_percent": coverage,
        "system_health": "healthy",
        "timestamp": now.isoformat(),
    }


@analytics_router.get("/events-timeline")
async def get_events_timeline(
    hours: int = Query(default=24, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Get event counts by hour for timeline chart."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(Event).where(Event.timestamp >= since).order_by(Event.timestamp)
    )
    events = result.scalars().all()

    # Group by hour
    hourly = {}
    for evt in events:
        hour_key = evt.timestamp.strftime("%Y-%m-%d %H:00") if evt.timestamp else "unknown"
        if hour_key not in hourly:
            hourly[hour_key] = {"total": 0, "by_type": {}}
        hourly[hour_key]["total"] += 1
        etype = evt.event_type.value if evt.event_type else "unknown"
        hourly[hour_key]["by_type"][etype] = hourly[hour_key]["by_type"].get(etype, 0) + 1

    return [{"hour": k, **v} for k, v in sorted(hourly.items())]


@analytics_router.get("/route-delays")
async def get_route_delays(db: AsyncSession = Depends(get_db)):
    """Get current route delay information."""
    result = await db.execute(
        select(RouteDelay, Route)
        .join(Route, RouteDelay.route_id == Route.id)
        .order_by(RouteDelay.timestamp.desc())
    )
    rows = result.all()

    # Get latest per route
    seen_routes = set()
    delays = []
    for delay, route in rows:
        if route.id not in seen_routes:
            seen_routes.add(route.id)
            delays.append({
                "route_id": route.id,
                "route_number": route.route_number,
                "route_name": route.name,
                "expected_minutes": delay.expected_duration_minutes,
                "actual_minutes": delay.actual_duration_minutes,
                "delay_minutes": delay.delay_minutes,
                "congestion_factor": delay.congestion_contribution,
                "timestamp": delay.timestamp.isoformat() if delay.timestamp else None,
            })

    return delays


# =============================================================================
# ROUTES (Bus Routes) ROUTER
# =============================================================================
routes_router = APIRouter(prefix="/api/routes", tags=["Routes"])


@routes_router.get("/")
async def get_routes(db: AsyncSession = Depends(get_db)):
    """Get all bus routes."""
    result = await db.execute(select(Route).where(Route.is_active == True))
    routes = result.scalars().all()
    return [
        {
            "id": r.id,
            "route_number": r.route_number,
            "name": r.name,
            "waypoints": r.waypoints,
            "distance_km": r.distance_km,
            "duration_minutes": r.expected_duration_minutes,
        }
        for r in routes
    ]


# =============================================================================
# SYSTEM ROUTER
# =============================================================================
system_router = APIRouter(prefix="/api/system", tags=["System"])


@system_router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """System health check."""
    try:
        # Check database
        result = await db.execute(select(func.count(Bus.id)))
        bus_count = result.scalar() or 0

        result = await db.execute(
            select(func.count(Bus.id)).where(Bus.status == BusStatus.ACTIVE)
        )
        buses_online = result.scalar() or 0

        result = await db.execute(
            select(func.count(Camera.id)).where(Camera.status == CameraStatus.ONLINE)
        )
        cameras_online = result.scalar() or 0

        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = await db.execute(
            select(func.count(Event.id)).where(Event.timestamp >= since)
        )
        events_last_hour = result.scalar() or 0

        # Model versions
        result = await db.execute(
            select(ModelVersion).where(ModelVersion.is_active == True)
        )
        models = result.scalars().all()
        model_info = {m.model_name: m.version for m in models}

        return SystemHealth(
            status="healthy",
            database="connected",
            buses_online=buses_online,
            cameras_online=cameras_online,
            events_last_hour=events_last_hour,
            api_version="1.0.0",
            uptime="running",
            model_versions=model_info,
        )
    except Exception as e:
        return SystemHealth(
            status="degraded",
            database=f"error: {str(e)}",
            buses_online=0,
            cameras_online=0,
            events_last_hour=0,
            api_version="1.0.0",
            uptime="running",
        )

@analytics_router.get("/corridor-journeys")
async def get_corridor_journeys(hours: int = Query(default=24, ge=1, le=168), db: AsyncSession = Depends(get_db)):
    from app.services.mobility import corridor_journeys
    return await corridor_journeys(db, hours)

@system_router.get("/models")
async def model_readiness():
    from pathlib import Path
    from app.core.config import settings
    return [{"name": name, "artifact_present": Path(path).is_file(),
             "status": "Artifact present; inference and accuracy unverified" if Path(path).is_file() else "MODEL NOT TRAINED / ARTIFACT NOT CONFIGURED",
             "validation": None, "scope": "Central server filesystem; onboard devices may differ"}
            for name, path in [("Road defect detector", settings.ROAD_DEFECT_MODEL_PATH),
                               ("Traffic / person detector", settings.YOLO_MODEL_PATH),
                               ("Plate detector", settings.ANPR_MODEL_PATH)]]
