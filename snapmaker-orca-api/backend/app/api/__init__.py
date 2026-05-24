from fastapi import APIRouter

from app.api import gcode, health, jobs, presets, settings, slice, uploads

router = APIRouter(prefix="/api")
router.include_router(health.router)
router.include_router(settings.router)
router.include_router(presets.router)
router.include_router(uploads.router)
router.include_router(slice.router)
router.include_router(jobs.router)
router.include_router(gcode.router)
