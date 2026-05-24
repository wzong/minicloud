from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.services.slicer import SlicerService

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    s = get_settings()
    version = await SlicerService().version()
    return {
        "ok": True,
        "slicer_bin": s.slicer_bin,
        "slicer_present": version is not None,
        "slicer_version": version,
        "resources_dir": s.slicer_resources_dir,
    }
