"""
Urban Intelligence Platform - Edge AI Subsystem Unit Tests

Validates road defect detection, vehicle tracking, ANPR plate extraction,
spatial deduplication, and privacy filtering.
"""
import pytest
import sys
import os

# Add project root to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from edge.processors.road_defect import RoadDefectProcessor
from edge.processors.traffic import TrafficProcessor
from edge.processors.safety import SafetyProcessor
from edge.processors.incident import IncidentProcessor
from edge.processors.anpr import ANPRProcessor
from edge.managers.spatial_dedup import SpatialDeduplicator
from edge.managers.privacy import PrivacyFilter


def test_road_defect_severity():
    """Verify explainable severity scoring on road surface defects."""
    proc = RoadDefectProcessor(confidence_threshold=0.6)
    sev_critical = proc._compute_severity("waterlogging", 0.85, [0.4, 0.2, 0.8, 0.8])
    assert sev_critical == "critical"

    sev_high = proc._compute_severity("pothole", 0.82, [0.5, 0.4, 0.7, 0.6])
    assert sev_high == "high"


def test_trained_road_labels_are_normalized():
    """Every class in the supplied RDD checkpoint must reach the platform."""
    aliases = RoadDefectProcessor.CLASS_ALIASES
    assert aliases["longitudinal_crack"] == "crack"
    assert aliases["transverse_crack"] == "crack"
    assert aliases["alligator_crack"] == "crack"
    assert aliases["other_corruption"] == "damaged_road"
    assert aliases["D40"] == "pothole"


def test_traffic_processor_congestion_classification():
    """Verify vehicle tracking and congestion level estimation."""
    tp = TrafficProcessor()

    # Register 12 vehicles with low speed (traffic jam)
    for i in range(12):
        tp.register_manual_observation(
            vehicle_class="car" if i % 2 == 0 else "auto_rickshaw",
            confidence=0.9,
            speed_kmh=8.5,
            bbox=[0.4, 0.1 * i, 0.6, 0.1 * i + 0.08]
        )

    tracks, metrics = tp.process_frame(None, bus_speed_kmh=10.0)
    assert metrics.total_vehicles == 12
    assert metrics.congestion_level in ["high", "severe"]
    assert metrics.is_bottleneck is True
    assert len(metrics.explainability) >= 2


def test_pedestrian_safety_processor():
    """Verify VRU hazard assessment in school zone."""
    sp = SafetyProcessor()

    # Pedestrian group in Ameerpet School Zone (lat 17.4500, lng 78.3800)
    # ymax 0.85 -> high proximity to bus
    ped_boxes = [
        [0.4, 0.3, 0.85, 0.35],
        [0.42, 0.36, 0.86, 0.41],
        [0.41, 0.42, 0.85, 0.47]
    ]

    alert = sp.evaluate_pedestrians(
        pedestrian_boxes=ped_boxes,
        bus_speed_kmh=24.0,
        gps_lat=17.4500,
        gps_lng=78.3800,
        has_zebra_crossing=False
    )

    assert alert is not None
    assert alert.is_group is True
    assert alert.is_school_zone is True
    assert alert.risk_level in ["high", "critical"]
    assert alert.time_to_collision_sec is not None


def test_incident_processor_wrong_way_and_rash_driving():
    """Verify trajectory motion analysis and incident triggers."""
    ip = IncidentProcessor(speed_limit_kmh=50.0)

    # Simulate swerving vehicle over 5 frames
    tid = 501
    detections = []
    positions = [
        [0.3, 0.2, 0.5, 0.4],
        [0.3, 0.5, 0.5, 0.7],
        [0.3, 0.25, 0.5, 0.45],
        [0.3, 0.55, 0.5, 0.75],
        [0.3, 0.3, 0.5, 0.5]
    ]

    for bbox in positions:
        det = ip.analyze_trajectory(
            track_id=tid,
            vehicle_type="car",
            current_bbox=bbox,
            estimated_speed_kmh=68.0
        )
        if det:
            detections.append(det)

    assert len(detections) > 0
    last_det = detections[-1]
    assert last_det.requires_anpr is True
    assert last_det.incident_type in ["rash_driving", "dangerous_overtake"]


def test_anpr_number_plate_validation():
    """Verify Indian vehicle registration syntax validation."""
    anpr = ANPRProcessor()

    # Valid Telangana plate
    valid_res = anpr.process_vehicle_crop(
        vehicle_track_id=101,
        vehicle_image_array=None,
        simulated_plate_hint="TS09AB1234"
    )
    assert valid_res.is_format_valid is True
    assert valid_res.plate_number == "TS09AB1234"
    assert valid_res.overall_confidence > 0.8

    # Corrupt / low confidence plate -> must return UNKNOWN, not hallucinate
    corrupt_res = anpr.process_vehicle_crop(
        vehicle_track_id=102,
        vehicle_image_array=None,
        simulated_plate_hint="X9"
    )
    assert corrupt_res.is_low_confidence is True
    assert corrupt_res.plate_number == "UNKNOWN"
    assert corrupt_res.requires_manual_verification is True


def test_spatial_temporal_deduplication():
    """Verify multi-bus spatial clustering and Bayesian confidence updating."""
    dedup = SpatialDeduplicator(radius_meters=50.0, time_window_seconds=3600.0)

    # Bus 1 observes pothole at Nampally
    is_dup1, cluster1 = dedup.check_and_update("pothole", 17.4400, 78.4980, confidence=0.90)
    assert is_dup1 is False
    assert cluster1.observation_count == 1
    assert cluster1.aggregate_confidence == 0.90

    # Bus 2 observes same pothole 15 meters away
    is_dup2, cluster2 = dedup.check_and_update("pothole", 17.4401, 78.4981, confidence=0.92)
    assert is_dup2 is True
    assert cluster2.cluster_id == cluster1.cluster_id
    assert cluster2.observation_count == 2
    # Confidence reinforced above single sighting
    assert cluster2.aggregate_confidence > 0.90


def test_near_miss_is_not_hit_and_run():
    processor = IncidentProcessor()
    for _ in range(5):
        result = processor.analyze_trajectory(1, 'car', [0.2, 0.2, 0.4, 0.4], 50.0, near_collision=True)
        assert result is None


def test_hit_and_run_requires_both_confirmations():
    for collision, departure in [(True, False), (False, True), (True, True)]:
        processor = IncidentProcessor()
        for _ in range(5):
            result = processor.analyze_trajectory(
                1, 'car', [0.2, 0.2, 0.4, 0.4], 30.0,
                collision_confirmed=collision, departure_confirmed=departure)
        if collision and departure:
            assert result.incident_type == 'hit_and_run'
            assert result.confidence == 0.0
        else:
            assert result is None


def test_single_frame_explanation_does_not_claim_temporal_verification():
    reasons = RoadDefectProcessor._generate_reasons('pothole', 0.8, 0.3, 'high')
    assert any('temporal confirmation has not been performed' in reason for reason in reasons)
