from __future__ import annotations

import io

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture()
async def client():
    app = create_app()
    # Run lifespan so tables are created.
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


async def test_health(client: AsyncClient) -> None:
    r = await client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "slicer_bin" in data


async def test_settings_catalog(client: AsyncClient) -> None:
    r = await client.get("/api/settings/catalog")
    assert r.status_code == 200
    data = r.json()
    tab_keys = {t["key"] for t in data["tabs"]}
    assert {"quality", "strength", "speed", "support", "others", "filament", "printer"} <= tab_keys
    # Sanity-check a common setting is present
    flat = [s["key"] for t in data["tabs"] for g in t["groups"] for s in g["settings"]]
    assert "layer_height" in flat
    assert "sparse_infill_density" in flat


async def test_upload_rejects_unknown_ext(client: AsyncClient) -> None:
    r = await client.post(
        "/api/uploads",
        files={"file": ("hello.txt", io.BytesIO(b"not a model"), "text/plain")},
    )
    assert r.status_code == 400


async def test_upload_accepts_stl(client: AsyncClient) -> None:
    r = await client.post(
        "/api/uploads",
        files={"file": ("cube.stl", io.BytesIO(b"solid x\nendsolid x\n"), "model/stl")},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["filename"] == "cube.stl"
    assert data["size_bytes"] > 0


async def test_slice_404_when_upload_missing(client: AsyncClient) -> None:
    r = await client.post(
        "/api/slice",
        json={"upload_id": "doesnotexist", "overrides": {}},
    )
    assert r.status_code == 404
