import asyncio
import json
from sqlalchemy import select
from backend.db.session import AsyncSessionLocal
from backend.models.user import User
from backend.models.farm import Farm, Zone
from backend.models.device import Device

async def check_data():
    async with AsyncSessionLocal() as db:
        # Check Users
        res = await db.execute(select(User))
        users = res.scalars().all()
        print(f"Users: {[{'id': u.id, 'phone': u.phone} for u in users]}")

        # Check Farms
        res = await db.execute(select(Farm))
        farms = res.scalars().all()
        print(f"Farms: {[{'name': f.name, 'user_id': f.user_id} for f in farms]}")

        # Check Zones
        res = await db.execute(select(Zone))
        zones = res.scalars().all()
        print(f"Zones: {[{'name': z.name, 'farm_id': z.farm_id} for z in zones]}")

if __name__ == "__main__":
    asyncio.run(check_data())
