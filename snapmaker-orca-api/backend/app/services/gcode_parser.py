"""Parse sliced G-code into per-layer move buffers consumable by a three.js viewer.

The parser is intentionally streaming/single-pass and supports the conventions Orca emits:

* ``;LAYER_CHANGE`` / ``;Z:<value>`` / ``;HEIGHT:<value>`` comments mark layer boundaries.
* ``;TYPE:<feature>`` comments switch the active extrusion feature
  (``External perimeter``, ``Internal infill``, ``Skirt``, ``Support material`` …).
* Lines are absolute by default (``G90``); we track ``M82``/``M83`` for extruder mode.
* Moves are split into extrude (``E`` increases) and travel (``E`` unchanged) buffers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_NUM = re.compile(r"([XYZEF])(-?\d+(?:\.\d+)?)")
_COMMENT_KV = re.compile(r";\s*([A-Za-z_]+)\s*[:=]\s*(.+)")


FEATURE_ALIASES = {
    "external perimeter": "outer_wall",
    "outer wall": "outer_wall",
    "inner wall": "inner_wall",
    "internal perimeter": "inner_wall",
    "perimeter": "inner_wall",
    "internal infill": "infill",
    "sparse infill": "infill",
    "solid infill": "solid_infill",
    "top solid infill": "top_surface",
    "bottom surface": "bottom_surface",
    "top surface": "top_surface",
    "skirt": "skirt",
    "brim": "brim",
    "support material": "support",
    "support material interface": "support_interface",
    "support": "support",
    "bridge infill": "bridge",
    "overhang perimeter": "overhang",
    "gap fill": "gap_fill",
    "wipe tower": "wipe_tower",
    "custom": "custom",
}

FEATURE_ORDER = [
    "outer_wall",
    "inner_wall",
    "solid_infill",
    "infill",
    "top_surface",
    "bottom_surface",
    "support",
    "support_interface",
    "bridge",
    "overhang",
    "skirt",
    "brim",
    "gap_fill",
    "wipe_tower",
    "custom",
    "unknown",
]


@dataclass
class _LayerBuf:
    index: int
    z: float
    extrude_segments: list[float] = field(default_factory=list)
    travel_segments: list[float] = field(default_factory=list)
    feature_ids: list[int] = field(default_factory=list)


@dataclass
class ParsedGcode:
    layers: list[_LayerBuf]
    bbox: list[float]
    feature_legend: dict[str, int]
    total_extruded: float
    total_travel: float
    stats: dict


def _normalize_feature(raw: str) -> str:
    key = raw.strip().lower()
    return FEATURE_ALIASES.get(key, "unknown")


def parse_gcode(text: str) -> ParsedGcode:
    feature_legend: dict[str, int] = {f: i for i, f in enumerate(FEATURE_ORDER)}

    x = y = z = 0.0
    e_abs = 0.0
    absolute_e = True

    cur_feature = "unknown"
    layers: list[_LayerBuf] = []
    cur: _LayerBuf | None = None
    pending_layer = True  # open the first layer lazily on the first move

    bbox = [float("inf"), float("inf"), float("inf"), float("-inf"), float("-inf"), float("-inf")]

    total_extruded = 0.0
    total_travel = 0.0

    stats: dict = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith(";"):
            # Feature switch
            up = line[1:].strip()
            if up.upper().startswith("TYPE:"):
                cur_feature = _normalize_feature(up.split(":", 1)[1])
            elif up.upper().startswith("LAYER_CHANGE") or up.upper().startswith("LAYER:"):
                pending_layer = True
            elif m := _COMMENT_KV.match(line):
                k, v = m.group(1).lower(), m.group(2).strip()
                if k in ("z", "layer_z", "layer_height", "height"):
                    try:
                        z = float(v.split()[0])
                        pending_layer = True
                    except ValueError:
                        pass
                elif k == "estimated_printing_time_normal_mode" or k == "estimated printing time":
                    stats["estimated_print_time_str"] = v
                elif k == "filament_used":
                    stats["filament_used_raw"] = v
            continue

        # Strip inline comment
        if ";" in line:
            line = line.split(";", 1)[0].strip()
            if not line:
                continue

        head, _, rest = line.partition(" ")
        head = head.upper()

        if head in ("G90",):
            absolute_e = True
            continue
        if head in ("G91",):
            absolute_e = False
            continue
        if head == "M82":
            absolute_e = True
            continue
        if head == "M83":
            absolute_e = False
            continue

        if head not in ("G0", "G1"):
            continue

        nx, ny, nz, ne = x, y, z, None
        for axis, val in _NUM.findall(rest):
            f = float(val)
            if axis == "X":
                nx = f
            elif axis == "Y":
                ny = f
            elif axis == "Z":
                nz = f
            elif axis == "E":
                ne = f

        # E delta
        e_delta = 0.0
        if ne is not None:
            if absolute_e:
                e_delta = ne - e_abs
                e_abs = ne
            else:
                e_delta = ne

        if pending_layer:
            cur = _LayerBuf(index=len(layers), z=nz)
            layers.append(cur)
            pending_layer = False

        if cur is None:
            cur = _LayerBuf(index=0, z=nz)
            layers.append(cur)

        # Layer rolled with this move's Z
        if nz != cur.z and (nx == x and ny == y):
            # pure Z-only motion; treat as layer boundary
            cur = _LayerBuf(index=len(layers), z=nz)
            layers.append(cur)

        if e_delta > 1e-6:
            cur.extrude_segments.extend((x, y, z, nx, ny, nz))
            cur.feature_ids.append(feature_legend.get(cur_feature, feature_legend["unknown"]))
            dx, dy, dz_ = nx - x, ny - y, nz - z
            total_extruded += (dx * dx + dy * dy + dz_ * dz_) ** 0.5
            for v, axis in ((nx, 0), (ny, 1), (nz, 2)):
                if v < bbox[axis]:
                    bbox[axis] = v
                if v > bbox[3 + axis]:
                    bbox[3 + axis] = v
        else:
            cur.travel_segments.extend((x, y, z, nx, ny, nz))
            dx, dy, dz_ = nx - x, ny - y, nz - z
            total_travel += (dx * dx + dy * dy + dz_ * dz_) ** 0.5

        x, y, z = nx, ny, nz

    # Drop preamble layers that contain only travel (pre-print priming / homing).
    layers = [L for L in layers if L.extrude_segments]
    for i, L in enumerate(layers):
        L.index = i

    if not all(b != float("inf") and b != float("-inf") for b in bbox):
        bbox = [0, 0, 0, 0, 0, 0]

    stats["layer_count"] = len(layers)
    stats["total_extruded_mm"] = total_extruded
    stats["total_travel_mm"] = total_travel

    return ParsedGcode(
        layers=layers,
        bbox=bbox,
        feature_legend=feature_legend,
        total_extruded=total_extruded,
        total_travel=total_travel,
        stats=stats,
    )


def extract_summary_comments(text: str, max_lines: int = 400) -> dict:
    """Extract Orca's slicing summary comments at the end of the G-code file.

    Orca appends a block like ``; estimated printing time (normal mode) = 1h 23m 45s``
    and ``; filament used [mm] = ...``. We scan from the bottom for speed.
    """
    out: dict = {}
    lines = text.splitlines()
    tail = lines[-max_lines:] if len(lines) > max_lines else lines
    for raw in tail:
        if not raw.startswith(";"):
            continue
        body = raw[1:].strip()
        if "=" not in body:
            continue
        key, _, value = body.partition("=")
        out[key.strip().lower()] = value.strip()
    return out
