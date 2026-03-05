import pytest


@pytest.mark.asyncio
async def test_list_clusters_empty(client):
    response = await client.get("/api/clusters")
    assert response.status_code == 200
    assert response.json() == []
