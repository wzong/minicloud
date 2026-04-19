import asyncio

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from typing import Optional

from app.models.host import Host
from app.models.vm import VM, VMStatus
from app.models.cluster import ClusterNode
from app.models.ssh_key import SSHKey
from app.schemas.vm import VMCreate, VMReadiness
from app.services.ip_manager import IPManager
from app.config import settings


class VMService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_vms(
        self,
        host_id: Optional[int] = None,
        status: Optional[str] = None,
        cluster_id: Optional[int] = None,
    ) -> list[dict]:
        query = select(VM, Host.ip_address, Host.rack_name).join(Host, VM.host_id == Host.id)

        if host_id:
            query = query.where(VM.host_id == host_id)
        if status:
            query = query.where(VM.status == status)
        if cluster_id:
            query = query.join(ClusterNode, ClusterNode.vm_id == VM.id).where(
                ClusterNode.cluster_id == cluster_id
            )

        query = query.order_by(VM.name)
        result = await self.db.execute(query)

        vms = []
        for vm, host_ip, rack_name in result.all():
            vm_dict = {
                "id": vm.id,
                "name": vm.name,
                "host_id": vm.host_id,
                "ip_address": vm.ip_address,
                "status": vm.status.value if hasattr(vm.status, 'value') else vm.status,
                "cpu_cores": vm.cpu_cores,
                "ram_mb": vm.ram_mb,
                "disk_gb": vm.disk_gb,
                "os_image": vm.os_image,
                "ssh_key_id": vm.ssh_key_id,
                "rack_sequence": vm.rack_sequence,
                "created_at": vm.created_at,
                "updated_at": vm.updated_at,
                "host_ip": host_ip,
                "rack_name": rack_name,
            }
            vms.append(vm_dict)
        return vms

    async def get_vm(self, vm_id: int) -> dict | None:
        result = await self.db.execute(
            select(VM, Host.ip_address, Host.rack_name)
            .join(Host, VM.host_id == Host.id)
            .where(VM.id == vm_id)
        )
        row = result.first()
        if not row:
            return None
        vm, host_ip, rack_name = row
        return {
            "id": vm.id,
            "name": vm.name,
            "host_id": vm.host_id,
            "ip_address": vm.ip_address,
            "status": vm.status.value if hasattr(vm.status, 'value') else vm.status,
            "cpu_cores": vm.cpu_cores,
            "ram_mb": vm.ram_mb,
            "disk_gb": vm.disk_gb,
            "os_image": vm.os_image,
            "ssh_key_id": vm.ssh_key_id,
            "rack_sequence": vm.rack_sequence,
            "created_at": vm.created_at,
            "updated_at": vm.updated_at,
            "host_ip": host_ip,
            "rack_name": rack_name,
        }

    async def create_vm(self, data: VMCreate) -> dict:
        # Determine host
        if data.host_id:
            host = await self.db.get(Host, data.host_id)
            if not host:
                raise HTTPException(status_code=404, detail="Host not found")
        else:
            # Auto-select host with most available resources
            result = await self.db.execute(select(Host).where(Host.status == "online").order_by(Host.ram_mb.desc()))
            host = result.scalars().first()
            if not host:
                raise HTTPException(status_code=400, detail="No available hosts")

        # Get next rack sequence
        result = await self.db.execute(
            select(func.max(VM.rack_sequence)).where(VM.host_id == host.id)
        )
        max_seq = result.scalar() or 0
        next_seq = max_seq + 1
        if next_seq > 99:
            raise HTTPException(status_code=400, detail="Maximum VMs per rack (99) reached")

        # Generate VM name: <dc_code><rack_name><sequence:02d>
        vm_name = f"{settings.datacenter_code}{host.rack_name}{next_seq:02d}"

        # Allocate IP
        ip_manager = IPManager(self.db)
        ip_address = await ip_manager.allocate(vm_id=0)  # temporary, will update

        vm = VM(
            name=vm_name,
            host_id=host.id,
            ip_address=ip_address,
            status=VMStatus.CREATING,
            cpu_cores=data.cpu_cores,
            ram_mb=data.ram_mb,
            disk_gb=data.disk_gb,
            os_image=data.os_image,
            ssh_key_id=data.ssh_key_id,
            rack_sequence=next_seq,
        )
        self.db.add(vm)
        await self.db.flush()

        # Update IP allocation with actual vm_id
        from app.models.ip_allocation import IPAllocation
        ip_result = await self.db.execute(
            select(IPAllocation).where(IPAllocation.ip_address == ip_address)
        )
        ip_alloc = ip_result.scalar_one()
        ip_alloc.vm_id = vm.id

        await self.db.commit()

        # Trigger actual VM creation via hypervisor driver
        try:
            await self._provision_vm(vm, host)
            vm.status = VMStatus.RUNNING
        except Exception as e:
            vm.status = VMStatus.ERROR

        await self.db.commit()
        return await self.get_vm(vm.id)

    async def _provision_vm(self, vm: VM, host: Host) -> None:
        from app.drivers import get_driver
        from app.ssh.client import SSHClient
        from app.models.ssh_key import SSHKey

        ssh = SSHClient(
            host=host.ip_address,
            port=host.ssh_port,
            username=host.ssh_user,
            key_path=host.ssh_key_path,
            password=host.ssh_password,
        )

        ssh_pub_key = None
        if vm.ssh_key_id:
            key = await self.db.get(SSHKey, vm.ssh_key_id)
            if key:
                ssh_pub_key = key.public_key

        routes = None
        if settings.wg_gateway_ip:
            from app.services.wireguard_service import WireGuardService
            wg_service = WireGuardService()
            peers = wg_service._load_peers()
            if peers:
                routes = [
                    {"to": cidr.strip(), "via": settings.wg_gateway_ip}
                    for peer in peers
                    for cidr in peer.get("allowed_ips", "").split(",")
                    if cidr.strip()
                ]

        driver = get_driver(host.os_type, ssh)
        from app.drivers.base import VMSpec
        spec = VMSpec(
            name=vm.name,
            cpu_cores=vm.cpu_cores,
            ram_mb=vm.ram_mb,
            disk_gb=vm.disk_gb,
            os_image=vm.os_image,
            ip_address=vm.ip_address,
            subnet_mask=host.subnet_mask or settings.ip_subnet_mask,
            gateway=host.gateway or settings.ip_gateway,
            dns_servers=settings.dns_servers,
            ssh_public_key=ssh_pub_key,
            bridge=host.bridge_interface or "br0",
            routes=routes,
        )
        async with ssh:
            await driver.create_vm(spec)

    async def start_vm(self, vm_id: int) -> dict:
        vm = await self.db.get(VM, vm_id)
        if not vm:
            raise HTTPException(status_code=404, detail="VM not found")
        host = await self.db.get(Host, vm.host_id)

        from app.drivers import get_driver
        from app.ssh.client import SSHClient
        ssh = SSHClient(host=host.ip_address, port=host.ssh_port, username=host.ssh_user,
                        key_path=host.ssh_key_path, password=host.ssh_password)
        driver = get_driver(host.os_type, ssh)
        async with ssh:
            await driver.start_vm(vm.name)
        vm.status = VMStatus.RUNNING
        await self.db.commit()
        return await self.get_vm(vm_id)

    async def stop_vm(self, vm_id: int) -> dict:
        vm = await self.db.get(VM, vm_id)
        if not vm:
            raise HTTPException(status_code=404, detail="VM not found")
        host = await self.db.get(Host, vm.host_id)

        from app.drivers import get_driver
        from app.ssh.client import SSHClient
        ssh = SSHClient(host=host.ip_address, port=host.ssh_port, username=host.ssh_user,
                        key_path=host.ssh_key_path, password=host.ssh_password)
        driver = get_driver(host.os_type, ssh)
        async with ssh:
            await driver.stop_vm(vm.name)
        vm.status = VMStatus.STOPPED
        await self.db.commit()
        return await self.get_vm(vm_id)

    async def delete_vm(self, vm_id: int) -> None:
        vm = await self.db.get(VM, vm_id)
        if not vm:
            raise HTTPException(status_code=404, detail="VM not found")

        # Check if part of a cluster
        result = await self.db.execute(
            select(ClusterNode).where(ClusterNode.vm_id == vm_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="VM is part of a cluster. Remove from cluster first.")

        host = await self.db.get(Host, vm.host_id)
        try:
            from app.drivers import get_driver
            from app.ssh.client import SSHClient
            ssh = SSHClient(host=host.ip_address, port=host.ssh_port, username=host.ssh_user,
                            key_path=host.ssh_key_path, password=host.ssh_password)
            driver = get_driver(host.os_type, ssh)
            async with ssh:
                await driver.delete_vm(vm.name)
        except Exception:
            pass  # Best effort deletion on hypervisor

        # Release IP
        ip_manager = IPManager(self.db)
        await ip_manager.release(vm.ip_address)

        await self.db.delete(vm)
        await self.db.commit()

    async def refresh_vm_status(self, vm_id: int) -> dict:
        vm = await self.db.get(VM, vm_id)
        if not vm:
            raise HTTPException(status_code=404, detail="VM not found")
        host = await self.db.get(Host, vm.host_id)

        try:
            from app.drivers import get_driver
            from app.ssh.client import SSHClient
            ssh = SSHClient(host=host.ip_address, port=host.ssh_port, username=host.ssh_user,
                            key_path=host.ssh_key_path, password=host.ssh_password)
            driver = get_driver(host.os_type, ssh)
            async with ssh:
                info = await driver.get_vm_info(vm.name)
                if info.state == "running":
                    vm.status = VMStatus.RUNNING
                elif info.state == "shut off" or info.state == "stopped":
                    vm.status = VMStatus.STOPPED
                else:
                    vm.status = VMStatus.ERROR
        except Exception:
            vm.status = VMStatus.ERROR

        await self.db.commit()
        return await self.get_vm(vm_id)

    async def check_readiness(self, vm_id: int) -> VMReadiness:
        import asyncssh

        vm = await self.db.get(VM, vm_id)
        if not vm:
            raise HTTPException(status_code=404, detail="VM not found")
        host = await self.db.get(Host, vm.host_id)

        hypervisor_running = False
        ip_reachable = False
        if host:
            try:
                from app.drivers import get_driver
                from app.ssh.client import SSHClient

                ssh = SSHClient(
                    host=host.ip_address,
                    port=host.ssh_port,
                    username=host.ssh_user,
                    key_path=host.ssh_key_path,
                    password=host.ssh_password,
                )
                driver = get_driver(host.os_type, ssh)
                async with ssh:
                    try:
                        info = await driver.get_vm_info(vm.name)
                        hypervisor_running = info.state == "running"
                    except Exception:
                        pass
                    try:
                        ok, _ = await ssh.run_safe(
                            f"ping -c 1 -W 2 {vm.ip_address}"
                        )
                        ip_reachable = ok
                    except Exception:
                        pass
            except Exception:
                pass

        ssh_port_open = await self._check_tcp(vm.ip_address, 22, timeout=3)

        ssh_auth_ok = False
        cloud_init_status: Optional[str] = None
        ssh_key = None
        if vm.ssh_key_id:
            ssh_key = await self.db.get(SSHKey, vm.ssh_key_id)

        if ssh_port_open and ssh_key:
            try:
                conn = await asyncio.wait_for(
                    asyncssh.connect(
                        vm.ip_address,
                        username="ubuntu",
                        client_keys=[ssh_key.private_key_path],
                        known_hosts=None,
                    ),
                    timeout=5,
                )
                ssh_auth_ok = True
                try:
                    result = await asyncio.wait_for(
                        conn.run("cloud-init status", check=False),
                        timeout=10,
                    )
                    out = (result.stdout or "").strip()
                    for line in out.splitlines():
                        if "status:" in line:
                            cloud_init_status = line.split("status:", 1)[1].strip().split()[0]
                            break
                except Exception:
                    pass
                finally:
                    conn.close()
                    try:
                        await conn.wait_closed()
                    except Exception:
                        pass
            except Exception:
                pass

        return VMReadiness(
            hypervisor_running=hypervisor_running,
            ip_reachable=ip_reachable,
            ssh_port_open=ssh_port_open,
            ssh_auth_ok=ssh_auth_ok,
            cloud_init_status=cloud_init_status,
        )

    @staticmethod
    async def _check_tcp(host: str, port: int, timeout: float) -> bool:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return True
        except Exception:
            return False

    async def get_vms_by_rack(self) -> list[dict]:
        result = await self.db.execute(
            select(VM, Host.ip_address, Host.rack_name)
            .join(Host, VM.host_id == Host.id)
            .order_by(Host.rack_name, VM.rack_sequence)
        )
        racks = {}
        for vm, host_ip, rack_name in result.all():
            if rack_name not in racks:
                racks[rack_name] = {"rack_name": rack_name, "host_ip": host_ip, "vms": []}
            racks[rack_name]["vms"].append({
                "id": vm.id,
                "name": vm.name,
                "host_id": vm.host_id,
                "ip_address": vm.ip_address,
                "status": vm.status.value if hasattr(vm.status, 'value') else vm.status,
                "cpu_cores": vm.cpu_cores,
                "ram_mb": vm.ram_mb,
                "disk_gb": vm.disk_gb,
                "os_image": vm.os_image,
                "ssh_key_id": vm.ssh_key_id,
                "rack_sequence": vm.rack_sequence,
                "created_at": vm.created_at,
                "updated_at": vm.updated_at,
                "host_ip": host_ip,
                "rack_name": rack_name,
            })
        return list(racks.values())
