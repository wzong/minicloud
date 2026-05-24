from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import JobStatus, SliceJob
from app.schemas.preview import GcodeLayer, GcodePreview
from app.services.gcode_parser import parse_gcode

router = APIRouter(prefix="/jobs", tags=["preview"])


@router.get("/{job_id}/preview", response_model=GcodePreview)
async def gcode_preview(
    job_id: str,
    skip_travel: bool = False,
    db: AsyncSession = Depends(get_db),
) -> GcodePreview:
    job = await db.get(SliceJob, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    if job.status != JobStatus.succeeded or job.gcode_path is None:
        raise HTTPException(409, "g-code not ready")
    p = Path(job.gcode_path)
    if not p.exists():
        raise HTTPException(410, "g-code file is gone")
    text = p.read_text(encoding="utf-8", errors="replace")
    parsed = parse_gcode(text)
    layers = [
        GcodeLayer(
            index=L.index,
            z=L.z,
            extrude_segments=L.extrude_segments,
            travel_segments=[] if skip_travel else L.travel_segments,
            feature_ids=L.feature_ids,
        )
        for L in parsed.layers
    ]
    return GcodePreview(
        layer_count=len(layers),
        bbox=parsed.bbox,
        feature_legend=parsed.feature_legend,
        layers=layers,
        total_extruded_mm=parsed.total_extruded,
        total_travel_mm=parsed.total_travel,
    )
