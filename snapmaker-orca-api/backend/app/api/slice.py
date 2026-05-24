from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.presets import _loader as _preset_loader
from app.database import get_db
from app.main_factory import session_factory
from app.models import SliceJob, Upload
from app.schemas.slice import JobOut, SliceRequest
from app.services.job_runner import run_slice_job

router = APIRouter(prefix="/slice", tags=["slice"])


@router.post("", response_model=JobOut)
async def start_slice(
    req: SliceRequest,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    upload = await db.get(Upload, req.upload_id)
    if upload is None:
        raise HTTPException(404, "upload not found")
    job = SliceJob(
        upload_id=req.upload_id,
        printer_preset=req.printer_preset,
        filament_preset=req.filament_preset,
        process_preset=req.process_preset,
        overrides=req.overrides or {},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background.add_task(run_slice_job, job.id, session_factory(), _preset_loader())
    return JobOut.model_validate(job)
