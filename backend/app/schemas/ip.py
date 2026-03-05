from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class IPAllocationResponse(BaseModel):
    id: int
    ip_address: str
    vm_id: Optional[int] = None
    vm_name: Optional[str] = None
    is_reserved: bool
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IPReserve(BaseModel):
    ip_address: str
    notes: Optional[str] = None


class IPAvailableResponse(BaseModel):
    available_ips: list[str]
    total_available: int
    total_range: int
