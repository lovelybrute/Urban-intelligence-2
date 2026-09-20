"""Recorded-video -> edge detections -> durable queue -> authenticated central API.
Run from repository root: python -m edge.run_video --help
"""
import argparse
import asyncio
import csv
import json
import os
import time
import uuid
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from pathlib import Path
import cv2
from edge.processors.road_defect import RoadDefectProcessor
from edge.processors.traffic import TrafficProcessor
from edge.processors.safety import SafetyProcessor
from edge.processors.incident import IncidentProcessor
from edge.processors.anpr import ANPRProcessor
from edge.managers.event_queue import EdgeEventQueue
from edge.managers.spatial_dedup import SpatialDeduplicator
from edge.managers.privacy import PrivacyFilter

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROAD_WEIGHTS = REPO_ROOT / "frontend" / "ml" / "weights" / "road_defect_best.pt"
DEFAULT_TRAFFIC_WEIGHTS = REPO_ROOT / "frontend" / "ml" / "weights" / "traffic_coco.pt"
CUSTOM_TRAFFIC_WEIGHTS = REPO_ROOT / "frontend" / "ml" / "weights" / "traffic_india.pt"
DEFAULT_INFRASTRUCTURE_WEIGHTS = REPO_ROOT / "frontend" / "ml" / "weights" / "infrastructure.pt"
DEFAULT_ANPR_WEIGHTS = REPO_ROOT / "frontend" / "ml" / "weights" / "anpr_plate.pt"

class GPSLog:
    def __init__(self, path):
        with open(path, newline="", encoding="utf-8-sig") as stream:
            self.rows = [{k: float(row[k]) for k in ["seconds", "latitude", "longitude", "speed_kmh"]} for row in csv.DictReader(stream)]
        if not self.rows or any(not(-90 <= r["latitude"] <=90 and -180 <= r["longitude"] <=180) for r in self.rows):
            raise ValueError("GPS CSV is empty or coordinates are invalid")
        self.rows.sort(key=lambda row: row["seconds"])
        self.seconds = [r["seconds"] for r in self.rows]
    def at(self, seconds):
        idx = bisect_right(self.seconds, seconds)-1
        if idx < 0 or seconds-self.seconds[idx] > 10:
            return None
        return self.rows[idx]

async def run(args):
    if not Path(args.video).is_file():
        raise ValueError("Video file not found")
    gps = GPSLog(args.gps)
    start = datetime.fromisoformat(args.start_time.replace('Z','+00:00'))
    if start.tzinfo is None:
        raise ValueError("Start time must include timezone, e.g. +05:30")
    if args.road_weights and not Path(args.road_weights).is_file():
        raise ValueError("Road weights not found")
    if args.infrastructure_weights and not Path(args.infrastructure_weights).is_file():
        raise ValueError("Infrastructure weights not found")
    if args.anpr_weights and not Path(args.anpr_weights).is_file():
        raise ValueError("ANPR weights not found")
    road = RoadDefectProcessor(model_path=args.road_weights)
    if args.road_weights and not road.is_model_loaded:
        raise RuntimeError("Road weights failed to load; install edge inference dependencies")
    infrastructure = RoadDefectProcessor(model_path=args.infrastructure_weights)
    if args.infrastructure_weights and not infrastructure.is_model_loaded:
        raise RuntimeError("Infrastructure weights failed to load; install edge inference dependencies")
    traffic = TrafficProcessor(model_path=args.traffic_weights)
    safety = SafetyProcessor()
    incident = IncidentProcessor()
    anpr = ANPRProcessor(model_path=args.anpr_weights)
    queue = EdgeEventQueue(args.api, os.environ.get("URBAN_API_TOKEN"), args.queue)
    dedup = SpatialDeduplicator(time_window_seconds=60)
    capture = cv2.VideoCapture(args.video)
    if not capture.isOpened():
        raise ValueError("Video could not be decoded")
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        raise ValueError("Video frame rate unavailable")
    evidence_dir = Path(args.queue).parent / 'evidence'
    evidence_dir.mkdir(parents=True, exist_ok=True)
    processed = emitted = skipped_gps = 0
    last_traffic = -args.sample_seconds
    started = time.perf_counter()
    def emit(kind, severity, confidence, reasons, metadata, position, timestamp, evidence=None):
        nonlocal emitted
        duplicate, _ = dedup.check_and_update(kind, position['latitude'], position['longitude'], confidence)
        if duplicate and kind != 'congestion':
            return
        queue.enqueue({"event_id": f"EDGE-{uuid.uuid4().hex}", "event_type": kind, "severity": severity,
            "confidence": confidence, "latitude": position['latitude'], "longitude": position['longitude'],
            "bus_id": args.bus_id, "timestamp": timestamp, "is_simulated": False,
            "description": f"{kind.replace('_',' ').title()} candidate from recorded video; operator review required",
            "ai_reasoning": reasons, "metadata": {**metadata, "source": "recorded_video", "camera_position": args.camera_position}},
            priority=1 if severity=='critical' else 2 if severity=='high' else 3, evidence_file=evidence)
        emitted += 1
    def vehicle_crop(frame, bbox):
        height, width = frame.shape[:2]
        y1, x1, y2, x2 = bbox
        left, top = max(0, int(x1 * width)), max(0, int(y1 * height))
        right, bottom = min(width, int(x2 * width)), min(height, int(y2 * height))
        return frame[top:bottom, left:right] if right > left and bottom > top else None
    try:
        index = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            seconds = index / fps
            index += 1
            if index % args.stride:
                continue
            position = gps.at(seconds)
            if not position:
                skipped_gps += 1
                continue
            processed += 1
            timestamp = (start + timedelta(seconds=seconds)).isoformat()
            tracks, metrics = traffic.process_frame(frame, position['speed_kmh'])
            evidence = None
            if args.save_evidence and traffic.model is not None and seconds-last_traffic >= args.sample_seconds:
                # Conservative vehicle/person-region blurring. Missed detections remain possible;
                # review evidence before sharing outside the authorized command system.
                private = PrivacyFilter().sanitize_frame(frame, traffic.pedestrian_boxes, [v.bbox for v in tracks])
                path = evidence_dir / f"{uuid.uuid4().hex}.jpg"
                if cv2.imwrite(str(path), private):
                    evidence = str(path)
            if args.camera_position == 'front':
                for detection in road.process_frame(frame, args.camera_position, position['latitude'], position['longitude'], position['speed_kmh']):
                    emit(detection.defect_type, detection.severity, detection.confidence, detection.explainability,
                         {**detection.metadata, "bbox": detection.bbox, "method": 'yolo' if road.is_model_loaded else 'opencv_heuristic', "confidence_calibrated": False}, position, timestamp, evidence)
                if infrastructure.is_model_loaded:
                    for detection in infrastructure.process_frame(frame, args.camera_position, position['latitude'], position['longitude'], position['speed_kmh']):
                        emit(detection.defect_type, detection.severity, detection.confidence, detection.explainability,
                             {**detection.metadata, "bbox": detection.bbox, "method": "custom_infrastructure_yolo", "confidence_calibrated": False}, position, timestamp, evidence)
                risk = safety.evaluate_pedestrians(traffic.pedestrian_boxes, position['speed_kmh'], position['latitude'], position['longitude'])
                if risk:
                    emit('pedestrian_risk',risk.risk_level,0.0,risk.explainability,{"method":"uncalibrated_risk_rules","confidence_calibrated":False},position,timestamp,evidence)
                for vehicle in tracks:
                    detected_incident = incident.analyze_trajectory(
                        vehicle.track_id,
                        vehicle.vehicle_class,
                        vehicle.bbox,
                        vehicle.speed_kmh or 0.0,
                        observation_time_sec=seconds,
                    )
                    if detected_incident is None:
                        continue
                    plate = anpr.process_vehicle_crop(
                        vehicle.track_id,
                        vehicle_crop(frame, vehicle.bbox),
                    ) if detected_incident.requires_anpr else None
                    incident_metadata = {
                        "track_id": vehicle.track_id,
                        "vehicle_type": vehicle.vehicle_class,
                        "trajectory": detected_incident.trajectory,
                        "method": "uncalibrated_temporal_rules",
                        "confidence_calibrated": False,
                    }
                    if plate:
                        incident_metadata.update({
                            "plate_number": plate.plate_number,
                            "plate_confidence": plate.overall_confidence,
                            "plate_requires_review": plate.requires_manual_verification,
                        })
                    emit(detected_incident.incident_type, detected_incident.severity, 0.0,
                         detected_incident.explainability, incident_metadata, position, timestamp, evidence)
            if traffic.model is not None and seconds-last_traffic >= args.sample_seconds:
                emit('congestion','high' if metrics.is_bottleneck else 'low',0.0,metrics.explainability,
                     {"vehicle_count": metrics.total_vehicles,"vehicle_breakdown": metrics.counts_by_class,
                      "estimated_density": metrics.density_score,"congestion_level": metrics.congestion_level,
                      "confidence_calibrated":False,"method":"yolo_bytetrack_count_rules"},position,timestamp,evidence)
                last_traffic = seconds
            if args.sync and processed % 30 == 0:
                await queue.sync_batch()
        if args.sync:
            while queue.queue:
                before = len(queue.queue)
                await queue.sync_batch()
                if len(queue.queue) >= before:
                    break
    finally:
        capture.release()
    result={"processed_frames":processed,"events_queued":emitted,"pending_delivery":len(queue.queue),
        "skipped_frames_without_recent_gps":skipped_gps,"processing_fps":round(processed/max(.001,time.perf_counter()-started),2),
        "road_mode":"weights_loaded_unvalidated" if road.is_model_loaded else "opencv_heuristic_unvalidated",
        "infrastructure_mode":"weights_loaded_unvalidated" if infrastructure.is_model_loaded else "not_configured",
        "traffic_mode":traffic.status,
        "anpr_mode":"detector_and_ocr_unvalidated" if anpr.model is not None else "ocr_only_manual_review",
        "accuracy":"NOT MEASURED"}
    print(json.dumps(result,indent=2))
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video',required=True)
    parser.add_argument('--gps',required=True,help='CSV: seconds,latitude,longitude,speed_kmh')
    parser.add_argument('--start-time',required=True,help='Recording start in ISO 8601 with timezone')
    parser.add_argument('--bus-id',type=int,required=True)
    parser.add_argument('--camera-position',choices=['front','rear','left','right','interior'],default='front')
    parser.add_argument('--road-weights', default=str(DEFAULT_ROAD_WEIGHTS) if DEFAULT_ROAD_WEIGHTS.is_file() else None)
    parser.add_argument('--traffic-weights', default=str(CUSTOM_TRAFFIC_WEIGHTS) if CUSTOM_TRAFFIC_WEIGHTS.is_file() else (str(DEFAULT_TRAFFIC_WEIGHTS) if DEFAULT_TRAFFIC_WEIGHTS.is_file() else None))
    parser.add_argument('--infrastructure-weights', default=str(DEFAULT_INFRASTRUCTURE_WEIGHTS) if DEFAULT_INFRASTRUCTURE_WEIGHTS.is_file() else None)
    parser.add_argument('--anpr-weights', default=str(DEFAULT_ANPR_WEIGHTS) if DEFAULT_ANPR_WEIGHTS.is_file() else None)
    parser.add_argument('--api',default='http://127.0.0.1:8000')
    parser.add_argument('--queue',default='edge_output/events.json')
    parser.add_argument('--stride',type=int,default=3)
    parser.add_argument('--sample-seconds',type=float,default=10)
    parser.add_argument('--save-evidence',action='store_true')
    parser.add_argument('--sync',action='store_true')
    args=parser.parse_args()
    if args.stride < 1 or args.sample_seconds < 1:
        parser.error('stride and sample-seconds must be at least 1')
    if args.sync and not os.environ.get('URBAN_API_TOKEN'):
        parser.error('Set URBAN_API_TOKEN to a valid operator token before syncing')
    asyncio.run(run(args))
if __name__=='__main__':
    main()
