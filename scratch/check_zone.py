import asyncio
from backend.db.session import AsyncSessionLocal
from backend.models.farm import Zone
from sqlalchemy import select
import uuid

async def check():
    async with AsyncSessionLocal() as db:
        zone_id = uuid.UUID('5e030a69-2c41-423a-ab19-ea847a5b5600')
        res = await db.execute(select(Zone).where(Zone.id == zone_id))
        zone = res.scalar_one_or_none()
        if zone:
            print(f"Zone: {zone.name}, Status: {zone.status}, FarmID: {zone.farm_id}")
        else:
            print("Zone not found")

if __name__ == "__main__":
    asyncio.run(check())
