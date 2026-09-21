from fastapi import APIRouter, File, HTTPException, UploadFile
from datetime import datetime, timezone
from loguru import logger
from starlette.concurrency import run_in_threadpool

from app.services.road_detector import detect_road_defects, road_model_health
from app.services.anpr_service import recognize_plate
from app.services.urban_vision import (
    analyze_infrastructure,
    analyze_safety,
    detect_traffic as detect_traffic_frame,
    detection_health as urban_detection_health,
)


router = APIRouter(prefix="/api/detect", tags=["AI Detection"])

MAX_FILE_SIZE = 5 * 1024 * 1024


@router.get("/health")
def detection_health():
    return {
        **road_model_health(),
        **urban_detection_health(),
    }


@router.post("/road")
async def detect_road(
    file: UploadFile = File(...),
    confidence: float = 0.10,
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gps": None,
        "requires_manual_verification": True,
        "status": "CUSTOM TRAINED / FIELD VALIDATION REQUIRED",
    }


@router.post("/anpr")
async def detect_anpr(file: UploadFile = File(...)):
    """Prototype ANPR endpoint. Never fabricates a plate when OCR is uncertain."""
    raw = await file.read(MAX_FILE_SIZE + 1)
    await file.close()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Image exceeds 5 MB")
    try:
        return await run_in_threadpool(recognize_plate, raw)
    except ValueError:
        raise HTTPException(status_code=422, detail="Upload a valid vehicle/plate image")
    except Exception:
        logger.exception("ANPR inference failed")
        raise HTTPException(status_code=500, detail="ANPR inference failed")


@router.post("/traffic")
async def detect_traffic(
    file: UploadFile = File(...),
    confidence: float = 0.25,
):
    if confidence < 0.01 or confidence > 1.0:
        raise HTTPException(status_code=400, detail="Confidence must be between 0.01 and 1.0")
    raw = await file.read(MAX_FILE_SIZE + 1)
    await file.close()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Image exceeds 5 MB")
    try:
        result = await run_in_threadpool(detect_traffic_frame, raw, confidence)
    except ValueError:
        raise HTTPException(status_code=422, detail="Upload a valid traffic image")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Traffic AI inference failed")
        raise HTTPException(status_code=500, detail="Traffic AI inference failed")
    return {
        **result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gps": None,
    }


@router.post("/infrastructure")
async def detect_infrastructure(file: UploadFile = File(...)):
    raw = await file.read(MAX_FILE_SIZE + 1)
    await file.close()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Image exceeds 5 MB")
    try:
        result = await run_in_threadpool(analyze_infrastructure, raw)
    except ValueError:
        raise HTTPException(status_code=422, detail="Upload a valid road/infrastructure image")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Infrastructure prototype inference failed")
        raise HTTPException(status_code=500, detail="Infrastructure prototype inference failed")
    return {
        **result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gps": None,
    }


@router.post("/safety")
async def detect_safety(
    file: UploadFile = File(...),
    confidence: float = 0.25,
):
    if confidence < 0.01 or confidence > 1.0:
        raise HTTPException(status_code=400, detail="Confidence must be between 0.01 and 1.0")
    raw = await file.read(MAX_FILE_SIZE + 1)
    await file.close()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Image exceeds 5 MB")
    try:
        result = await run_in_threadpool(analyze_safety, raw, confidence)
    except ValueError:
        raise HTTPException(status_code=422, detail="Upload a valid traffic/safety image")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Safety prototype inference failed")
        raise HTTPException(status_code=500, detail="Safety prototype inference failed")
    return {
        **result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gps": None,
    }
