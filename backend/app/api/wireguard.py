from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import router
from app.database import get_db
from app.schemas.wireguard import WGPeerCreate, WGPeerResponse, WGStatusResponse

wg_router = APIRouter(prefix="/wireguard", tags=["wireguard"])


@wg_router.get("/status", response_model=WGStatusResponse)
async def get_status():
    from app.services.wireguard_service import WireGuardService
    service = WireGuardService()
    return await service.get_status()


@wg_router.get("/public-key")
async def get_public_key():
    from app.services.wireguard_service import WireGuardService
    service = WireGuardService()
    return await service.get_public_key()


@wg_router.get("/peers", response_model=list[WGPeerResponse])
async def list_peers():
    from app.services.wireguard_service import WireGuardService
    service = WireGuardService()
    return await service.list_peers()


@wg_router.post("/peers", response_model=WGPeerResponse)
async def add_peer(data: WGPeerCreate):
    from app.services.wireguard_service import WireGuardService
    service = WireGuardService()
    return await service.add_peer(data)


@wg_router.delete("/peers/{datacenter_code}")
async def remove_peer(datacenter_code: str):
    from app.services.wireguard_service import WireGuardService
    service = WireGuardService()
    await service.remove_peer(datacenter_code)
    return {"status": "removed"}


@wg_router.post("/reload")
async def reload():
    from app.services.wireguard_service import WireGuardService
    service = WireGuardService()
    await service.regenerate_config()
    return {"status": "reloaded"}


router.include_router(wg_router)
