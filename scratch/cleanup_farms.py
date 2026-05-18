import asyncio
from backend.db.session import AsyncSessionLocal
from backend.models.farm import Farm, Zone, Acre
from backend.models.device import Device
from sqlalchemy import delete, select

async def cleanup_farms():
    async with AsyncSessionLocal() as db:
        # Get all farms for the user (assuming only one user or we just clean up all)
        res = await db.execute(select(Farm).order_by(Farm.created_at.desc()))
        farms = res.scalars().all()
        
        if len(farms) <= 1:
            print("No duplicate farms found.")
            return

        keep_farm = farms[0]
        duplicate_ids = [f.id for f in farms[1:]]
        
        print(f"Keeping farm: {keep_farm.name} ({keep_farm.id})")
        print(f"Deleting {len(duplicate_ids)} duplicate farms...")

        # Delete duplicates (cascades should handle zones/acres but we'll be safe)
        await db.execute(delete(Farm).where(Farm.id.in_(duplicate_ids)))
        await db.commit()
        print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup_farms())
