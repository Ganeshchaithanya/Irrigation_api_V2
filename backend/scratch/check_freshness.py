import asyncio
from sqlalchemy import select
from backend.models.device import Device
from backend.db.session import AsyncSessionLocal
from datetime import datetime, timezone

async def check_freshness():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Device))
        devices = res.scalars().all()
        now = datetime.now(timezone.utc)
        print(f"Current Time: {now}")
        for d in devices:
            if d.mac_address:
                ago = (now - d.last_seen_at).total_seconds() if d.last_seen_at else "Never"
                print(f"Device: {d.mac_address} ({d.role}) - Status: {d.status} - Last Seen: {ago}s ago")

if __name__ == "__main__":
    asyncio.run(check_freshness())
