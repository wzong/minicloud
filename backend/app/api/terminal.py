from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import router
from app.database import get_db
from app.models.host import Host
from app.models.ssh_key import SSHKey
from app.models.vm import VM, VMStatus
from app.ssh.client import SSHClient
from app.ssh.terminal import proxy_terminal

terminal_router = APIRouter(tags=["terminal"])


@terminal_router.websocket("/hosts/{host_id}/terminal")
async def host_terminal(
    websocket: WebSocket,
    host_id: int,
    db: AsyncSession = Depends(get_db),
):
    host = await db.get(Host, host_id)
    if not host:
        await websocket.close(code=4404)
        return

    from app.services.host_service import HostService

    ssh_client = HostService(db).get_ssh_client(host)
    await proxy_terminal(websocket, ssh_client)


@terminal_router.websocket("/vms/{vm_id}/terminal")
async def vm_terminal(
    websocket: WebSocket,
    vm_id: int,
    db: AsyncSession = Depends(get_db),
):
    vm = await db.get(VM, vm_id)
    if not vm:
        await websocket.close(code=4404)
        return
    if vm.status != VMStatus.RUNNING:
        await websocket.close(code=4409)
        return
    if not vm.ssh_key_id:
        await websocket.close(code=4412)
        return

    ssh_key = await db.get(SSHKey, vm.ssh_key_id)
    if not ssh_key:
        await websocket.close(code=4412)
        return

    host = await db.get(Host, vm.host_id)
    if not host:
        await websocket.close(code=4404)
        return

    from app.services.host_service import HostService

    host_ssh = HostService(db).get_ssh_client(host)

    ssh_client = SSHClient(
        host=vm.ip_address,
        port=22,
        username="ubuntu",
        key_path=ssh_key.private_key_path,
        jump_via=host_ssh,
    )
    await proxy_terminal(websocket, ssh_client)


router.include_router(terminal_router)
