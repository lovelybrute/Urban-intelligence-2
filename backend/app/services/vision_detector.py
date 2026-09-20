from io import BytesIO
from pathlib import Path
import os

import numpy as np
from PIL import Image, UnidentifiedImageError

try:
    import torch
    from ultralytics import YOLO
except ImportError:
    torch = None
    YOLO = None

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_WEIGHTS = Path(__file__).resolve().parents[2] / "ml" / "weights"
REPO_WEIGHTS = REPO_ROOT / "frontend" / "ml" / "weights"

def _weight(name: str) -> Path:
    local = BACKEND_WEIGHTS / name
    repo = REPO_WEIGHTS / name
    return local if local.exists() else repo
_traffic = None
INFERENCE_SIZE = int(os.getenv("TRAFFIC_AI_IMGSZ", "320"))

VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "bicycle", "auto_rickshaw", "emergency"}
PERSON_CLASS = "person"

def _load_traffic():
    global _traffic
    if YOLO is None:
        raise RuntimeError("Ultralytics is not installed")
    if _traffic is None:
        if torch is not None:
            torch.set_num_threads(max(1, int(os.getenv("TORCH_NUM_THREADS", "1"))))
        custom = _weight("traffic_india.pt")
        local = _weight("traffic_coco.pt")
        # YOLO11n is an official pretrained fallback, not a custom-trained model.
        source = str(custom if custom.exists() else local) if (custom.exists() or local.exists()) else "yolo11n.pt"
        _traffic = YOLO(source)
    return _traffic

def model_health():
    road = _weight("road_defect_best.pt")
    return {
        "road_defect": {"ready": road.exists(), "weight": road.name, "custom_trained": road.exists()},
        "traffic_person": {"ready": YOLO is not None, "weight": "traffic_india.pt if present, otherwise official pretrained YOLO11n", "custom_trained": _weight("traffic_india.pt").exists()},
        "tracking": {"ready": YOLO is not None, "engine": "ByteTrack via Ultralytics", "custom_trained": False},
        "anpr": {"ready": _weight("anpr_plate.pt").exists(), "weight": "anpr_plate.pt", "custom_trained": _weight("anpr_plate.pt").exists()},
        "infrastructure": {"ready": _weight("infrastructure.pt").exists(), "weight": "infrastructure.pt", "custom_trained": _weight("infrastructure.pt").exists()},
        "event_logic": {"ready": True, "note": "Temporal rules require video/track history; still-image endpoint reports observable risk inputs only"},
    }

def detect_scene(raw: bytes, confidence: float = 0.25):
    try:
        with Image.open(BytesIO(raw)) as image:
            image.load()
            image = image.convert("RGB")
            image.thumbnail((640, 640))
            frame = np.array(image)
    except (UnidentifiedImageError, OSError):
        raise ValueError("Invalid image")

    model = _load_traffic()
    results = model.predict(source=frame, conf=confidence, verbose=False, imgsz=INFERENCE_SIZE, device="cpu")
    detections = []
    counts = {}
    people = 0
    vehicles = 0
    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            cid = int(box.cls[0].item())
            name = str(result.names[cid])
            if name not in VEHICLE_CLASSES and name != PERSON_CLASS:
                continue
            score = float(box.conf[0].item())
            x1,y1,x2,y2 = [round(float(v),2) for v in box.xyxy[0].tolist()]
            detections.append({"class_id":cid,"class_name":name,"confidence":round(score,4),"bbox":{"x1":x1,"y1":y1,"x2":x2,"y2":y2}})
            counts[name] = counts.get(name, 0) + 1
            people += int(name == PERSON_CLASS)
            vehicles += int(name in VEHICLE_CLASSES)
    # Density is an explicit observable proxy for the still-image endpoint.
    density = "high" if vehicles >= 12 else "medium" if vehicles >= 6 else "low"
    return {"model":"traffic_india.pt" if _weight("traffic_india.pt").exists() else "official-pretrained-yolo11n","custom_trained":(WEIGHTS/"traffic_india.pt").exists(),"vehicle_count":vehicles,"pedestrian_count":people,"density_level":density,"class_counts":counts,"detection_count":len(detections),"detections":detections}
