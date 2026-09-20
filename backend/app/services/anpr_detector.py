"""Indian ANPR: plate localization + OCR + format validation.

A custom plate detector is used only when anpr_plate.pt exists. OCR confidence
and syntax validity are returned separately; the API never fabricates a plate.
"""
from io import BytesIO
from pathlib import Path
import re
import numpy as np
from PIL import Image, UnidentifiedImageError

try:
    from ultralytics import YOLO
except ImportError:
    YOLO=None
try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR=None

REPO_ROOT=Path(__file__).resolve().parents[3]
BACKEND_WEIGHT=Path(__file__).resolve().parents[2]/"ml"/"weights"/"anpr_plate.pt"
REPO_WEIGHT=REPO_ROOT/"frontend"/"ml"/"weights"/"anpr_plate.pt"
WEIGHT=BACKEND_WEIGHT if BACKEND_WEIGHT.exists() else REPO_WEIGHT
_plate_model=None
_ocr=None
INDIAN_PLATE=re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$")

def _clean(text):
    return re.sub(r"[^A-Z0-9]","",text.upper())

def _get_ocr():
    global _ocr
    if PaddleOCR is None: raise RuntimeError("PaddleOCR is not installed")
    if _ocr is None: _ocr=PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    return _ocr

def _get_plate_model():
    global _plate_model
    if YOLO is None: raise RuntimeError("Ultralytics is not installed")
    if not WEIGHT.exists(): return None
    if _plate_model is None: _plate_model=YOLO(str(WEIGHT))
    return _plate_model

def _ocr_crop(crop):
    result=_get_ocr().ocr(crop, cls=True)
    candidates=[]
    for page in result or []:
        for row in page or []:
            if len(row)<2: continue
            text,score=row[1]
            cleaned=_clean(str(text))
            if cleaned:
                candidates.append((cleaned,float(score)))
    return max(candidates,key=lambda x:x[1]) if candidates else ("",0.0)

def recognize_plate(raw: bytes, confidence=.25):
    try:
        with Image.open(BytesIO(raw)) as im:
            im.load(); frame=np.array(im.convert("RGB"))
    except (UnidentifiedImageError,OSError):
        raise ValueError("Invalid image")

    model=_get_plate_model()
    if model is None:
        # OCR-only fallback is explicitly identified; it is useful for tight plate crops.
        text,score=_ocr_crop(frame)
        return {"detector":"not-trained","ocr":"PaddleOCR","plate":text or None,
                "ocr_confidence":round(score,4),"format_valid":bool(text and INDIAN_PLATE.fullmatch(text)),
                "custom_plate_model":False,
                "warning":"anpr_plate.pt is absent; OCR-only mode expects a cropped/close plate image."}

    plates=[]
    for result in model.predict(source=frame,conf=confidence,verbose=False):
        if result.boxes is None: continue
        h,w=frame.shape[:2]
        for box in result.boxes:
            x1,y1,x2,y2=[int(v) for v in box.xyxy[0].tolist()]
            x1,y1=max(0,x1),max(0,y1); x2,y2=min(w,x2),min(h,y2)
            if x2<=x1 or y2<=y1: continue
            text,ocr_score=_ocr_crop(frame[y1:y2,x1:x2])
            plates.append({"plate":text or None,"ocr_confidence":round(ocr_score,4),
                           "detector_confidence":round(float(box.conf[0].item()),4),
                           "format_valid":bool(text and INDIAN_PLATE.fullmatch(text)),
                           "bbox":{"x1":x1,"y1":y1,"x2":x2,"y2":y2}})
    return {"detector":"anpr_plate.pt","ocr":"PaddleOCR","custom_plate_model":True,
            "plate_count":len(plates),"plates":plates}
