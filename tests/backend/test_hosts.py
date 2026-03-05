import pytest


@pytest.mark.asyncio
async def test_list_hosts_empty(client):
    response = await client.get("/api/hosts")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_host(client):
    response = await client.post("/api/hosts", json={
        "ip_address": "192.168.1.100",
        "ssh_user": "root",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["ip_address"] == "192.168.1.100"
    assert data["ssh_user"] == "root"
    assert data["rack_name"] == "aa"
    assert data["status"] == "pending"
