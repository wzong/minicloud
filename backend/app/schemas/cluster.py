from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ClusterCreate(BaseModel):
    name: str
    control_plane_count: int = 1
    worker_count: int = 2
    cpu_cores: int = 2
    ram_mb: int = 2048
    disk_gb: int = 20
    os_image: str = "ubuntu-22.04"
    k3s_version: str = "stable"
    ssh_key_id: int
    host_ids: Optional[list[int]] = None


class ClusterPreview(BaseModel):
    distribution: dict[str, dict[str, int]]
    total_vms: int
    total_cpu: int
    total_ram_mb: int
    total_disk_gb: int


class NodeAdd(BaseModel):
    role: str = "worker"
    count: int = 1
    host_id: Optional[int] = None


class ClusterNodeResponse(BaseModel):
    id: int
    cluster_id: int
    vm_id: int
    role: str
    status: str
    vm_name: Optional[str] = None
    vm_ip: Optional[str] = None
    host_ip: Optional[str] = None
    rack_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ClusterResponse(BaseModel):
    id: int
    name: str
    status: str
    k3s_version: str
    control_plane_count: int = 0
    worker_count: int = 0
    created_at: datetime
    updated_at: datetime
    nodes: list[ClusterNodeResponse] = []

    model_config = {"from_attributes": True}


class ClusterStatusResponse(BaseModel):
    status: str
    message: str
    progress: Optional[int] = None
