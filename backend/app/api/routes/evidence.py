"""Authenticated, bounded evidence storage. No public static evidence directory."""
from pathlib import Path
from io import BytesIO
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from app.core.config import settings
from app.db.session import get_db
from app.models.models import Event

router = APIRouter(prefix="/api/events", tags=["Evidence"])

@router.post("/{event_id}/evidence")
async def upload_evidence(event_id: int, file: UploadFile, db=Depends(get_db)):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    raw = await file.read(5 * 1024 * 1024 + 1)
    await file.close()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(413, "Image exceeds 5 MB")
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.width * image.height > 16_000_000:
                raise ValueError("Image too large")
            image.load()
            clean = image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, "Upload a valid image up to 16 megapixels")
    folder = Path(settings.EVIDENCE_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    # Re-encode to remove embedded metadata. Stored filenames are server-generated.
    target = folder / f"{event.id}.jpg"
    temp = folder / f"{uuid.uuid4().hex}.tmp"
    try:
        clean.save(temp, format="JPEG", quality=85)
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    event.evidence_path = f"/api/events/{event.id}/evidence"
    return {"persisted": True, "evidence_path": event.evidence_path}

@router.get("/{event_id}/evidence")
async def get_evidence(event_id: int, db=Depends(get_db)):
    event = await db.get(Event, event_id)
    path = Path(settings.EVIDENCE_DIR) / f"{event_id}.jpg"
    if not event or not event.evidence_path or not path.is_file():
        raise HTTPException(404, "Evidence unavailable")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})
