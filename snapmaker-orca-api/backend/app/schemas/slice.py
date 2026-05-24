from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models import JobStatus


class UploadOut(BaseModel):
    id: str
    filename: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SliceRequest(BaseModel):
    upload_id: str
    printer_preset: str | None = None
    filament_preset: str | None = None
    process_preset: str | None = None
    overrides: dict[str, Any] = Field(default_factory=dict)
    plate: int = 0
    arrange: bool = False
    orient: bool = False
    bed_type: str | None = None


class SliceStats(BaseModel):
    estimated_print_time_sec: int | None = None
    filament_used_mm: float | None = None
    filament_used_g: float | None = None
    filament_cost: float | None = None
    layer_count: int | None = None
    layer_height_mm: float | None = None
    first_layer_height_mm: float | None = None
    nozzle_diameter_mm: float | None = None
    object_bbox_mm: list[float] | None = None  # [minx, miny, minz, maxx, maxy, maxz]


class JobOut(BaseModel):
    id: str
    upload_id: str
    status: JobStatus
    progress: int
    stage: str | None = None
    error: str | None = None
    stats: SliceStats | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}
