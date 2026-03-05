from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class VMSpec:
    name: str
    cpu_cores: int
    ram_mb: int
    disk_gb: int
    os_image: str
    ip_address: str
    subnet_mask: str
    gateway: str
    dns_servers: list[str]
    ssh_public_key: Optional[str] = None
    bridge: str = "br0"
    routes: list[dict] | None = None


@dataclass
class VMInfo:
    name: str
    state: str
    cpu_cores: int = 0
    ram_mb: int = 0
    ip_address: str = ""


class HypervisorDriver(ABC):
    def __init__(self, ssh_client):
        self.ssh = ssh_client

    @abstractmethod
    async def create_vm(self, spec: VMSpec) -> None:
        pass

    @abstractmethod
    async def delete_vm(self, vm_name: str) -> None:
        pass

    @abstractmethod
    async def start_vm(self, vm_name: str) -> None:
        pass

    @abstractmethod
    async def stop_vm(self, vm_name: str) -> None:
        pass

    @abstractmethod
    async def get_vm_info(self, vm_name: str) -> VMInfo:
        pass

    @abstractmethod
    async def list_vms(self) -> list[VMInfo]:
        pass
