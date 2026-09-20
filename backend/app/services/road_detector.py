from pathlib import Path
from io import BytesIO

import numpy as np
from PIL import Image, UnidentifiedImageError

try:
    from ultralytics import YOLO
except ImportError:  # Optional: edge nodes normally perform GPU inference.
    YOLO = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = PROJECT_ROOT / "frontend" / "ml" / "weights" / "road_defect_best.pt"

_model = None


def get_model():
    global _model

    if YOLO is None:
        raise RuntimeError(
            "Backend AI detection is not installed. Use the edge inference "
            "pipeline, or install the optional ultralytics dependency."
        )

    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

        _model = YOLO(str(MODEL_PATH))

    return _model


def detect_road_defects(raw: bytes, confidence: float = 0.25):
    try:
        with Image.open(BytesIO(raw)) as image:
            image.load()
            image = image.convert("RGB")
            frame = np.array(image)
    except (UnidentifiedImageError, OSError):
        raise ValueError("Invalid image")

    model = get_model()

    results = model.predict(
        source=frame,
        conf=confidence,
        verbose=False,
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
