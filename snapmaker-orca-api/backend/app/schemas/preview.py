from __future__ import annotations

from pydantic import BaseModel


class GcodeLayer(BaseModel):
    index: int
    z: float
    # Flat float32 buffer: [x0,y0,z0, x1,y1,z1, ...] per segment (pairs of vertices).
    # Frontend ingests directly into a three.js BufferGeometry.
    extrude_segments: list[float]
    travel_segments: list[float]
    # Per-extrude-segment feature classification (parallel to extrude_segments pairs).
    feature_ids: list[int]


class GcodePreview(BaseModel):
    layer_count: int
    bbox: list[float]  # [minx, miny, minz, maxx, maxy, maxz]
    feature_legend: dict[str, int]  # feature_name -> id
    layers: list[GcodeLayer]
    total_extruded_mm: float
    total_travel_mm: float
