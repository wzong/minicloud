import pytest


@pytest.mark.asyncio
async def test_list_ssh_keys_empty(client):
    response = await client.get("/api/ssh-keys")
    assert response.status_code == 200
    assert response.json() == []
