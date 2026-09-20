from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.road_detector import detect_road_defects
from app.services.vision_detector import detect_scene, model_health

router = APIRouter(prefix="/api/detect", tags=["AI Detection"])
MAX_FILE_SIZE = 5 * 1024 * 1024

async def _read_image(file: UploadFile) -> bytes:
    raw = await file.read(MAX_FILE_SIZE + 1)
    await file.close()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Image exceeds 5 MB")
    return raw

@router.get("/health")
def detection_health():
    return model_health()

@router.post("/road")
async def detect_road(file: UploadFile = File(...), confidence: float = 0.25):
    if confidence < 0.01 or confidence > 1.0:
        raise HTTPException(status_code=400, detail="Confidence must be between 0.01 and 1.0")
    raw = await _read_image(file)
    try:
        detections = detect_road_defects(raw, confidence=confidence)
    except ValueError:
        raise HTTPException(status_code=422, detail="Upload a valid image")
    except (FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"model":"road_defect_best.pt","detection_count":len(detections),"detections":detections}

@router.post("/scene")
async def detect_traffic_scene(file: UploadFile = File(...), confidence: float = 0.25):
    raw = await _read_image(file)
    try:
        return detect_scene(raw, confidence=confidence)
    except ValueError:
        raise HTTPException(status_code=422, detail="Upload a valid image")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
