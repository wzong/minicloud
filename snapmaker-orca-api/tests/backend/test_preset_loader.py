from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.preset_loader import PresetLoader


@pytest.fixture()
def fake_resources(tmp_path: Path) -> Path:
    root = tmp_path / "resources"
    (root / "profiles" / "Generic" / "machine").mkdir(parents=True)
    (root / "profiles" / "Generic" / "process").mkdir(parents=True)
    (root / "profiles" / "Generic" / "filament").mkdir(parents=True)

    (root / "profiles" / "Generic" / "machine" / "base.json").write_text(
        json.dumps({"type": "machine", "name": "Base 0.4", "printable_height": "250"})
    )
    (root / "profiles" / "Generic" / "machine" / "derived.json").write_text(
        json.dumps(
            {
                "type": "machine",
                "name": "Derived 0.6",
                "inherits": "Base 0.4",
                "nozzle_diameter": ["0.6"],
            }
        )
    )
    (root / "profiles" / "Generic" / "process" / "p1.json").write_text(
        json.dumps({"type": "process", "name": "P1", "layer_height": "0.2"})
    )
    (root / "profiles" / "Generic" / "filament" / "f1.json").write_text(
        json.dumps({"type": "filament", "name": "F1", "filament_type": ["PLA"]})
    )
    return root


def test_scan_and_list(fake_resources: Path) -> None:
    pl = PresetLoader(fake_resources)
    pl.scan()
    by_kind = {k: [p["name"] for p in pl.list_presets(k)] for k in ("printer", "filament", "process")}
    assert "Base 0.4" in by_kind["printer"]
    assert "Derived 0.6" in by_kind["printer"]
    assert "F1" in by_kind["filament"]
    assert "P1" in by_kind["process"]


def test_inheritance_resolve(fake_resources: Path) -> None:
    pl = PresetLoader(fake_resources)
    pl.scan()
    chain = pl.chain("printer", "Derived 0.6")
    assert chain == ["Derived 0.6", "Base 0.4"]
    values = pl.resolve("printer", "Derived 0.6")
    # child wins on conflict, parent fills the rest
    assert values["nozzle_diameter"] == ["0.6"]
    assert values["printable_height"] == "250"


def test_missing_preset_chain_empty(fake_resources: Path) -> None:
    pl = PresetLoader(fake_resources)
    pl.scan()
    assert pl.chain("printer", "Does Not Exist") == []
