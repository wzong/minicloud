"""Background slice-job execution. Updates the job row as the slicer makes progress."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.models import JobStatus, SliceJob, Upload
from app.services.gcode_parser import extract_summary_comments
from app.services.preset_loader import PresetLoader
from app.services.slicer import SlicerError, SlicerService

_PROGRESS_RE = re.compile(r"(\d+)\s*%")


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def run_slice_job(
    job_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    preset_loader: PresetLoader,
) -> None:
    s = get_settings()
    async with session_factory() as session:
        job = await session.get(SliceJob, job_id)
        if job is None:
            return
        upload = await session.get(Upload, job.upload_id)
        if upload is None:
            job.status = JobStatus.failed
            job.error = "upload not found"
            await session.commit()
            return

        job.status = JobStatus.running
        job.started_at = _now()
        job.stage = "preparing"
        work_dir = s.jobs_path / job_id
        job.work_dir = str(work_dir)
        await session.commit()

        printer_vals = (
            preset_loader.resolve("printer", job.printer_preset) if job.printer_preset else None
        )
        filament_vals = (
            preset_loader.resolve("filament", job.filament_preset)
            if job.filament_preset
            else None
        )
        process_vals = (
            preset_loader.resolve("process", job.process_preset) if job.process_preset else None
        )

        async def progress_cb(line: str) -> None:
            m = _PROGRESS_RE.search(line)
            if not m:
                return
            pct = int(m.group(1))
            async with session_factory() as s2:
                j = await s2.get(SliceJob, job_id)
                if j is not None and pct > j.progress:
                    j.progress = min(99, pct)
                    j.stage = "slicing"
                    await s2.commit()

        try:
            result = await SlicerService().slice(
                input_path=Path(upload.path),
                work_dir=work_dir,
                printer_values=printer_vals,
                filament_values=filament_vals,
                process_values=process_vals,
                overrides=job.overrides or {},
                progress_cb=progress_cb,
            )
        except SlicerError as e:
            job.status = JobStatus.failed
            job.error = str(e)
            job.finished_at = _now()
            await session.commit()
            return
        except Exception as e:  # pragma: no cover - defensive
            job.status = JobStatus.failed
            job.error = f"{type(e).__name__}: {e}"
            job.finished_at = _now()
            await session.commit()
            return

        job.log = result.log
        if result.returncode != 0 or result.gcode_path is None:
            job.status = JobStatus.failed
            job.error = f"slicer exit {result.returncode}"
            job.finished_at = _now()
            await session.commit()
            return

        job.gcode_path = str(result.gcode_path)
        job.stats = _build_stats(result.gcode_path, result.stats_raw)
        job.progress = 100
        job.stage = "done"
        job.status = JobStatus.succeeded
        job.finished_at = _now()
        await session.commit()


def _build_stats(gcode_path: Path, stats_raw: dict) -> dict:
    text = gcode_path.read_text(encoding="utf-8", errors="replace")
    summary = extract_summary_comments(text)
    stats: dict = {}

    time_str = summary.get("estimated printing time (normal mode)") or summary.get(
        "estimated printing time"
    )
    if time_str:
        stats["estimated_print_time_sec"] = _parse_time_str(time_str)
        stats["estimated_print_time_str"] = time_str

    fil_mm = summary.get("filament used [mm]")
    if fil_mm:
        try:
            stats["filament_used_mm"] = sum(float(x) for x in fil_mm.split(","))
        except ValueError:
            pass
    fil_g = summary.get("filament used [g]")
    if fil_g:
        try:
            stats["filament_used_g"] = sum(float(x) for x in fil_g.split(","))
        except ValueError:
            pass

    if "slice_info_xml" in stats_raw:
        stats["slice_info_xml_excerpt"] = stats_raw["slice_info_xml"][:4000]

    return stats


def _parse_time_str(s: str) -> int | None:
    parts = re.findall(r"(\d+)([hms])", s)
    if not parts:
        return None
    total = 0
    for n, unit in parts:
        n = int(n)
        if unit == "h":
            total += n * 3600
        elif unit == "m":
            total += n * 60
        elif unit == "s":
            total += n
    return total
