from pydantic import BaseModel
from typing import Optional


class WGPeerCreate(BaseModel):
    datacenter_code: str
    public_key: str
    endpoint: str
    allowed_ips: str
    comment: Optional[str] = None


class WGPeerResponse(BaseModel):
    datacenter_code: str
    public_key: str
    endpoint: str
    allowed_ips: str
    comment: Optional[str] = None
    latest_handshake: Optional[str] = None
    transfer_rx: Optional[str] = None
    transfer_tx: Optional[str] = None


class WGStatusResponse(BaseModel):
    interface: str
    public_key: str
    listen_port: int
    address: str
    is_up: bool
    peers: list[WGPeerResponse] = []
