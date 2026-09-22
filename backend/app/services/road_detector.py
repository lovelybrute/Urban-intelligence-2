from pathlib import Path
from io import BytesIO
import os
import threading
import time

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    import cv2
except ImportError:  # pragma: no cover - OpenCV is optional in some edge installs.
    cv2 = None

try:
    import torch
    from ultralytics import YOLO
except ImportError:  # Optional: edge nodes normally perform GPU inference.
    torch = None
    YOLO = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PT_MODEL_PATH = PROJECT_ROOT / "frontend" / "ml" / "weights" / "road_defect_best.pt"
ONNX_MODEL_PATH = PROJECT_ROOT / "frontend" / "ml" / "weights" / "road_defect_best.onnx"
PRETRAINED_POTHOLE_MODEL_PATHS = [
    PROJECT_ROOT / "frontend" / "ml" / "weights" / "candidates" / "vinothvikas1987_road_distress_yolov8_best.pt",
    PROJECT_ROOT / "frontend" / "ml" / "weights" / "candidates" / "peterhdd_pothole_yolov8_best.pt",
]
# Prefer the validated PyTorch checkpoint in cloud deployment. The current ONNX
# export is incompatible with Render's ONNX Runtime graph support (Split
# num_outputs), so ONNX remains opt-in until a compatible export is validated.
USE_ONNX = os.getenv("ROAD_AI_USE_ONNX", "0").strip().lower() in {"1", "true", "yes"}
MODEL_PATH = ONNX_MODEL_PATH if USE_ONNX and ONNX_MODEL_PATH.exists() else PT_MODEL_PATH

_model = None
_pretrained_pothole_model = None
_pretrained_pothole_model_path = None
_inference_lock = threading.Lock()
_model_load_ms = None
_model_warmup_ms = None
# Benchmarking on RDD-style pothole images showed 640px materially improves
# pothole box recall versus 320px while keeping warm CPU inference practical.
INFERENCE_SIZE = int(os.getenv("ROAD_AI_IMGSZ", "512"))
PREPROCESS_MAX_SIDE = int(os.getenv("ROAD_AI_MAX_SIDE", "1024"))
ROAD_NMS_IOU = float(os.getenv("ROAD_AI_NMS_IOU", "0.70"))
ROAD_POTHOLE_MIN_CONFIDENCE = float(os.getenv("ROAD_AI_POTHOLE_MIN_CONF", "0.12"))
USE_PRETRAINED_POTHOLE_MODEL = os.getenv("ROAD_AI_USE_PRETRAINED_POTHOLE", "0").strip().lower() in {"1", "true", "yes"}
USE_TILED_INFERENCE = os.getenv("ROAD_AI_TILED", "1").strip().lower() in {"1", "true", "yes"}
TILE_TRIGGER_SIDE = int(os.getenv("ROAD_AI_TILE_TRIGGER_SIDE", "900"))
TILE_SIZE = int(os.getenv("ROAD_AI_TILE_SIZE", "512"))
TILE_OVERLAP = float(os.getenv("ROAD_AI_TILE_OVERLAP", "0.18"))


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


def get_pretrained_pothole_model():
    global _pretrained_pothole_model, _pretrained_pothole_model_path
    if YOLO is None:
        return None
    if _pretrained_pothole_model is not None:
        return _pretrained_pothole_model
    for candidate in PRETRAINED_POTHOLE_MODEL_PATHS:
        if candidate.exists():
            _pretrained_pothole_model_path = candidate
            _pretrained_pothole_model = YOLO(str(candidate))
            return _pretrained_pothole_model
    return None


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


def _collect_road_model_detections(frame, scale_x, scale_y, confidence):
    model = get_model()
    inference_confidence = confidence
    try:
        with _inference_lock:
            results = model.predict(
                source=frame,
                conf=inference_confidence,
                verbose=False,
                imgsz=INFERENCE_SIZE,
                iou=ROAD_NMS_IOU,
                max_det=200,
                device="cpu",
            )
    except Exception:
        if PT_MODEL_PATH.exists() and MODEL_PATH != PT_MODEL_PATH:
            MODEL_PATH = PT_MODEL_PATH
            _model = YOLO(str(PT_MODEL_PATH))
            with _inference_lock:
                results = _model.predict(
                    source=frame,
                        conf=inference_confidence,
                    verbose=False,
                    imgsz=INFERENCE_SIZE,
                        iou=ROAD_NMS_IOU,
                        max_det=200,
                    device="cpu",
                )
        else:
            raise

    detections = []
    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            class_name = str(result.names.get(class_id, "")).strip()
            score = float(box.conf[0].item())
            if score < confidence:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": round(score, 4),
                    "bbox": {
                        "x1": round(float(x1) * scale_x, 2),
                        "y1": round(float(y1) * scale_y, 2),
                        "x2": round(float(x2) * scale_x, 2),
                        "y2": round(float(y2) * scale_y, 2),
                    },
                }
            )
    return detections


def _collect_pothole_detections(frame, scale_x, scale_y, confidence):
    if not USE_PRETRAINED_POTHOLE_MODEL:
        return []
    candidate_model = get_pretrained_pothole_model()
    if candidate_model is None:
        return []
    try:
        with _inference_lock:
            results = candidate_model.predict(
                source=frame,
                conf=confidence,
                verbose=False,
                imgsz=INFERENCE_SIZE,
                device="cpu",
            )
    except Exception:
        return []

    detections = []
    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            name = str(result.names.get(class_id, "")).strip()
            if "pothole" not in name.lower():
                continue
            score = float(box.conf[0].item())
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": "pothole",
                    "confidence": round(score, 4),
                    "bbox": {
                        "x1": round(float(x1) * scale_x, 2),
                        "y1": round(float(y1) * scale_y, 2),
                        "x2": round(float(x2) * scale_x, 2),
                        "y2": round(float(y2) * scale_y, 2),
                    },
                    "detection_method": "PRETRAINED-POTHOLE MODEL",
                }
            )
    return _nms_by_class(detections, ROAD_NMS_IOU)


def _collect_tiled_detections(image_rgb, original_width, original_height, confidence):
    """Sequential tiled inference for small/multiple defects without RAM spikes."""
    if not USE_TILED_INFERENCE:
        return []
    width, height = image_rgb.size
    if max(width, height) < TILE_TRIGGER_SIDE:
        return []

    tile = max(256, min(TILE_SIZE, width, height))
    overlap = max(0.0, min(0.40, TILE_OVERLAP))
    step = max(64, int(tile * (1.0 - overlap)))
    xs = list(range(0, max(1, width - tile + 1), step))
    ys = list(range(0, max(1, height - tile + 1), step))
    if not xs or xs[-1] != max(0, width - tile):
        xs.append(max(0, width - tile))
    if not ys or ys[-1] != max(0, height - tile):
        ys.append(max(0, height - tile))

    detections = []
    for y in ys:
        for x in xs:
            crop = image_rgb.crop((x, y, x + tile, y + tile))
            frame = np.asarray(crop)
            crop.close()
            local = _collect_road_model_detections(frame, 1.0, 1.0, confidence)
            for det in local:
                box = det["bbox"]
                box["x1"] = round((box["x1"] + x) * original_width / width, 2)
                box["x2"] = round((box["x2"] + x) * original_width / width, 2)
                box["y1"] = round((box["y1"] + y) * original_height / height, 2)
                box["y2"] = round((box["y2"] + y) * original_height / height, 2)
                det["detection_method"] = det.get("detection_method", "CUSTOM YOLO") + " / TILED"
                detections.append(det)
            del frame, local

    return _nms_by_class(detections, ROAD_NMS_IOU)


def detect_road_defects(raw: bytes, confidence: float = 0.12):
    global MODEL_PATH, _model
    request_started = time.perf_counter()
    decode_started = request_started
    try:
        with Image.open(BytesIO(raw)) as image:
            image.load()
            image = ImageOps.exif_transpose(image).convert("RGB")
            original_width, original_height = image.size
            decoded_image = image.copy()\n            image.close()
    except (UnidentifiedImageError, OSError):
        raise ValueError("Invalid image")

    decode_ms = (time.perf_counter() - decode_started) * 1000
    preprocess_started = time.perf_counter()
    # Bound input size before NumPy conversion to reduce RAM/CPU pressure.
    decoded_image.thumbnail((INFERENCE_SIZE, INFERENCE_SIZE))
    tile_image.thumbnail((PREPROCESS_MAX_SIDE, PREPROCESS_MAX_SIDE))
    inference_width, inference_height = decoded_image.size
    scale_x = original_width / inference_width
    scale_y = original_height / inference_height
    frame = np.asarray(decoded_image)\n    decoded_image.close()
    preprocess_ms = (time.perf_counter() - preprocess_started) * 1000
    model_started = time.perf_counter()
    model = get_model()
    model_ready_ms = (time.perf_counter() - model_started) * 1000

    # Serialize inference on tiny CPU instances so concurrent scans do not
    # exhaust CPU/RAM or invoke the same model object concurrently.
    inference_started = time.perf_counter()
    detections = _collect_road_model_detections(frame, scale_x, scale_y, confidence)
    tiled_detections = _collect_tiled_detections(
        tile_image, original_width, original_height, confidence
    )
    tile_image.close()
    if tiled_detections:
        detections.extend(tiled_detections)
    pothole_detections = _collect_pothole_detections(frame, scale_x, scale_y, confidence)
    if pothole_detections:
        detections.extend(pothole_detections)
    detections = _nms_by_class(detections, ROAD_NMS_IOU)
    inference_ms = (time.perf_counter() - inference_started) * 1000

    # Waterlogging currently has a lightweight CV fallback because the road
    # checkpoint may not contain a trained waterlogging class. Keep it clearly
    # marked as heuristic so its score is never confused with YOLO confidence.
    postprocess_started = time.perf_counter()
    waterlogging_started = time.perf_counter()
    model_has_waterlogging = any(d["class_name"].lower() == "waterlogging" for d in detections)
    if not model_has_waterlogging:
        detections.extend(_detect_waterlogging(frame, scale_x, scale_y))
        detections = _nms_by_class(detections, ROAD_NMS_IOU)
    waterlogging_ms = (time.perf_counter() - waterlogging_started) * 1000
    postprocess_ms = (time.perf_counter() - postprocess_started) * 1000

    total_ms = (time.perf_counter() - request_started) * 1000
    timing = {
        "image_decode_ms": round(decode_ms, 2),
        "preprocess_ms": round(preprocess_ms, 2),
        "model_load_ms": round(model_ready_ms, 2),
        "model_ready_ms": round(model_ready_ms, 2),
        "inference_ms": round(inference_ms, 2),
        "waterlogging_ms": round(waterlogging_ms, 2),
        "postprocess_ms": round(postprocess_ms, 2),
        "total_ms": round(total_ms, 2),
    }
    return detections, timing


def _box_iou(a, b):
    ax1, ay1, ax2, ay2 = a["bbox"]["x1"], a["bbox"]["y1"], a["bbox"]["x2"], a["bbox"]["y2"]
    bx1, by1, bx2, by2 = b["bbox"]["x1"], b["bbox"]["y1"], b["bbox"]["x2"], b["bbox"]["y2"]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter <= 0:
        return 0.0
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    return inter / max(1e-6, area_a + area_b - inter)


def _nms_by_class(detections, threshold):
    kept = []
    for class_name in sorted({d["class_name"] for d in detections}):
        class_dets = sorted(
            [d for d in detections if d["class_name"] == class_name],
            key=lambda item: item["confidence"],
            reverse=True,
        )
        while class_dets:
            best = class_dets.pop(0)
            kept.append(best)
            class_dets = [d for d in class_dets if _box_iou(best, d) < threshold]
    return sorted(kept, key=lambda item: item["confidence"], reverse=True)


def _detect_waterlogging(frame_rgb, scale_x, scale_y):
    if cv2 is None:
        return []
    height, width = frame_rgb.shape[:2]
    if height < 40 or width < 40:
        return []

    bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lower_y = int(height * 0.25)
    roi = hsv[lower_y:, :]

    blue_gray_water = cv2.inRange(roi, (80, 10, 35), (135, 160, 245))
    muddy_water = cv2.inRange(roi, (5, 25, 35), (45, 255, 255))
    mask = cv2.morphologyEx(blue_gray_water | muddy_water, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detections = []
    image_area = max(1, height * width)
    for contour in contours:
        area = cv2.contourArea(contour)
        area_ratio = area / image_area
        if area_ratio < 0.12 or area_ratio > 0.55:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if w < 20 or h < 12:
            continue
        aspect = w / max(1, h)
        if aspect < 1.3:
            continue
        y += lower_y
        center_y = y + h / 2
        if center_y < height * 0.35 or center_y > height * 0.88:
            continue
        crop = hsv[y : y + h, x : x + w]
        saturation = float(np.median(crop[:, :, 1])) if crop.size else 255.0
        hue = float(np.median(crop[:, :, 0])) if crop.size else 180.0
        is_muddy = 5 <= hue <= 45
        if not is_muddy and saturation > 140:
            continue
        confidence = min(0.72, 0.35 + area_ratio * 6)
        detections.append(
            {
                "class_id": 5,
                "class_name": "waterlogging",
                "confidence": round(float(confidence), 4),
                "bbox": {
                    "x1": round(float(x) * scale_x, 2),
                    "y1": round(float(y) * scale_y, 2),
                    "x2": round(float(x + w) * scale_x, 2),
                    "y2": round(float(y + h) * scale_y, 2),
                },
                "detection_method": "COMPUTER-VISION PROTOTYPE",
                "requires_manual_verification": True,
            }
        )
    return _nms_by_class(detections, 0.30)


def road_model_health():
    """Lightweight readiness check that does not load the model into memory."""
    return {
        "road_model_ready": MODEL_PATH.exists(),
        "weight": MODEL_PATH.name,
        "ultralytics_ready": YOLO is not None,
        "engine": "onnxruntime" if MODEL_PATH.suffix == ".onnx" else "pytorch",
        "inference_size": INFERENCE_SIZE,
        "preprocess_max_side": PREPROCESS_MAX_SIDE,
        "device": "cpu",
        "model_load_ms": _model_load_ms,
        "model_warmup_ms": _model_warmup_ms,
    }
