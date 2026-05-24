from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter

from app.schemas.settings import SettingsCatalog

router = APIRouter(prefix="/settings", tags=["settings"])

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "settings_catalog.json"


@lru_cache(maxsize=1)
def _load_catalog() -> SettingsCatalog:
    with _CATALOG_PATH.open("r", encoding="utf-8") as fh:
        return SettingsCatalog.model_validate(json.load(fh))


@router.get("/catalog", response_model=SettingsCatalog)
async def catalog() -> SettingsCatalog:
    return _load_catalog()
