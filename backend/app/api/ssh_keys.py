from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import router
from app.database import get_db
from app.schemas.ssh_key import SSHKeyGenerate, SSHKeyImport, SSHKeyResponse

ssh_keys_router = APIRouter(prefix="/ssh-keys", tags=["ssh-keys"])


@ssh_keys_router.get("", response_model=list[SSHKeyResponse])
async def list_ssh_keys(db: AsyncSession = Depends(get_db)):
    from app.services.ssh_key_service import SSHKeyService
    service = SSHKeyService(db)
    return await service.list_keys()


@ssh_keys_router.post("/generate", response_model=SSHKeyResponse)
async def generate_ssh_key(data: SSHKeyGenerate, db: AsyncSession = Depends(get_db)):
    from app.services.ssh_key_service import SSHKeyService
    service = SSHKeyService(db)
    return await service.generate_key(data.name)


@ssh_keys_router.post("/import", response_model=SSHKeyResponse)
async def import_ssh_key(data: SSHKeyImport, db: AsyncSession = Depends(get_db)):
    from app.services.ssh_key_service import SSHKeyService
    service = SSHKeyService(db)
    return await service.import_key(data.name, data.private_key)


@ssh_keys_router.delete("/{key_id}")
async def delete_ssh_key(key_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.ssh_key_service import SSHKeyService
    service = SSHKeyService(db)
    await service.delete_key(key_id)
    return {"status": "deleted"}


router.include_router(ssh_keys_router)
