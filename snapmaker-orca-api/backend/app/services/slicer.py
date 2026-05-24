"""Drive the Snapmaker Orca CLI to produce G-code from an uploaded model + JSON settings."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import get_settings


@dataclass
class SliceResult:
    returncode: int
    gcode_path: Path | None
    log: str
    stats_raw: dict[str, Any]


class SlicerError(RuntimeError):
    pass


class SlicerService:
    def __init__(
        self,
        slicer_bin: str | None = None,
        resources_dir: str | None = None,
        timeout: int | None = None,
    ) -> None:
        s = get_settings()
        self.slicer_bin = slicer_bin or s.slicer_bin
        self.resources_dir = resources_dir or s.slicer_resources_dir
        self.timeout = timeout or s.slice_timeout_sec

    # --------------------------------------------------------------- version

    async def version(self) -> str | None:
        if not Path(self.slicer_bin).exists():
            return None
        try:
            proc = await asyncio.create_subprocess_exec(
                self.slicer_bin,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, _err = await asyncio.wait_for(proc.communicate(), timeout=10)
        except (FileNotFoundError, asyncio.TimeoutError):
            return None
        return out.decode("utf-8", "replace").strip().splitlines()[0] if out else None

    # ----------------------------------------------------------------- slice

    async def slice(
        self,
        *,
        input_path: Path,
        work_dir: Path,
        printer_values: dict[str, Any] | None,
        filament_values: dict[str, Any] | None,
        process_values: dict[str, Any] | None,
        overrides: dict[str, Any],
        plate: int = 0,
        arrange: bool = False,
        orient: bool = False,
        bed_type: str | None = None,
        progress_cb=None,
    ) -> SliceResult:
        work_dir.mkdir(parents=True, exist_ok=True)
        out_dir = work_dir / "out"
        out_dir.mkdir(exist_ok=True)

        # Merge overrides into the process profile — that's where most slicing settings live.
        process = dict(process_values or {})
        process.update(overrides)

        printer_json = self._write_profile(work_dir / "printer.json", printer_values, "machine")
        filament_json = self._write_profile(work_dir / "filament.json", filament_values, "filament")
        process_json = self._write_profile(work_dir / "process.json", process, "process")

        export_3mf = out_dir / "result.3mf"

        cmd = [self.slicer_bin]
        if arrange:
            cmd += ["--arrange", "1"]
        if orient:
            cmd += ["--orient", "1"]
        if bed_type:
            cmd += ["--curr-bed-type", bed_type]
        load_parts: list[str] = []
        if printer_json:
            load_parts.append(str(printer_json))
        if process_json:
            load_parts.append(str(process_json))
        if load_parts:
            cmd += ["--load-settings", ";".join(load_parts)]
        if filament_json:
            cmd += ["--load-filaments", str(filament_json)]
        cmd += [
            "--slice",
            str(plate),
            "--export-3mf",
            str(export_3mf),
            "--outputdir",
            str(out_dir),
            "--debug",
            "2",
            str(input_path),
        ]

        env = os.environ.copy()
        # The slicer initialises GL even in headless mode; provide a safe default.
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        env.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")

        log_path = work_dir / "slicer.log"
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
            cwd=str(work_dir),
        )

        log_buf: list[str] = []
        assert proc.stdout is not None
        try:
            async with asyncio.timeout(self.timeout):
                async for line in proc.stdout:
                    s = line.decode("utf-8", "replace").rstrip()
                    log_buf.append(s)
                    if progress_cb is not None:
                        try:
                            await progress_cb(s)
                        except Exception:
                            pass
                rc = await proc.wait()
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            log_path.write_text("\n".join(log_buf), encoding="utf-8")
            raise SlicerError(f"Slicer timed out after {self.timeout}s")

        log_text = "\n".join(log_buf)
        log_path.write_text(log_text, encoding="utf-8")

        gcode_path: Path | None = None
        stats_raw: dict[str, Any] = {}
        if export_3mf.exists():
            gcode_path, stats_raw = self._extract_3mf(export_3mf, out_dir)

        return SliceResult(returncode=rc, gcode_path=gcode_path, log=log_text, stats_raw=stats_raw)

    # --------------------------------------------------------------- helpers

    def _write_profile(
        self, path: Path, values: dict[str, Any] | None, kind: str
    ) -> Path | None:
        if not values:
            return None
        payload = {
            "type": kind,
            "name": path.stem,
            **{k: self._to_str(v) for k, v in values.items()},
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def _to_str(v: Any) -> Any:
        # Orca's JSON profiles store every leaf as a string or list of strings.
        if isinstance(v, bool):
            return "1" if v else "0"
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, list):
            return [SlicerService._to_str(x) for x in v]
        return v

    def _extract_3mf(self, archive: Path, out_dir: Path) -> tuple[Path | None, dict[str, Any]]:
        gcode_path: Path | None = None
        stats: dict[str, Any] = {}
        try:
            with zipfile.ZipFile(archive) as zf:
                names = zf.namelist()
                for name in names:
                    if name.endswith(".gcode") and "Metadata" in name:
                        target = out_dir / Path(name).name
                        with zf.open(name) as src, target.open("wb") as dst:
                            shutil.copyfileobj(src, dst)
                        gcode_path = target
                        break
                for name in names:
                    if name.endswith("slice_info.config"):
                        with zf.open(name) as src:
                            stats["slice_info_xml"] = src.read().decode("utf-8", "replace")
                        break
        except zipfile.BadZipFile:
            pass
        return gcode_path, stats
