from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import router
from app.database import get_db
from app.schemas.host import HostCreate, HostResponse, RackNameUpdate, HypervisorCheck

hosts_router = APIRouter(prefix="/hosts", tags=["hosts"])


@hosts_router.get("", response_model=list[HostResponse])
async def list_hosts(db: AsyncSession = Depends(get_db)):
    from app.services.host_service import HostService
    service = HostService(db)
    return await service.list_hosts()


@hosts_router.get("/{host_id}", response_model=HostResponse)
async def get_host(host_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.host_service import HostService
    service = HostService(db)
    host = await service.get_host(host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


@hosts_router.post("", response_model=HostResponse)
async def create_host(data: HostCreate, db: AsyncSession = Depends(get_db)):
    from app.services.host_service import HostService
    service = HostService(db)
    return await service.create_host(data)


@hosts_router.delete("/{host_id}")
async def delete_host(host_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.host_service import HostService
    service = HostService(db)
    await service.delete_host(host_id)
    return {"status": "deleted"}


@hosts_router.post("/{host_id}/detect", response_model=HostResponse)
async def detect_host(host_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.host_service import HostService
    service = HostService(db)
    return await service.detect_hardware(host_id)


@hosts_router.post("/{host_id}/check-hypervisor", response_model=HypervisorCheck)
async def check_hypervisor(host_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.host_service import HostService
    service = HostService(db)
    return await service.check_hypervisor(host_id)


@hosts_router.put("/{host_id}/rack-name", response_model=HostResponse)
async def update_rack_name(host_id: int, data: RackNameUpdate, db: AsyncSession = Depends(get_db)):
    from app.services.host_service import HostService
    service = HostService(db)
    return await service.update_rack_name(host_id, data.rack_name)


router.include_router(hosts_router)
