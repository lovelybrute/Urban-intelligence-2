"""Infrastructure inference for observable road assets/hazards.

Classes are learned by a custom YOLO model. "Missing" infrastructure is not
claimed from a single frame because absence requires mapped expectations or
temporal/geospatial context.
"""
from io import BytesIO
from pathlib import Path
import numpy as np
from PIL import Image, UnidentifiedImageError

try:
    from ultralytics import YOLO
except ImportError:
    YOLO=None

REPO_ROOT=Path(__file__).resolve().parents[3]
BACKEND_WEIGHT=Path(__file__).resolve().parents[2]/"ml"/"weights"/"infrastructure.pt"
REPO_WEIGHT=REPO_ROOT/"frontend"/"ml"/"weights"/"infrastructure.pt"
WEIGHT=BACKEND_WEIGHT if BACKEND_WEIGHT.exists() else REPO_WEIGHT
_model=None

def _get_model():
    global _model
    if YOLO is None: raise RuntimeError("Ultralytics is not installed")
    if not WEIGHT.exists():
        raise RuntimeError("Infrastructure model is not trained: infrastructure.pt is missing")
    if _model is None: _model=YOLO(str(WEIGHT))
    return _model

def detect_infrastructure(raw: bytes, confidence=.25):
    try:
        with Image.open(BytesIO(raw)) as im:
            im.load(); frame=np.array(im.convert("RGB"))
    except (UnidentifiedImageError,OSError):
        raise ValueError("Invalid image")
    detections=[]
    for result in _get_model().predict(source=frame,conf=confidence,verbose=False):
        if result.boxes is None: continue
        for box in result.boxes:
            cid=int(box.cls[0].item()); name=str(result.names[cid])
            x1,y1,x2,y2=[round(float(v),2) for v in box.xyxy[0].tolist()]
            detections.append({"class_id":cid,"class_name":name,
                "confidence":round(float(box.conf[0].item()),4),
                "bbox":{"x1":x1,"y1":y1,"x2":x2,"y2":y2}})
    return {"model":"infrastructure.pt","custom_trained":True,
            "detection_count":len(detections),"detections":detections,
            "note":"Missing zebra/divider/sign requires expected-asset map or repeated route observations."}
