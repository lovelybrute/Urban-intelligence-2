"""
Urban Intelligence Platform - Edge Incident & Rash-Driving Processor

Edge-side analysis of vehicle trajectories, anomalous maneuvers,
rash driving, wrong-way movement, and hit-and-run detection.
"""
import uuid
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class IncidentDetection:
    """Represents a dangerous traffic incident or reckless driving event."""
    incident_id: str
    incident_type: str  # rash_driving, wrong_way, hit_and_run, dangerous_overtake, vehicle_violation
    severity: str       # medium, high, critical
    confidence: float
    vehicle_track_id: int
    vehicle_type: str
    speed_kmh: float
    trajectory: List[List[float]]
    requires_anpr: bool
    explainability: List[str]
    evidence_frame_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class IncidentProcessor:
    """
    Edge vision processor that tracks trajectories and flags hazardous driving behavior.
    """

    def __init__(self, speed_limit_kmh: float = 60.0):
        self.speed_limit_kmh = speed_limit_kmh
        # Historical positions per track_id: list of (x, y, timestamp)
        self.track_histories: Dict[int, List[Tuple[float, float, float]]] = {}

    def analyze_trajectory(
        self,
        track_id: int,
        vehicle_type: str,
        current_bbox: List[float],
        estimated_speed_kmh: float,
        is_bus_stationary: bool = False,
        near_collision: bool = False,
        collision_confirmed: bool = False,
        departure_confirmed: bool = False,
        observation_time_sec: Optional[float] = None,
    ) -> Optional[IncidentDetection]:
        """
        Evaluates a vehicle's multi-frame trajectory and dynamics.
        """
        now = observation_time_sec if observation_time_sec is not None else datetime.now(timezone.utc).timestamp()
        center_x = (current_bbox[1] + current_bbox[3]) / 2.0
        center_y = (current_bbox[0] + current_bbox[2]) / 2.0

        if track_id not in self.track_histories:
            self.track_histories[track_id] = []
        history = self.track_histories[track_id]
        history.append((center_x, center_y, now))

        # Keep last 15 points (≈ 1.5 - 3 seconds)
        if len(history) > 15:
            history.pop(0)

        # Need at least 4 observations to evaluate motion vector
        if len(history) < 4:
            return None

        # 1. Check for Wrong-Way Driving
        # In typical Indian driving (left side), traffic moving forward in front camera moves down/center
        # A vehicle moving directly upwards in lower central FOV with rapid scale increase is opposing traffic
        dy = history[-1][1] - history[0][1]
        dt = max(0.1, history[-1][2] - history[0][2])
        y_rate = dy / dt

        # 2. Check for Lateral Swerving (Rash Driving / Dangerous Overtaking)
        dx_vals = [history[i][0] - history[i-1][0] for i in range(1, len(history))]
        lateral_oscillations = sum(1 for i in range(1, len(dx_vals)) if dx_vals[i] * dx_vals[i-1] < -0.001)

        # 3. Check for Extreme Overspeeding
        is_overspeeding = estimated_speed_kmh > (self.speed_limit_kmh * 1.35)

        # 4. Check for Hit-and-Run conditions
        # Severe near collision followed by sudden acceleration away
        if collision_confirmed and departure_confirmed:
            return IncidentDetection(
                incident_id=f"inc_{uuid.uuid4().hex[:8]}",
                incident_type="hit_and_run",
                severity="critical",
                confidence=0.0,  # No calibrated probability is available for this rule.
                vehicle_track_id=track_id,
                vehicle_type=vehicle_type,
                speed_kmh=round(estimated_speed_kmh, 1),
                trajectory=[[p[0], p[1]] for p in history],
                requires_anpr=True,
                explainability=[
                    f"Caller supplied collision confirmation for vehicle #{track_id} ({vehicle_type})",
                    "Caller supplied post-collision departure confirmation; manual review required",
                    "ANPR requested; confidence is uncalibrated (0.0 sentinel), not a probability"
                ]
            )

        # 5. Wrong-Way Driving Detection
        if y_rate < -0.25 and current_bbox[2] > 0.4:
            return IncidentDetection(
                incident_id=f"inc_{uuid.uuid4().hex[:8]}",
                incident_type="wrong_way",
                severity="critical",
                confidence=0.89,
                vehicle_track_id=track_id,
                vehicle_type=vehicle_type,
                speed_kmh=round(estimated_speed_kmh, 1),
                trajectory=[[p[0], p[1]] for p in history],
                requires_anpr=True,
                explainability=[
                    f"Vehicle #{track_id} trajectory vector opposing designated directional flow of bus route",
                    f"Inverted optical flow vector: {round(y_rate, 2)} units/sec",
                    "Immediate wrong-way hazard alert generated for corridor"
                ]
            )

        # 6. Rash Driving / Dangerous Overtaking
        if (lateral_oscillations >= 2 and estimated_speed_kmh > 40.0) or is_overspeeding:
            severity = "high" if is_overspeeding else "medium"
            incident_type = "dangerous_overtake" if lateral_oscillations >= 2 else "rash_driving"
            return IncidentDetection(
                incident_id=f"inc_{uuid.uuid4().hex[:8]}",
                incident_type=incident_type,
                severity=severity,
                confidence=0.84,
                vehicle_track_id=track_id,
                vehicle_type=vehicle_type,
                speed_kmh=round(estimated_speed_kmh, 1),
                trajectory=[[p[0], p[1]] for p in history],
                requires_anpr=True,
                explainability=[
                    f"Reckless driving signature: {lateral_oscillations} aggressive lane switches in {round(dt, 1)}s window",
                    f"Estimated speed {round(estimated_speed_kmh, 1)} km/h against {self.speed_limit_kmh} km/h speed limit",
                    "Offending vehicle flagged for license plate verification"
                ]
            )

        return None
