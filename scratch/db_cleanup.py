import asyncio
from backend.db.session import AsyncSessionLocal
from backend.models.device import Device
from sqlalchemy import delete, select

async def cleanup():
    async with AsyncSessionLocal() as db:
        # Delete devices with no MAC
        await db.execute(delete(Device).where(Device.mac_address == None))
        
        # Ensure Master has no zone_id (it's the farm gateway)
        # Ensure Nodes HAVE zone_ids
        res = await db.execute(select(Device))
        for d in res.scalars():
            if d.mac_address == "28:05:A5:25:4D:78":
                d.is_master = True
                d.zone_id = None # Master is farm-level
            else:
                d.is_master = False
                # Keep existing zone_id if assigned
        
        await db.commit()
        print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup())
