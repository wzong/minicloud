from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(1024))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SliceJob(Base):
    __tablename__ = "slice_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    upload_id: Mapped[str] = mapped_column(String(32))
    printer_preset: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filament_preset: Mapped[str | None] = mapped_column(String(255), nullable=True)
    process_preset: Mapped[str | None] = mapped_column(String(255), nullable=True)
    overrides: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.pending)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    work_dir: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    gcode_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    log: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
