from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas.settings import PresetOut, PresetValues
from app.services.preset_loader import PresetLoader

router = APIRouter(prefix="/presets", tags=["presets"])


@lru_cache(maxsize=1)
def _loader() -> PresetLoader:
    pl = PresetLoader(get_settings().slicer_resources_dir)
    pl.scan()
    return pl


@router.get("", response_model=list[PresetOut])
async def list_presets(kind: str | None = None) -> list[PresetOut]:
    if kind and kind not in ("printer", "filament", "process"):
        raise HTTPException(400, "kind must be printer | filament | process")
    return [PresetOut(**p) for p in _loader().list_presets(kind)]


@router.get("/{kind}/{name}", response_model=PresetValues)
async def preset_values(kind: str, name: str) -> PresetValues:
    if kind not in ("printer", "filament", "process"):
        raise HTTPException(400, "kind must be printer | filament | process")
    chain = _loader().chain(kind, name)
    if not chain:
        raise HTTPException(404, f"{kind} preset {name!r} not found")
    return PresetValues(
        name=name, kind=kind, inherits_chain=chain, values=_loader().resolve(kind, name)
    )
