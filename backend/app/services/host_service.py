from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.host import Host, HostStatus, OSType
from app.models.vm import VM
from app.schemas.host import HostCreate, HypervisorCheck, BridgeCheck
from app.services.rack_namer import get_next_rack_name
from app.ssh.client import SSHClient


class HostService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_hosts(self) -> list[Host]:
        result = await self.db.execute(select(Host).order_by(Host.rack_name))
        return list(result.scalars().all())

    async def get_host(self, host_id: int) -> Host | None:
        return await self.db.get(Host, host_id)

    async def create_host(self, data: HostCreate) -> Host:
        # Check for duplicate IP
        existing = await self.db.execute(
            select(Host).where(Host.ip_address == data.ip_address)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Host with this IP already exists")

        rack_name = await get_next_rack_name(self.db)
        host = Host(
            ip_address=data.ip_address,
            ssh_port=data.ssh_port,
            ssh_user=data.ssh_user,
            ssh_key_path=data.ssh_key_path,
            ssh_password=data.ssh_password,
            rack_name=rack_name,
            status=HostStatus.PENDING,
        )
        self.db.add(host)
        await self.db.commit()
        await self.db.refresh(host)
        return host

    async def delete_host(self, host_id: int) -> None:
        host = await self.db.get(Host, host_id)
        if not host:
            raise HTTPException(status_code=404, detail="Host not found")

        # Check for existing VMs
        vms = await self.db.execute(select(VM).where(VM.host_id == host_id))
        if vms.scalars().first():
            raise HTTPException(status_code=400, detail="Cannot delete host with existing VMs")

        await self.db.delete(host)
        await self.db.commit()

    async def update_rack_name(self, host_id: int, rack_name: str) -> Host:
        host = await self.db.get(Host, host_id)
        if not host:
            raise HTTPException(status_code=404, detail="Host not found")

        if len(rack_name) != 2 or not rack_name.isalpha() or not rack_name.islower():
            raise HTTPException(status_code=400, detail="Rack name must be 2 lowercase letters")

        # Check uniqueness
        existing = await self.db.execute(
            select(Host).where(Host.rack_name == rack_name, Host.id != host_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Rack name already in use")

        host.rack_name = rack_name
        await self.db.commit()
        await self.db.refresh(host)
        return host

    def _get_ssh_client(self, host: Host) -> SSHClient:
        return SSHClient(
            host=host.ip_address,
            port=host.ssh_port,
            username=host.ssh_user,
            key_path=host.ssh_key_path,
            password=host.ssh_password,
        )

    async def detect_hardware(self, host_id: int) -> Host:
        host = await self.db.get(Host, host_id)
        if not host:
            raise HTTPException(status_code=404, detail="Host not found")

        ssh = self._get_ssh_client(host)
        try:
            async with ssh:
                # Detect OS
                os_type = await self._detect_os(ssh)
                host.os_type = os_type

                # Detect hardware based on OS
                if os_type == OSType.LINUX:
                    await self._detect_linux(ssh, host)
                elif os_type == OSType.MACOS:
                    await self._detect_macos(ssh, host)
                elif os_type == OSType.WINDOWS:
                    await self._detect_windows(ssh, host)

                host.status = HostStatus.ONLINE
        except Exception as e:
            host.status = HostStatus.ERROR
            raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")
        finally:
            await self.db.commit()
            await self.db.refresh(host)

        return host

    async def _detect_os(self, ssh: SSHClient) -> OSType:
        success, output = await ssh.run_safe("uname -s")
        if success:
            if "Linux" in output:
                return OSType.LINUX
            elif "Darwin" in output:
                return OSType.MACOS
        # Try Windows
        success, output = await ssh.run_safe('powershell -Command "$env:OS"')
        if success and "Windows" in output:
            return OSType.WINDOWS
        raise HTTPException(status_code=500, detail="Could not detect OS type")

    async def _detect_linux(self, ssh: SSHClient, host: Host) -> None:
        success, cpu = await ssh.run_safe("nproc")
        if success:
            host.cpu_cores = int(cpu)

        success, ram = await ssh.run_safe("free -m | awk '/^Mem:/{print $2}'")
        if success:
            host.ram_mb = int(ram)

        success, disk = await ssh.run_safe(
            "lsblk -b -d -n -o SIZE | awk '{s+=$1} END {printf \"%.0f\", s/1073741824}'"
        )
        if success:
            host.disk_gb = int(disk)

        success, gw = await ssh.run_safe("ip route | awk '/default/{print $3}'")
        if success:
            host.gateway = gw

        success, subnet = await ssh.run_safe(
            "ip -o -4 addr show $(ip route | awk '/default/{print $5}') | awk '{print $4}'"
        )
        if success:
            host.subnet_mask = subnet

        success, dns = await ssh.run_safe(
            "grep nameserver /etc/resolv.conf | awk '{print $2}' | tr '\\n' ','"
        )
        if success:
            host.dns_servers = dns.rstrip(",")

        # Check bridge
        success, bridge = await ssh.run_safe("ip link show type bridge | head -1 | awk -F: '{print $2}' | tr -d ' '")
        if success and bridge:
            host.bridge_interface = bridge

    async def _detect_macos(self, ssh: SSHClient, host: Host) -> None:
        success, cpu = await ssh.run_safe("sysctl -n hw.ncpu")
        if success:
            host.cpu_cores = int(cpu)

        success, ram = await ssh.run_safe(
            "sysctl -n hw.memsize | awk '{printf \"%.0f\", $1/1048576}'"
        )
        if success:
            host.ram_mb = int(ram)

        success, disk = await ssh.run_safe(
            "diskutil info disk0 | grep 'Disk Size' | awk '{print $3}'"
        )
        if success:
            host.disk_gb = int(float(disk))

        success, gw = await ssh.run_safe(
            "route -n get default | grep gateway | awk '{print $2}'"
        )
        if success:
            host.gateway = gw

        success, subnet = await ssh.run_safe(
            "ifconfig $(route -n get default | grep interface | awk '{print $2}') | grep 'inet ' | awk '{print $4}'"
        )
        if success:
            host.subnet_mask = subnet

        success, dns = await ssh.run_safe(
            "scutil --dns | grep nameserver | awk '{print $3}' | head -3 | tr '\\n' ','"
        )
        if success:
            host.dns_servers = dns.rstrip(",")

    async def _detect_windows(self, ssh: SSHClient, host: Host) -> None:
        success, cpu = await ssh.run_safe(
            'powershell -Command "(Get-WmiObject Win32_Processor).NumberOfLogicalProcessors"'
        )
        if success:
            host.cpu_cores = int(cpu)

        success, ram = await ssh.run_safe(
            'powershell -Command "[math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory/1MB)"'
        )
        if success:
            host.ram_mb = int(ram)

        success, disk = await ssh.run_safe(
            'powershell -Command "[math]::Round((Get-WmiObject Win32_DiskDrive | Measure-Object Size -Sum).Sum/1GB)"'
        )
        if success:
            host.disk_gb = int(disk)

        success, gw = await ssh.run_safe(
            "powershell -Command \"(Get-NetRoute -DestinationPrefix '0.0.0.0/0').NextHop\""
        )
        if success:
            host.gateway = gw

        success, subnet = await ssh.run_safe(
            "powershell -Command \"(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notmatch 'Loopback'} | Select-Object -First 1).PrefixLength\""
        )
        if success:
            host.subnet_mask = subnet

        success, dns = await ssh.run_safe(
            "powershell -Command \"(Get-DnsClientServerAddress -AddressFamily IPv4 | Select-Object -First 1).ServerAddresses -join ','\""
        )
        if success:
            host.dns_servers = dns

    async def check_hypervisor(self, host_id: int) -> HypervisorCheck:
        host = await self.db.get(Host, host_id)
        if not host:
            raise HTTPException(status_code=404, detail="Host not found")

        ssh = self._get_ssh_client(host)
        try:
            async with ssh:
                if host.os_type == OSType.LINUX:
                    return await self._check_linux_hypervisor(ssh, host)
                elif host.os_type == OSType.MACOS:
                    return await self._check_macos_hypervisor(ssh, host)
                elif host.os_type == OSType.WINDOWS:
                    return await self._check_windows_hypervisor(ssh, host)
                else:
                    raise HTTPException(status_code=400, detail="OS type not detected. Run detection first.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hypervisor check failed: {str(e)}")

    async def _check_linux_hypervisor(self, ssh: SSHClient, host: Host) -> HypervisorCheck:
        success, version = await ssh.run_safe("which virsh && virsh version 2>/dev/null | head -1")

        if success and "virsh" in version:
            host.hypervisor_installed = True
            host.hypervisor_type = "kvm"
            await self.db.commit()
            return HypervisorCheck(
                installed=True,
                hypervisor_type="kvm",
                version=version,
            )

        host.hypervisor_installed = False
        await self.db.commit()
        return HypervisorCheck(
            installed=False,
            hypervisor_type="kvm",
            install_commands=[
                "# Debian/Ubuntu:",
                "sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virt-manager cloud-image-utils",
                "sudo systemctl enable --now libvirtd",
                "# RHEL/CentOS/Fedora:",
                "sudo dnf install -y qemu-kvm libvirt virt-install cloud-utils",
                "sudo systemctl enable --now libvirtd",
            ],
        )

    async def _check_macos_hypervisor(self, ssh: SSHClient, host: Host) -> HypervisorCheck:
        success, version = await ssh.run_safe("which multipass && multipass version")
        if success and "multipass" in version:
            host.hypervisor_installed = True
            host.hypervisor_type = "multipass"
            await self.db.commit()
            return HypervisorCheck(
                installed=True,
                hypervisor_type="multipass",
                version=version,
            )

        host.hypervisor_installed = False
        await self.db.commit()
        return HypervisorCheck(
            installed=False,
            hypervisor_type="multipass",
            install_commands=["brew install --cask multipass"],
        )

    async def _check_windows_hypervisor(self, ssh: SSHClient, host: Host) -> HypervisorCheck:
        success, output = await ssh.run_safe(
            'powershell -Command "(Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V).State"'
        )
        if success and "Enabled" in output:
            host.hypervisor_installed = True
            host.hypervisor_type = "hyperv"
            await self.db.commit()
            return HypervisorCheck(
                installed=True,
                hypervisor_type="hyperv",
                version=output,
            )

        host.hypervisor_installed = False
        await self.db.commit()
        return HypervisorCheck(
            installed=False,
            hypervisor_type="hyperv",
            install_commands=[
                'powershell -Command "Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All -NoRestart"',
                "# Restart required after enabling Hyper-V",
            ],
        )

    async def check_bridge(self, host_id: int) -> BridgeCheck:
        host = await self.db.get(Host, host_id)
        if not host:
            raise HTTPException(status_code=404, detail="Host not found")

        ssh = self._get_ssh_client(host)
        try:
            async with ssh:
                if host.os_type == OSType.LINUX:
                    return await self._check_linux_bridge(ssh, host)
                elif host.os_type == OSType.MACOS:
                    return await self._check_macos_bridge(ssh, host)
                elif host.os_type == OSType.WINDOWS:
                    return await self._check_windows_bridge(ssh, host)
                else:
                    raise HTTPException(status_code=400, detail="OS type not detected. Run detection first.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Bridge check failed: {str(e)}")

    async def _check_linux_bridge(self, ssh: SSHClient, host: Host) -> BridgeCheck:
        bridge_name = host.bridge_interface
        if bridge_name:
            success, output = await ssh.run_safe(f"ip link show {bridge_name}")
            if success and output:
                host.bridge_configured = True
                await self.db.commit()
                return BridgeCheck(configured=True, bridge_name=bridge_name, output=output)
        else:
            success, output = await ssh.run_safe("ip -o link show type bridge | awk -F': ' '{print $2}' | head -1")
            if success and output.strip():
                detected = output.strip()
                host.bridge_configured = True
                await self.db.commit()
                return BridgeCheck(configured=True, bridge_name=detected, output=detected)

        host.bridge_configured = False
        await self.db.commit()
        return BridgeCheck(
            configured=False,
            bridge_name=bridge_name,
            setup_commands=[
                "sudo nmcli connection add type bridge con-name br0 ifname br0",
                "sudo nmcli connection add type ethernet slave-type bridge con-name br0-port1 ifname eth0 master br0",
                "sudo nmcli connection up br0",
            ],
        )

    async def _check_macos_bridge(self, ssh: SSHClient, host: Host) -> BridgeCheck:
        bridge_name = host.bridge_interface or "bridge100"
        success, output = await ssh.run_safe(f"ifconfig {bridge_name}")
        if success and output:
            host.bridge_configured = True
            await self.db.commit()
            return BridgeCheck(configured=True, bridge_name=bridge_name, output=output)

        host.bridge_configured = False
        await self.db.commit()
        return BridgeCheck(
            configured=False,
            bridge_name=bridge_name,
            setup_commands=[
                "# Ensure Multipass is installed:",
                "brew install --cask multipass",
                "# Configure the bridged interface (replace en0 with the target physical interface):",
                "multipass set local.bridged-network=en0",
            ],
        )

    async def _check_windows_bridge(self, ssh: SSHClient, host: Host) -> BridgeCheck:
        if host.bridge_interface:
            command = (
                f'powershell -Command "(Get-VMSwitch -Name \'{host.bridge_interface}\' '
                '-ErrorAction SilentlyContinue).Name"'
            )
        else:
            command = (
                'powershell -Command "(Get-VMSwitch -SwitchType External | '
                'Select-Object -First 1).Name"'
            )
        success, output = await ssh.run_safe(command)
        detected = output.strip() if output else ""
        if success and detected:
            host.bridge_configured = True
            await self.db.commit()
            return BridgeCheck(configured=True, bridge_name=detected, output=detected)

        host.bridge_configured = False
        await self.db.commit()
        return BridgeCheck(
            configured=False,
            bridge_name=host.bridge_interface,
            setup_commands=[
                "# Run in an elevated PowerShell session:",
                "New-VMSwitch -Name 'br0' -NetAdapterName 'Ethernet' -AllowManagementOS $true",
            ],
        )
