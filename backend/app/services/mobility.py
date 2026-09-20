"""Observed bus corridor journeys, not individual citizens' origin/destination paths."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.models.models import Route, Bus, GPSPoint
from app.api.routes.events import haversine

async def corridor_journeys(db, hours=24):
    routes = (await db.execute(select(Route).where(Route.is_active == True))).scalars().all()
    buses = (await db.execute(select(Bus))).scalars().all()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    points = (await db.execute(select(GPSPoint).where(GPSPoint.timestamp >= since).order_by(GPSPoint.timestamp))).scalars().all()
    by_bus = {}
    for point in points:
        by_bus.setdefault(point.bus_id, []).append(point)
    output = []
    for route in routes:
        journeys = []
        if not route.waypoints or len(route.waypoints) < 2:
            continue
        start, end = route.waypoints[0], route.waypoints[-1]
        for bus in buses:
            if bus.route_id != route.id:
                continue
            departure = None
            last_point = None
            for point in by_bus.get(bus.id, []):
                if last_point and (point.timestamp - last_point.timestamp).total_seconds() > 600:
                    departure = None  # Do not infer a complete journey across a GPS outage.
                last_point = point
                if haversine(point.latitude, point.longitude, *start) <= 150:
                    departure = point  # Last origin sighting approximates departure.
                elif departure and haversine(point.latitude, point.longitude, *end) <= 150:
                    minutes = (point.timestamp - departure.timestamp).total_seconds() / 60
                    if minutes >= 1:
                        journeys.append({"bus_id": bus.id, "minutes": round(minutes, 1), "is_simulated": bool(departure.is_simulated or point.is_simulated), "arrived_at": point.timestamp.isoformat()})
                    departure = None
        parts = route.name.split(" - ", 1)
        average = round(sum(j["minutes"] for j in journeys)/len(journeys), 1) if journeys else None
        output.append({"route_id": route.id, "route_number": route.route_number, "route_name": route.name,
            "origin": parts[0], "destination": parts[-1], "observations": len(journeys),
            "average_minutes": average, "expected_minutes": route.expected_duration_minutes,
            "delay_minutes": round(average-route.expected_duration_minutes,1) if average is not None and route.expected_duration_minutes else None,
            "simulated_journeys": sum(j["is_simulated"] for j in journeys), "journeys": journeys,
            "basis": "Bus GPS endpoint crossings within 150 m; maximum sample gap 10 minutes"})
    return output
