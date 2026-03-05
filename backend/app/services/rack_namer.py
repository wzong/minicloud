from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.host import Host


async def get_next_rack_name(db: AsyncSession) -> str:
    """Generate next available rack name (aa, ab, ..., az, ba, ..., zz)."""
    result = await db.execute(select(Host.rack_name))
    used_names = {row[0] for row in result.fetchall()}

    for first in range(26):
        for second in range(26):
            name = chr(ord('a') + first) + chr(ord('a') + second)
            if name not in used_names:
                return name

    raise ValueError("All 676 rack names exhausted")
