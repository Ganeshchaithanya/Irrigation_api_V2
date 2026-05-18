import asyncio
from sqlalchemy import select
from backend.models.farm import Zone, NodeSlot
from backend.db.session import AsyncSessionLocal

async def check_slots():
    async with AsyncSessionLocal() as db:
        print("--- NODE SLOTS ---")
        res = await db.execute(select(NodeSlot))
        slots = res.scalars().all()
        for s in slots:
            print(f"Slot ID: {s.id}, Name: {s.name}, Zone ID: {s.zone_id}")
        
        print("\n--- ZONES ---")
        res = await db.execute(select(Zone))
        zones = res.scalars().all()
        for z in zones:
            print(f"Zone ID: {z.id}, Name: {z.name}, Farm ID: {z.farm_id}")

if __name__ == "__main__":
    asyncio.run(check_slots())
