import pytest

from app.models.host import OSType
from app.services import host_service as host_service_module


class _StubSSH:
    def __init__(self, responses: dict[str, tuple[bool, str]]):
        self._responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def run_safe(self, command: str) -> tuple[bool, str]:
        for prefix, result in self._responses.items():
            if command.startswith(prefix):
                return result
        return False, ""


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
    assert data["bridge_configured"] is None
    assert data["hypervisor_installed"] is None


async def _make_linux_host(client, db_session, *, bridge_interface: str | None):
    response = await client.post("/api/hosts", json={
        "ip_address": "192.168.1.101",
        "ssh_user": "root",
    })
    host_id = response.json()["id"]
    from app.models.host import Host
    host = await db_session.get(Host, host_id)
    host.os_type = OSType.LINUX
    host.bridge_interface = bridge_interface
    await db_session.commit()
    return host_id


@pytest.mark.asyncio
async def test_check_bridge_configured(client, db_session, monkeypatch):
    host_id = await _make_linux_host(client, db_session, bridge_interface="br0")
    stub = _StubSSH({"ip link show br0": (True, "2: br0: <BROADCAST,MULTICAST,UP,LOWER_UP>")})
    monkeypatch.setattr(host_service_module.HostService, "_get_ssh_client", lambda self, host: stub)

    response = await client.post(f"/api/hosts/{host_id}/check-bridge")
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True
    assert data["bridge_name"] == "br0"

    host_resp = await client.get(f"/api/hosts/{host_id}")
    assert host_resp.json()["bridge_configured"] is True


@pytest.mark.asyncio
async def test_check_bridge_not_configured(client, db_session, monkeypatch):
    host_id = await _make_linux_host(client, db_session, bridge_interface="br0")
    stub = _StubSSH({"ip link show br0": (False, "Device does not exist")})
    monkeypatch.setattr(host_service_module.HostService, "_get_ssh_client", lambda self, host: stub)

    response = await client.post(f"/api/hosts/{host_id}/check-bridge")
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is False
    assert data["setup_commands"]
    assert any("nmcli" in cmd for cmd in data["setup_commands"])

    host_resp = await client.get(f"/api/hosts/{host_id}")
    assert host_resp.json()["bridge_configured"] is False


@pytest.mark.asyncio
async def test_check_bridge_os_not_detected(client, monkeypatch):
    response = await client.post("/api/hosts", json={
        "ip_address": "192.168.1.102",
        "ssh_user": "root",
    })
    host_id = response.json()["id"]
    stub = _StubSSH({})
    monkeypatch.setattr(host_service_module.HostService, "_get_ssh_client", lambda self, host: stub)

    response = await client.post(f"/api/hosts/{host_id}/check-bridge")
    assert response.status_code == 400
    assert "OS type not detected" in response.json()["detail"]
