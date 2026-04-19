from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.api import router
from app.database import get_db
from app.schemas.vm import VMCreate, VMResponse, VMsByRack, VMReadiness

vms_router = APIRouter(prefix="/vms", tags=["vms"])


@vms_router.get("", response_model=list[VMResponse])
async def list_vms(
    host_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    cluster_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    from app.services.vm_service import VMService
    service = VMService(db)
    return await service.list_vms(host_id=host_id, status=status, cluster_id=cluster_id)


@vms_router.get("/by-rack", response_model=list[VMsByRack])
async def vms_by_rack(db: AsyncSession = Depends(get_db)):
    from app.services.vm_service import VMService
    service = VMService(db)
    return await service.get_vms_by_rack()


@vms_router.get("/{vm_id}", response_model=VMResponse)
async def get_vm(vm_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.vm_service import VMService
    service = VMService(db)
    vm = await service.get_vm(vm_id)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    return vm


@vms_router.post("", response_model=VMResponse)
async def create_vm(data: VMCreate, db: AsyncSession = Depends(get_db)):
    from app.services.vm_service import VMService
    service = VMService(db)
    return await service.create_vm(data)


@vms_router.post("/{vm_id}/start", response_model=VMResponse)
async def start_vm(vm_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.vm_service import VMService
    service = VMService(db)
    return await service.start_vm(vm_id)


@vms_router.post("/{vm_id}/stop", response_model=VMResponse)
async def stop_vm(vm_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.vm_service import VMService
    service = VMService(db)
    return await service.stop_vm(vm_id)


@vms_router.delete("/{vm_id}")
async def delete_vm(vm_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.vm_service import VMService
    service = VMService(db)
    await service.delete_vm(vm_id)
    return {"status": "deleted"}


@vms_router.post("/{vm_id}/refresh", response_model=VMResponse)
async def refresh_vm(vm_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.vm_service import VMService
    service = VMService(db)
    return await service.refresh_vm_status(vm_id)


@vms_router.get("/{vm_id}/readiness", response_model=VMReadiness)
async def vm_readiness(vm_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.vm_service import VMService
    service = VMService(db)
    return await service.check_readiness(vm_id)


router.include_router(vms_router)
