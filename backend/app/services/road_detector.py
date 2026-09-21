from pathlib import Path
from io import BytesIO
import os
import threading
import time

import numpy as np
from PIL import Image, UnidentifiedImageError

try:
    import torch
    from ultralytics import YOLO
except ImportError:  # Optional: edge nodes normally perform GPU inference.
    torch = None
    YOLO = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PT_MODEL_PATH = PROJECT_ROOT / "frontend" / "ml" / "weights" / "road_defect_best.pt"
ONNX_MODEL_PATH = PROJECT_ROOT / "frontend" / "ml" / "weights" / "road_defect_best.onnx"
# Prefer the validated PyTorch checkpoint in cloud deployment. The current ONNX
# export is incompatible with Render's ONNX Runtime graph support (Split
# num_outputs), so ONNX remains opt-in until a compatible export is validated.
USE_ONNX = os.getenv("ROAD_AI_USE_ONNX", "0").strip().lower() in {"1", "true", "yes"}
MODEL_PATH = ONNX_MODEL_PATH if USE_ONNX and ONNX_MODEL_PATH.exists() else PT_MODEL_PATH

_model = None
_inference_lock = threading.Lock()
_model_load_ms = None
_model_warmup_ms = None
# The exported ONNX model uses a fixed 320px input. This preserves substantially
# more small-road detail than the previous 160px deployment.
INFERENCE_SIZE = int(os.getenv("ROAD_AI_IMGSZ", "320"))


def get_model():
    global _model, _model_load_ms, MODEL_PATH

    if YOLO is None:
        raise RuntimeError(
            "Backend AI detection is not installed. Use the edge inference "
            "pipeline, or install the optional ultralytics dependency."
        )

    if _model is None:
        if torch is not None:
            torch.set_num_threads(max(1, int(os.getenv("TORCH_NUM_THREADS", "1"))))
        if not MODEL_PATH.exists() and not PT_MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

        load_started = time.perf_counter()
        try:
            _model = YOLO(str(MODEL_PATH))
        except Exception:
            if PT_MODEL_PATH.exists() and MODEL_PATH != PT_MODEL_PATH:
                MODEL_PATH = PT_MODEL_PATH
                _model = YOLO(str(PT_MODEL_PATH))
            else:
                raise
        _model_load_ms = round((time.perf_counter() - load_started) * 1000, 2)

    return _model


def warm_road_model():
    """Initialize the inference backend and run one synthetic frame at startup."""
    global _model_warmup_ms, MODEL_PATH, _model
    model = get_model()
    if _model_warmup_ms is None:
        started = time.perf_counter()
        frame = np.zeros((INFERENCE_SIZE, INFERENCE_SIZE, 3), dtype=np.uint8)
        try:
            with _inference_lock:
                model.predict(
                    source=frame,
                    conf=0.18,
                    verbose=False,
                    imgsz=INFERENCE_SIZE,
                    device="cpu",
                )
        except Exception:
            if PT_MODEL_PATH.exists() and MODEL_PATH != PT_MODEL_PATH:
                MODEL_PATH = PT_MODEL_PATH
                _model = YOLO(str(PT_MODEL_PATH))
                with _inference_lock:
                    _model.predict(
                        source=frame,
                        conf=0.18,
                        verbose=False,
                        imgsz=INFERENCE_SIZE,
                        device="cpu",
                    )
                model = _model
            else:
                raise
        _model_warmup_ms = round((time.perf_counter() - started) * 1000, 2)
    return model


def detect_road_defects(raw: bytes, confidence: float = 0.18):
    global MODEL_PATH, _model
    request_started = time.perf_counter()
    preprocess_started = request_started
    try:
        with Image.open(BytesIO(raw)) as image:
            image.load()
            image = image.convert("RGB")
            original_width, original_height = image.size
            # Bound input size before NumPy conversion to reduce RAM/CPU pressure.
            image.thumbnail((640, 640))
            inference_width, inference_height = image.size
            scale_x = original_width / inference_width
            scale_y = original_height / inference_height
            frame = np.array(image)
    except (UnidentifiedImageError, OSError):
        raise ValueError("Invalid image")

    preprocess_ms = (time.perf_counter() - preprocess_started) * 1000
    model_started = time.perf_counter()
    model = get_model()
    model_ready_ms = (time.perf_counter() - model_started) * 1000

    # Serialize inference on tiny CPU instances so concurrent scans do not
    # exhaust CPU/RAM or invoke the same model object concurrently.
    inference_started = time.perf_counter()
    try:
        with _inference_lock:
            results = model.predict(
                source=frame,
                conf=confidence,
                verbose=False,
                imgsz=INFERENCE_SIZE,
                device="cpu",
            )
    except Exception:
        if PT_MODEL_PATH.exists() and MODEL_PATH != PT_MODEL_PATH:
            MODEL_PATH = PT_MODEL_PATH
            _model = YOLO(str(PT_MODEL_PATH))
            with _inference_lock:
                results = _model.predict(
                    source=frame,
                    conf=confidence,
                    verbose=False,
                    imgsz=INFERENCE_SIZE,
                    device="cpu",
                )
        else:
            raise
    inference_ms = (time.perf_counter() - inference_started) * 1000

    detections = []

    for result in results:
        if result.boxes is None:
            continue

        for box in result.boxes:
            class_id = int(box.cls[0].item())
            score = float(box.conf[0].item())

            x1, y1, x2, y2 = box.xyxy[0].tolist()
            x1 = round(float(x1) * scale_x, 2)
            y1 = round(float(y1) * scale_y, 2)
            x2 = round(float(x2) * scale_x, 2)
            y2 = round(float(y2) * scale_y, 2)

            detections.append(
                {
                    "class_id": class_id,
                    "class_name": result.names[class_id],
                    "confidence": round(score, 4),
                    "bbox": {
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                    },
                }
            )

    total_ms = (time.perf_counter() - request_started) * 1000
    timing = {
        "preprocess_ms": round(preprocess_ms, 2),
        "model_ready_ms": round(model_ready_ms, 2),
        "inference_ms": round(inference_ms, 2),
        "total_ms": round(total_ms, 2),
    }
    return detections, timing


def road_model_health():
    """Lightweight readiness check that does not load the model into memory."""
    return {
        "road_model_ready": MODEL_PATH.exists(),
        "weight": MODEL_PATH.name,
        "ultralytics_ready": YOLO is not None,
        "engine": "onnxruntime" if MODEL_PATH.suffix == ".onnx" else "pytorch",
        "inference_size": INFERENCE_SIZE,
        "device": "cpu",
        "model_load_ms": _model_load_ms,
        "model_warmup_ms": _model_warmup_ms,
    }
