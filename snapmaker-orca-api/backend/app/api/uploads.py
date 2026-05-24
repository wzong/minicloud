from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Upload
from app.schemas.slice import UploadOut

router = APIRouter(prefix="/uploads", tags=["uploads"])

_ALLOWED_EXT = {".stl", ".3mf", ".obj", ".step", ".stp"}


@router.post("", response_model=UploadOut)
async def upload_model(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> UploadOut:
    s = get_settings()
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(400, f"unsupported extension {ext!r}, expected one of {_ALLOWED_EXT}")
    max_bytes = s.max_upload_mb * 1024 * 1024
    upload_id = uuid.uuid4().hex
    dest = s.uploads_path / f"{upload_id}{ext}"
    written = 0
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            written += len(chunk)
            if written > max_bytes:
                await out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"upload exceeds {s.max_upload_mb} MB")
            await out.write(chunk)
    row = Upload(id=upload_id, filename=file.filename or dest.name, path=str(dest), size_bytes=written)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return UploadOut.model_validate(row)
