import pytest


@pytest.mark.asyncio
async def test_list_vms_empty(client):
    response = await client.get("/api/vms")
    assert response.status_code == 200
    assert response.json() == []
