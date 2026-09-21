"""Prototype ANPR service using the existing edge processor without fabricated plate text."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import numpy as np
from PIL import Image,UnidentifiedImageError
import importlib.util

EDGE_ANPR = ROOT / "edge" / "processors" / "anpr.py"
_spec = importlib.util.spec_from_file_location("urban_edge_anpr", EDGE_ANPR)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load ANPR processor from {EDGE_ANPR}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
ANPRProcessor = _mod.ANPRProcessor

ROOT=Path(__file__).resolve().parents[3]
WEIGHTS=ROOT/"frontend"/"ml"/"weights"/"anpr_plate.pt"
_processor=None

def get_processor():
    global _processor
    if _processor is None:
        _processor=ANPRProcessor(model_path=str(WEIGHTS) if WEIGHTS.is_file() else None)
    return _processor

def recognize_plate(raw:bytes):
    try:
        with Image.open(BytesIO(raw)) as im:
            frame=np.array(im.convert("RGB"))[:,:,::-1].copy()
    except (UnidentifiedImageError,OSError):
        raise ValueError("Invalid image")
    result=get_processor().process_vehicle_crop(0,frame)
    return {
        "plate_number":result.plate_number,"raw_ocr_text":result.raw_ocr_text,
        "plate_detection_confidence":result.plate_detection_confidence,
        "ocr_confidence":result.ocr_confidence,"overall_confidence":result.overall_confidence,
        "is_format_valid":result.is_format_valid,
        "requires_manual_verification":result.requires_manual_verification,
        "timestamp":result.timestamp,
        "mode":"trained_plate_detector" if WEIGHTS.is_file() else "ocr_prototype_no_plate_detector",
        "warning":None if WEIGHTS.is_file() else "Custom plate-localizer weights are not trained yet; OCR result must be manually verified."
    }
