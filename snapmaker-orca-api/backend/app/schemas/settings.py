from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

SettingType = Literal[
    "float", "int", "bool", "enum", "percent", "string", "floats", "ints", "strings", "color"
]


class EnumChoice(BaseModel):
    value: str
    label: str


class SettingDef(BaseModel):
    key: str
    label: str
    type: SettingType
    default: Any | None = None
    min: float | None = None
    max: float | None = None
    unit: str | None = None
    tooltip: str | None = None
    choices: list[EnumChoice] | None = None
    depends_on: dict[str, Any] | None = None


class SettingGroup(BaseModel):
    title: str
    settings: list[SettingDef]


class SettingTab(BaseModel):
    key: str
    title: str
    groups: list[SettingGroup]


class SettingsCatalog(BaseModel):
    version: str
    tabs: list[SettingTab]


class PresetOut(BaseModel):
    name: str
    kind: Literal["printer", "filament", "process"]
    inherits: str | None = None
    source: str  # path relative to resources dir


class PresetValues(BaseModel):
    name: str
    kind: Literal["printer", "filament", "process"]
    inherits_chain: list[str]
    values: dict[str, Any]
