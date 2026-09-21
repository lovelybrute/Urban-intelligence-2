"""ANPR service using the existing edge processor without fabricated plate text."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import numpy as np
from PIL import Image,UnidentifiedImageError
import importlib.util

SERVICE_FILE = Path(__file__).resolve()
ROOT = SERVICE_FILE.parents[3]
EDGE_ANPR = ROOT / "edge" / "processors" / "anpr.py"
_spec = importlib.util.spec_from_file_location("urban_edge_anpr", EDGE_ANPR)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load ANPR processor from {EDGE_ANPR}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
ANPRProcessor = _mod.ANPRProcessor

def _find_weight(filename: str) -> Path | None:
    """Find a repository weight without relying on the process working directory."""
    candidates = [parent / "frontend" / "ml" / "weights" / filename for parent in SERVICE_FILE.parents]
    candidates.append(Path.cwd() / "frontend" / "ml" / "weights" / filename)
    return next((candidate for candidate in candidates if candidate.is_file()), None)


WEIGHTS_PT = _find_weight("anpr_plate.pt")
WEIGHTS_ONNX = _find_weight("anpr_plate.onnx")
WEIGHTS = WEIGHTS_PT or WEIGHTS_ONNX
_processor = None
_processor_error = None

def get_processor():
    global _processor, _processor_error
    if _processor is None:
        try:
            _processor = ANPRProcessor(model_path=str(WEIGHTS) if WEIGHTS else None)
            if WEIGHTS and _processor.model is None:
                _processor_error = f"ANPR model failed to load from {WEIGHTS}"
            elif not WEIGHTS:
                _processor_error = "ANPR weight was not found in the repository"
        except Exception as exc:
            _processor_error = f"ANPR model load failed: {type(exc).__name__}"
            _processor = ANPRProcessor()
    return _processor


def anpr_model_health():
    processor = get_processor()
    return {
        "anpr_model_ready": bool(WEIGHTS and processor.model is not None),
        "anpr_weight": str(WEIGHTS) if WEIGHTS else None,
        "anpr_error": _processor_error,
    }

def recognize_plate(raw:bytes):
    try:
        with Image.open(BytesIO(raw)) as im:
            frame=np.array(im.convert("RGB"))[:,:,::-1].copy()
    except (UnidentifiedImageError,OSError):
        raise ValueError("Invalid image")
    result=get_processor().process_vehicle_crop(0,frame)
    has_plate_weights = bool(WEIGHTS and result is not None and get_processor().model is not None)
    return {
        "plate_number":result.plate_number,"raw_ocr_text":result.raw_ocr_text,
        "plate_detection_confidence":result.plate_detection_confidence,
        "ocr_confidence":result.ocr_confidence,"overall_confidence":result.overall_confidence,
        "is_format_valid":result.is_format_valid,
        "requires_manual_verification":result.requires_manual_verification,
        "timestamp":result.timestamp,
        "mode":"trained_plate_detector" if has_plate_weights else "ocr_prototype_no_plate_detector",
        "warning":None if has_plate_weights else "Custom plate-localizer weights are not trained yet; OCR result must be manually verified."
    }
