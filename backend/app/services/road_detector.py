from pathlib import Path
from io import BytesIO
import os

import numpy as np
from PIL import Image, UnidentifiedImageError

try:
    import torch
    from ultralytics import YOLO
except ImportError:  # Optional: edge nodes normally perform GPU inference.
    torch = None
    YOLO = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = PROJECT_ROOT / "frontend" / "ml" / "weights" / "road_defect_best.pt"

_model = None
INFERENCE_SIZE = int(os.getenv("ROAD_AI_IMGSZ", "320"))


def get_model():
    global _model

    if YOLO is None:
        raise RuntimeError(
            "Backend AI detection is not installed. Use the edge inference "
            "pipeline, or install the optional ultralytics dependency."
        )

    if _model is None:
        if torch is not None:
            torch.set_num_threads(max(1, int(os.getenv("TORCH_NUM_THREADS", "1"))))
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

        _model = YOLO(str(MODEL_PATH))

    return _model


def detect_road_defects(raw: bytes, confidence: float = 0.25):
    try:
        with Image.open(BytesIO(raw)) as image:
            image.load()
            image = image.convert("RGB")
            # Bound input size before NumPy conversion to reduce RAM/CPU pressure.
            image.thumbnail((640, 640))
            frame = np.array(image)
    except (UnidentifiedImageError, OSError):
        raise ValueError("Invalid image")

    model = get_model()

    results = model.predict(
        source=frame,
        conf=confidence,
        verbose=False,
        imgsz=INFERENCE_SIZE,
        device="cpu",
    )

    detections = []

    for result in results:
        if result.boxes is None:
            continue

        for box in result.boxes:
            class_id = int(box.cls[0].item())
            score = float(box.conf[0].item())

            x1, y1, x2, y2 = [
                round(float(v), 2)
                for v in box.xyxy[0].tolist()
            ]

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

    return detections
