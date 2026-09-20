"""
Urban Intelligence Platform - Edge Road Defect Processor

Edge-side computer vision processor for detecting road surface defects,
structural damage, and missing infrastructure elements from bus-mounted cameras.
"""
import uuid
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class DefectDetection:
    """Represents a road defect detected by edge vision models."""
    detection_id: str
    defect_type: str  # pothole, crack, waterlogging, damaged_divider, missing_sign, etc.
    severity: str     # low, medium, high, critical
    confidence: float
    bbox: List[float]  # [ymin, xmin, ymax, xmax] normalized
    area_sq_meters: float
    explainability: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RoadDefectProcessor:
    """
    Edge inference processor for road defects.
    Designed for real-time edge execution on bus onboard compute units (NVIDIA Jetson / x86).
    Supports PyTorch/YOLO/ONNX models or simulated heuristic fallback.
    """

    DEFECT_TYPES = [
        "pothole", "crack", "damaged_road", "waterlogging", "debris",
        "damaged_divider", "missing_divider", "damaged_zebra", "missing_zebra",
        "damaged_sign", "missing_sign", "road_hazard"
    ]

    # RDD2022 exports descriptive labels while older checkpoints may use D00-D40.
    # Normalize both formats before the platform filters and stores detections.
    CLASS_ALIASES = {
        "D00": "crack",
        "D10": "crack",
        "D20": "crack",
        "D40": "pothole",
        "longitudinal_crack": "crack",
        "transverse_crack": "crack",
        "alligator_crack": "crack",
        "other_corruption": "damaged_road",
    }

    def __init__(self, confidence_threshold: float = 0.5, model_path: Optional[str] = None):
        self.confidence_threshold = confidence_threshold
        self.model_path = model_path
        self.is_model_loaded = False
        self._init_model()

    def _init_model(self):
        """Attempt to load YOLO/PyTorch weights if available, else use fallback."""
        if self.model_path:
            try:
                import torch
                # If ultralytics is available, load it
                from ultralytics import YOLO
                self.model = YOLO(self.model_path)
                self.is_model_loaded = True
            except Exception:
                self.is_model_loaded = False
        else:
            self.is_model_loaded = False

    def process_frame(
        self,
        frame_array: Optional[Any],
        camera_id: str,
        gps_lat: float,
        gps_lng: float,
        speed_kmh: float = 30.0
    ) -> List[DefectDetection]:
        """
        Analyze a single camera frame for road defects.
        Returns list of DefectDetection objects passing confidence threshold.
        """
        if self.is_model_loaded and frame_array is not None:
            return self._infer_neural(frame_array)
        else:
            return self._heuristic_fallback(frame_array, gps_lat, gps_lng)

    def _infer_neural(self, frame_array: Any) -> List[DefectDetection]:
        """Inference using loaded deep learning weights."""
        detections = []
        try:
            results = self.model(frame_array, conf=self.confidence_threshold, verbose=False)
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    defect_name = self.model.names.get(cls_id, "road_hazard")
                    defect_name = self.CLASS_ALIASES.get(defect_name, defect_name)
                    if defect_name not in self.DEFECT_TYPES:
                        continue
                    coords = box.xyxyn[0].tolist()
                    severity = self._compute_severity(defect_name, conf, coords)
                    area = self._estimate_area(coords)
                    reasons = self._generate_reasons(defect_name, conf, area, severity)

                    detections.append(DefectDetection(
                        detection_id=f"det_{uuid.uuid4().hex[:8]}",
                        defect_type=defect_name,
                        severity=severity,
                        confidence=round(conf, 3),
                        bbox=[coords[1], coords[0], coords[3], coords[2]],
                        area_sq_meters=round(area, 2),
                        explainability=reasons
                    ))
        except Exception:
            pass
        return detections

    def _heuristic_fallback(
        self,
        frame_array: Optional[Any],
        lat: float,
        lng: float
    ) -> List[DefectDetection]:
        """
        Computer vision heuristic based on pixel contrast / texture analysis
        or synthetic simulation for pipeline verification.
        """
        detections = []
        # If real frame array is provided, apply edge & dark patch detection
        if frame_array is not None:
            try:
                import cv2
                import numpy as np
                gray = cv2.cvtColor(frame_array, cv2.COLOR_BGR2GRAY)
                h, w = gray.shape
                # Focus on lower half (road surface)
                roi = gray[int(h * 0.5):, :]
                blur = cv2.GaussianBlur(roi, (7, 7), 0)
                # Potholes typically appear as dark elliptical depressions surrounded by high gradient
                thresh = cv2.adaptiveThreshold(
                    blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 4
                )
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if 500 < area < 20000:
                        x, y, cw, ch = cv2.boundingRect(cnt)
                        aspect_ratio = float(cw) / max(ch, 1)
                        if 0.5 < aspect_ratio < 2.5:
                            conf = min(0.92, 0.65 + (area / 30000.0))
                            real_y = (y + int(h * 0.5)) / h
                            real_x = x / w
                            real_h = ch / h
                            real_w = cw / w
                            det = DefectDetection(
                                detection_id=f"cv_{uuid.uuid4().hex[:8]}",
                                defect_type="pothole",
                                severity="high" if area > 5000 else "medium",
                                confidence=0.0,
                                metadata={"method": "opencv_heuristic", "confidence_calibrated": False, "heuristic_score": round(conf, 2)},
                                bbox=[real_y, real_x, real_y + real_h, real_x + real_w],
                                area_sq_meters=round(area * 0.0001, 2),
                                explainability=[
                                    f"High-contrast depression contour detected on road plane",
                                    f"Estimated surface disruption area: {round(area * 0.0001, 2)} m²",
                                    "Uncalibrated visual candidate; manual review required"
                                ]
                            )
                            detections.append(det)
                            if len(detections) >= 3:
                                break
            except Exception:
                pass
        return detections

    @staticmethod
    def _compute_severity(defect_type: str, confidence: float, bbox: List[float]) -> str:
        """Determines severity from type, confidence, and relative visual size."""
        height = bbox[3] - bbox[1] if len(bbox) >= 4 else 0.1
        width = bbox[2] - bbox[0] if len(bbox) >= 4 else 0.1
        visual_area = height * width

        if defect_type in ["waterlogging", "damaged_divider", "missing_sign"] or visual_area > 0.15:
            return "critical" if confidence > 0.8 else "high"
        elif defect_type in ["pothole", "damaged_road"] or visual_area > 0.05:
            return "high" if confidence > 0.75 else "medium"
        elif defect_type in ["crack", "debris", "missing_zebra"]:
            return "medium"
        return "low"

    @staticmethod
    def _estimate_area(bbox: List[float]) -> float:
        """Approximates real world square meters assuming road plane geometry."""
        h = max(0.01, bbox[3] - bbox[1]) if len(bbox) >= 4 else 0.1
        w = max(0.01, bbox[2] - bbox[0]) if len(bbox) >= 4 else 0.1
        # Edge perspective projection heuristic: 1x1 normalized bounding box at road center ≈ 8m²
        return round(h * w * 8.0, 2)

    @staticmethod
    def _generate_reasons(defect_type: str, confidence: float, area: float, severity: str) -> List[str]:
        """Produces explainable AI justification without hallucinations."""
        name_clean = defect_type.replace("_", " ").title()
        return [
            f"Identified {name_clean} with {int(confidence * 100)}% model confidence",
            f"Assessed severity: {severity.upper()} based on road plane dimension ({area} m²)",
            f"Single-frame detection; temporal confirmation has not been performed"
        ]
