"""
Urban Intelligence Platform - Edge Traffic Intelligence Processor

Edge-side vehicle detection, multi-object tracking, density analysis,
and congestion classification using bus camera streams.
"""
import uuid
import math
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TrackedVehicle:
    """Represents a tracked vehicle in consecutive video frames."""
    track_id: int
    vehicle_class: str  # car, bus, truck, motorcycle, auto_rickshaw, bicycle, emergency, other
    confidence: float
    bbox: List[float]  # [ymin, xmin, ymax, xmax] normalized
    speed_kmh: Optional[float]
    trajectory: List[List[float]] = field(default_factory=list)
    frames_tracked: int = 1
    direction: str = "forward"
    is_violating: bool = False
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TrafficMetrics:
    """Aggregated traffic metrics computed at the edge."""
    timestamp: str
    total_vehicles: int
    counts_by_class: Dict[str, int]
    density_score: float  # 0.0 to 1.0
    congestion_level: str  # low, moderate, high, severe
    avg_speed_kmh: Optional[float]
    flow_rate_per_min: Optional[float]
    is_bottleneck: bool
    explainability: List[str]


class TrafficProcessor:
    """
    Edge vision processor for traffic monitoring.
    Performs object tracking across frames, estimates vehicle flow and congestion.
    """

    CLASSES = [
        "car", "bus", "truck", "motorcycle", "auto_rickshaw", "bicycle", "emergency", "other"
    ]

    def __init__(self, confidence_threshold: float = 0.5, model_path: Optional[str] = None):
        self.model = None
        self.status = "MODEL NOT CONFIGURED"
        self.pedestrian_boxes = []
        if model_path:
            if not Path(model_path).is_file():
                raise FileNotFoundError(f"Traffic weights missing: {model_path}")
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.status = "WEIGHTS LOADED / ACCURACY UNVERIFIED"
        self.confidence_threshold = confidence_threshold
        self.next_track_id = 1001
        self.active_tracks: Dict[int, TrackedVehicle] = {}
        self.frame_count = 0
        self.last_clean_time = time.time() if 'time' in globals() else 0.0

    def process_frame(
        self,
        frame_array: Optional[Any],
        bus_speed_kmh: float = 25.0,
        road_speed_limit_kmh: float = 50.0
    ) -> Tuple[List[TrackedVehicle], TrafficMetrics]:
        """
        Processes video frame and outputs active tracked vehicles and traffic metrics.
        """
        self.frame_count += 1
        now_iso = datetime.now(timezone.utc).isoformat()

        # Generate / infer vehicle tracks
        tracked = self._detect_and_track(frame_array, bus_speed_kmh)

        # Aggregate traffic metrics
        class_counts = {cls: 0 for cls in self.CLASSES}
        for veh in tracked:
            cls = veh.vehicle_class if veh.vehicle_class in class_counts else "other"
            class_counts[cls] += 1

        total_vehicles = len(tracked)
        # Image occupancy is not calibrated road density or real-world speed.
        density_score = min(1.0, sum(max(0, v.bbox[2]-v.bbox[0]) * max(0, v.bbox[3]-v.bbox[1]) for v in tracked))
        speeds = [v.speed_kmh for v in tracked if v.speed_kmh is not None]
        avg_speed = sum(speeds)/len(speeds) if speeds else None
        if (avg_speed is not None and avg_speed < 12) or total_vehicles >= 14:
            congestion_level = "severe"
        elif (avg_speed is not None and avg_speed < 22) or total_vehicles >= 9:
            congestion_level = "high"
        elif total_vehicles >= 5:
            congestion_level = "moderate"
        else:
            congestion_level = "low"
        is_bottleneck = congestion_level in {"high", "severe"}
        flow_rate = None  # Requires a calibrated counting line and observation duration.

        reasons = [
            f"Observed {total_vehicles} vehicles in camera FOV: {class_counts.get('car', 0)} cars, {class_counts.get('auto_rickshaw', 0)} autos, {class_counts.get('motorcycle', 0)} 2-wheelers",
            "Speed unavailable without calibration" if avg_speed is None else f"Supplied speed: {avg_speed:.1f} km/h",
            f"Count-based congestion indicator: {congestion_level.upper()}; {int(density_score * 100)}% image occupancy",
        ]
        if is_bottleneck:
            reasons.append("Potential bottleneck requires review; camera motion and perspective affect counts")

        metrics = TrafficMetrics(
            timestamp=now_iso,
            total_vehicles=total_vehicles,
            counts_by_class=class_counts,
            density_score=round(density_score, 2),
            congestion_level=congestion_level,
            avg_speed_kmh=round(avg_speed, 1) if avg_speed is not None else None,
            flow_rate_per_min=flow_rate,
            is_bottleneck=is_bottleneck,
            explainability=reasons
        )

        return tracked, metrics

    def _detect_and_track(self, frame_array: Optional[Any], bus_speed: float) -> List[TrackedVehicle]:
        """
        Internal multi-object tracker.
        If OpenCV frame is available, extracts bounding boxes; otherwise maintains current tracks.
        """
        if frame_array is None:
            return list(self.active_tracks.values())  # Explicit manually registered test observations.
        self.pedestrian_boxes = []
        if self.model is None:
            self.active_tracks = {}
            return []
        results = self.model.track(frame_array, persist=True, tracker="bytetrack.yaml", conf=self.confidence_threshold, verbose=False)
        current = {}
        for result in results:
            for box in result.boxes:
                name = str(result.names[int(box.cls[0])])
                x1, y1, x2, y2 = box.xyxyn[0].tolist()
                bbox = [y1, x1, y2, x2]
                if name == "person":
                    self.pedestrian_boxes.append(bbox)
                    continue
                if name not in self.CLASSES or box.id is None:
                    continue
                tid = int(box.id[0])
                old = self.active_tracks.get(tid)
                current[tid] = TrackedVehicle(track_id=tid, vehicle_class=name, confidence=float(box.conf[0]),
                    bbox=bbox, speed_kmh=None, trajectory=((old.trajectory if old else []) + [[(x1+x2)/2, (y1+y2)/2]])[-30:],
                    frames_tracked=(old.frames_tracked+1 if old else 1))
        self.active_tracks = current
        return list(current.values())

    def register_manual_observation(
        self,
        vehicle_class: str,
        confidence: float,
        speed_kmh: Optional[float],
        bbox: List[float],
        is_violating: bool = False
    ) -> TrackedVehicle:
        """Helper to register a detected vehicle for testing and simulation."""
        tid = self.next_track_id
        self.next_track_id += 1
        veh = TrackedVehicle(
            track_id=tid,
            vehicle_class=vehicle_class,
            confidence=round(confidence, 2),
            bbox=bbox,
            speed_kmh=speed_kmh,
            trajectory=[bbox[:2]],
            frames_tracked=1,
            is_violating=is_violating
        )
        self.active_tracks[tid] = veh
        return veh
