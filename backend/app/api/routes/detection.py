from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger
from starlette.concurrency import run_in_threadpool

from app.services.road_detector import detect_road_defects, road_model_health


router = APIRouter(prefix="/api/detect", tags=["AI Detection"])

MAX_FILE_SIZE = 5 * 1024 * 1024


@router.get("/health")
def detection_health():
    return road_model_health()


@router.post("/road")
async def detect_road(
    file: UploadFile = File(...),
    confidence: float = 0.18,
):
    if confidence < 0.01 or confidence > 1.0:
        raise HTTPException(
            status_code=400,
            detail="Confidence must be between 0.01 and 1.0",
        )

    raw = await file.read(MAX_FILE_SIZE + 1)
    await file.close()

    if not raw:
        raise HTTPException(
            status_code=400,
            detail="Empty file",
        )

    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds 5 MB",
        )

    try:
        # Road-model inference is CPU-heavy. Run it outside the async
        # event loop so health/docs/API requests stay responsive during inference.
        detections, timing = await run_in_threadpool(
            detect_road_defects,
            raw,
            confidence,
        )
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Upload a valid image",
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )
    except Exception:
        # Keep unexpected inference failures inside FastAPI's handled response
        # path. This preserves CORS headers, so the browser receives a useful
        # JSON error instead of reporting a misleading network failure.
        logger.exception("Road AI inference failed")
        raise HTTPException(
            status_code=500,
            detail="Road AI inference failed",
        )

    return {
        "model": road_model_health()["weight"],
        "detection_count": len(detections),
        "detections": detections,
        "timing": timing,
    }
