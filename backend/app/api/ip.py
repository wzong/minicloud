from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import router
from app.config import settings
from app.database import get_db
from app.schemas.ip import IPAllocationResponse, IPReserve, IPAvailableResponse, IPConfigResponse

ip_router = APIRouter(prefix="/ip", tags=["ip"])


@ip_router.get("/config", response_model=IPConfigResponse)
async def get_config():
    return IPConfigResponse(
        range_start=settings.ip_range_start,
        range_end=settings.ip_range_end,
        subnet_mask=settings.ip_subnet_mask,
        gateway=settings.ip_gateway,
        dns=settings.dns_servers,
    )


@ip_router.get("/allocations", response_model=list[IPAllocationResponse])
async def list_allocations(db: AsyncSession = Depends(get_db)):
    from app.services.ip_manager import IPManager
    manager = IPManager(db)
    return await manager.list_allocations()


@ip_router.get("/available", response_model=IPAvailableResponse)
async def get_available(db: AsyncSession = Depends(get_db)):
    from app.services.ip_manager import IPManager
    manager = IPManager(db)
    return await manager.get_available()


@ip_router.post("/reserve", response_model=IPAllocationResponse)
async def reserve_ip(data: IPReserve, db: AsyncSession = Depends(get_db)):
    from app.services.ip_manager import IPManager
    manager = IPManager(db)
    return await manager.reserve(data.ip_address, data.notes)


@ip_router.delete("/reserve/{ip_address}")
async def unreserve_ip(ip_address: str, db: AsyncSession = Depends(get_db)):
    from app.services.ip_manager import IPManager
    manager = IPManager(db)
    await manager.unreserve(ip_address)
    return {"status": "released"}


router.include_router(ip_router)
