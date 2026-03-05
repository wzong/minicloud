from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class HostCreate(BaseModel):
    ip_address: str
    ssh_port: int = 22
    ssh_user: str = "root"
    ssh_key_path: Optional[str] = None
    ssh_password: Optional[str] = None


class HostUpdate(BaseModel):
    ssh_port: Optional[int] = None
    ssh_user: Optional[str] = None
    ssh_key_path: Optional[str] = None
    ssh_password: Optional[str] = None


class RackNameUpdate(BaseModel):
    rack_name: str


class HostResponse(BaseModel):
    id: int
    ip_address: str
    ssh_port: int
    ssh_user: str
    rack_name: str
    os_type: Optional[str] = None
    status: str
    cpu_cores: Optional[int] = None
    ram_mb: Optional[int] = None
    disk_gb: Optional[int] = None
    gateway: Optional[str] = None
    subnet_mask: Optional[str] = None
    dns_servers: Optional[str] = None
    bridge_interface: Optional[str] = None
    hypervisor_installed: bool
    hypervisor_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HypervisorCheck(BaseModel):
    installed: bool
    hypervisor_type: Optional[str] = None
    version: Optional[str] = None
    install_commands: Optional[list[str]] = None
    bridge_status: Optional[dict] = None
