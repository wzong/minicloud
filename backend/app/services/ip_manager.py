import ipaddress
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.ip_allocation import IPAllocation
from app.models.vm import VM
from app.config import settings


class IPManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _ip_range(self) -> list[str]:
        start = ipaddress.IPv4Address(settings.ip_range_start)
        end = ipaddress.IPv4Address(settings.ip_range_end)
        return [str(ipaddress.IPv4Address(ip)) for ip in range(int(start), int(end) + 1)]

    async def allocate(self, vm_id: int) -> str:
        result = await self.db.execute(select(IPAllocation.ip_address))
        used = {row[0] for row in result.fetchall()}

        for ip in self._ip_range():
            if ip not in used:
                alloc = IPAllocation(ip_address=ip, vm_id=vm_id)
                self.db.add(alloc)
                await self.db.flush()
                return ip

        raise HTTPException(status_code=400, detail="No available IP addresses")

    async def release(self, ip_address: str) -> None:
        result = await self.db.execute(
            select(IPAllocation).where(IPAllocation.ip_address == ip_address)
        )
        alloc = result.scalar_one_or_none()
        if alloc:
            await self.db.delete(alloc)
            await self.db.flush()

    async def is_available(self, ip_address: str) -> bool:
        result = await self.db.execute(
            select(IPAllocation).where(IPAllocation.ip_address == ip_address)
        )
        return result.scalar_one_or_none() is None

    async def list_allocations(self) -> list[dict]:
        result = await self.db.execute(
            select(IPAllocation, VM.name)
            .outerjoin(VM, IPAllocation.vm_id == VM.id)
            .order_by(IPAllocation.ip_address)
        )
        allocations = []
        for alloc, vm_name in result.all():
            allocations.append({
                "id": alloc.id,
                "ip_address": alloc.ip_address,
                "vm_id": alloc.vm_id,
                "vm_name": vm_name,
                "is_reserved": alloc.is_reserved,
                "notes": alloc.notes,
                "created_at": alloc.created_at,
            })
        return allocations

    async def get_available(self) -> dict:
        result = await self.db.execute(select(IPAllocation.ip_address))
        used = {row[0] for row in result.fetchall()}
        all_ips = self._ip_range()
        available = [ip for ip in all_ips if ip not in used]
        return {
            "available_ips": available,
            "total_available": len(available),
            "total_range": len(all_ips),
        }

    async def reserve(self, ip_address: str, notes: str | None = None) -> IPAllocation:
        if not await self.is_available(ip_address):
            raise HTTPException(status_code=400, detail="IP address already allocated")

        alloc = IPAllocation(ip_address=ip_address, is_reserved=True, notes=notes)
        self.db.add(alloc)
        await self.db.commit()
        await self.db.refresh(alloc)
        return alloc

    async def unreserve(self, ip_address: str) -> None:
        result = await self.db.execute(
            select(IPAllocation).where(
                IPAllocation.ip_address == ip_address,
                IPAllocation.is_reserved == True,
            )
        )
        alloc = result.scalar_one_or_none()
        if not alloc:
            raise HTTPException(status_code=404, detail="Reserved IP not found")
        await self.db.delete(alloc)
        await self.db.commit()
