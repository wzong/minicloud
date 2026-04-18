from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SSHKeyGenerate(BaseModel):
    name: str


class SSHKeyImport(BaseModel):
    name: str
    private_key: str


class SSHKeyResponse(BaseModel):
    id: int
    name: str
    public_key: str
    private_key_path: str
    fingerprint: str
    created_at: datetime

    model_config = {"from_attributes": True}
