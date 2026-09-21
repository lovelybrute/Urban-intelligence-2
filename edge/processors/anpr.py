"""
Urban Intelligence Platform - Edge ANPR Processor

Automatic Number Plate Recognition (ANPR) pipeline for incident-associated vehicles.
Includes plate localization, image enhancement, OCR extraction, Indian registration
format syntax validation, and confidence calibration.
"""
import re
import os
import shutil
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _configure_tesseract(pytesseract) -> bool:
    """Configure common Windows installs when tesseract.exe is absent from PATH."""
    candidates = [
        shutil.which("tesseract"),
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Tesseract-OCR" / "tesseract.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
    ]
    executable = next((Path(path) for path in candidates if path and Path(path).is_file()), None)
    if executable:
        pytesseract.pytesseract.tesseract_cmd = str(executable)
        return True
    return False


@dataclass
class PlateResult:
    """Represents the output of the ANPR pipeline."""
    plate_id: str
    vehicle_track_id: int
    plate_number: str  # Validated registration or "UNKNOWN"
    raw_ocr_text: str
    plate_detection_confidence: float
    ocr_confidence: float
    overall_confidence: float
    is_format_valid: bool
    is_low_confidence: bool
    requires_manual_verification: bool
    explainability: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ANPRProcessor:
    """
    Edge ANPR Processor for localized plate recognition.
    Strictly avoids fabricating or hallucinating numbers when OCR is low-confidence.
    """

    # Standard Indian Motor Vehicle Registration Format (e.g. TS09AB1234, DL01C5678, MH12DE1423, KA03MJ9988)
    # State (2 letters) + RTO Code (2 digits) + Optional Series (1-3 letters) + Registration Number (4 digits)
    INDIAN_PLATE_REGEX = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{4}$")

    # Common OCR character confusion maps for automotive number plates
    CHAR_CORRECTIONS = {
        "O": "0", "I": "1", "Z": "2", "S": "5", "B": "8", "G": "6", "Q": "0"
    }
    NUM_CORRECTIONS = {
        "0": "O", "1": "I", "2": "Z", "5": "S", "8": "B", "6": "G"
    }

    def __init__(self, min_confidence: float = 0.55, model_path: Optional[str] = None):
        self.min_confidence = min_confidence
        self.model = None
        if model_path:
            if not Path(model_path).is_file():
                raise FileNotFoundError(f"ANPR weights missing: {model_path}")
            from ultralytics import YOLO
            self.model = YOLO(model_path)

    def process_vehicle_crop(
        self,
        vehicle_track_id: int,
        vehicle_image_array: Optional[Any],
        simulated_plate_hint: Optional[str] = None
    ) -> PlateResult:
        """
        Executes full ANPR pipeline:
        Detection -> Crop -> Enhancement -> OCR -> Validation -> Confidence Calibration.
        """
        if vehicle_image_array is not None:
            raw_text, det_conf, ocr_conf = self._cv_ocr_pipeline(vehicle_image_array)
        elif simulated_plate_hint:
            raw_text = simulated_plate_hint
            det_conf = 0.93
            ocr_conf = 0.88
        else:
            raw_text = ""
            det_conf = 0.0
            ocr_conf = 0.0

        # Clean string: uppercase alphanumeric only
        cleaned_text = re.sub(r"[^A-Z0-9]", "", raw_text.upper())

        # Validate syntax against official Indian vehicle format
        is_valid = bool(self.INDIAN_PLATE_REGEX.match(cleaned_text))
        
        # Overall confidence is geometric mean of plate localization and character recognition
        overall_conf = round((det_conf * ocr_conf) ** 0.5, 3) if det_conf else round(ocr_conf, 3)

        # Guard against hallucination
        is_low_conf = det_conf <= 0 or overall_conf < self.min_confidence or len(cleaned_text) < 6
        final_plate_number = cleaned_text if (not is_low_conf and is_valid) else ("UNKNOWN" if is_low_conf else f"{cleaned_text} (UNVERIFIED)")
        requires_manual = is_low_conf or not is_valid or vehicle_image_array is not None

        explainability = [
            f"Plate region detected with {int(det_conf * 100)}% visual localization confidence",
            f"Character OCR text extraction score: {int(ocr_conf * 100)}%",
            f"Format Syntax Match: {'VALID (Indian Motor Vehicle Standard)' if is_valid else 'NON-STANDARD / IRREGULAR'}"
        ]
        if is_low_conf:
            explainability.append("LOW CONFIDENCE WARNING: OCR quality below safety threshold; plate marked UNKNOWN to prevent erroneous enforcement")
        if requires_manual:
            explainability.append("Flagged for manual operator verification in Command Center")

        return PlateResult(
            plate_id=f"plt_{uuid.uuid4().hex[:8]}",
            vehicle_track_id=vehicle_track_id,
            plate_number=final_plate_number,
            raw_ocr_text=cleaned_text,
            plate_detection_confidence=round(det_conf, 2),
            ocr_confidence=round(ocr_conf, 2),
            overall_confidence=overall_conf,
            is_format_valid=is_valid,
            is_low_confidence=is_low_conf,
            requires_manual_verification=requires_manual,
            explainability=explainability
        )

    def _cv_ocr_pipeline(self, frame_crop: Any) -> Tuple[str, float, float]:
        """Runs OpenCV enhancement and OCR if Tesseract / EasyOCR / PaddleOCR is installed."""
        try:
            import cv2
            import numpy as np
            plate_crop = frame_crop
            detection_confidence = 0.0
            if self.model is not None:
                results = self.model(frame_crop, conf=0.35, verbose=False)
                candidates = [box for result in results for box in result.boxes]
                if candidates:
                    best = max(candidates, key=lambda box: float(box.conf[0]))
                    x1, y1, x2, y2 = [int(value) for value in best.xyxy[0].tolist()]
                    height, width = frame_crop.shape[:2]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(width, x2), min(height, y2)
                    if x2 > x1 and y2 > y1:
                        plate_crop = frame_crop[y1:y2, x1:x2]
                        detection_confidence = float(best.conf[0])
            gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
            # Bilateral filter to remove noise while preserving edges
            denoised = cv2.bilateralFilter(gray, 11, 17, 17)
            # Adaptive threshold for high contrast plate characters
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            # Prefer EasyOCR in cloud deployments: unlike pytesseract it does not
            # require a separately installed Tesseract system executable.
            try:
                import easyocr
                if not hasattr(self, "_easyocr_reader"):
                    self._easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
                # Without trained plate-localizer weights, OCR the original crop
                # as well as the thresholded image. EasyOCR often performs better
                # on the original colour crop because it has its own detector.
                candidates = []
                for candidate in (plate_crop, thresh):
                    reads = self._easyocr_reader.readtext(
                        candidate, detail=1,
                        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                        paragraph=False,
                    )
                    if reads:
                        text = "".join(str(item[1]).strip() for item in reads)
                        confidence = sum(float(item[2]) for item in reads) / len(reads)
                        candidates.append((text, confidence))
                if candidates:
                    text, confidence = max(candidates, key=lambda item: item[1])
                    # EasyOCR's own text-region detection acts as the prototype
                    # localization signal when custom YOLO plate weights are absent.
                    if detection_confidence <= 0:
                        detection_confidence = confidence
                    return text, detection_confidence, confidence
            except Exception as exc:
                import logging
                logging.getLogger("uvicorn.error").exception("EasyOCR ANPR failed: %s", exc)

            # Local fallback when Tesseract happens to be installed.
            try:
                import pytesseract
                if _configure_tesseract(pytesseract):
                    data = pytesseract.image_to_data(thresh, config='--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', output_type=pytesseract.Output.DICT)
                    tokens = [(text.strip(), float(conf)) for text, conf in zip(data["text"], data["conf"]) if text.strip() and float(conf) >= 0]
                    text = "".join(t for t, _ in tokens)
                    confidence = sum(c for _, c in tokens) / (100 * len(tokens)) if tokens else 0.0
                    return text, detection_confidence, confidence
            except Exception:
                pass
        except Exception:
            pass
        return "", 0.0, 0.0
