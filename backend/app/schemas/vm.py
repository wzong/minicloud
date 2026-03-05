from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class VMCreate(BaseModel):
    host_id: Optional[int] = None
    cpu_cores: int = 2
    ram_mb: int = 2048
    disk_gb: int = 20
    os_image: str = "ubuntu-22.04"
    ssh_key_id: Optional[int] = None


class VMResponse(BaseModel):
    id: int
    name: str
    host_id: int
    ip_address: str
    status: str
    cpu_cores: int
    ram_mb: int
    disk_gb: int
    os_image: str
    ssh_key_id: Optional[int] = None
    rack_sequence: int
    created_at: datetime
    updated_at: datetime
    host_ip: Optional[str] = None
    rack_name: Optional[str] = None
    cluster_name: Optional[str] = None

    model_config = {"from_attributes": True}


class VMListResponse(BaseModel):
    vms: list[VMResponse]
    total: int


class VMsByRack(BaseModel):
    rack_name: str
    host_ip: str
    vms: list[VMResponse]
