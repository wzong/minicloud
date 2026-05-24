from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import JobStatus, SliceJob
from app.schemas.slice import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
async def list_jobs(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[JobOut]:
    rows = (
        (await db.execute(select(SliceJob).order_by(desc(SliceJob.created_at)).limit(limit)))
        .scalars()
        .all()
    )
    return [JobOut.model_validate(r) for r in rows]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)) -> JobOut:
    job = await db.get(SliceJob, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return JobOut.model_validate(job)


@router.delete("/{job_id}")
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    job = await db.get(SliceJob, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    await db.delete(job)
    await db.commit()
    return {"ok": True}


@router.get("/{job_id}/logs", response_class=PlainTextResponse)
async def get_logs(job_id: str, db: AsyncSession = Depends(get_db)) -> str:
    job = await db.get(SliceJob, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job.log or ""


@router.get("/{job_id}/gcode")
async def download_gcode(job_id: str, db: AsyncSession = Depends(get_db)) -> FileResponse:
    job = await db.get(SliceJob, job_id)
    if job is None or job.gcode_path is None:
        raise HTTPException(404, "g-code not available")
    if job.status != JobStatus.succeeded:
        raise HTTPException(409, f"job not finished (status={job.status})")
    p = Path(job.gcode_path)
    if not p.exists():
        raise HTTPException(410, "g-code file is gone")
    return FileResponse(p, media_type="text/plain", filename=p.name)
