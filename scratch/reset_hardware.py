import asyncio
from backend.db.session import AsyncSessionLocal
from sqlalchemy import text

async def reset_hardware():
    async with AsyncSessionLocal() as db:
        print("Factory resetting all hardware to 'discovery' mode...")
        await db.execute(text("UPDATE devices SET status = 'discovery', farm_id = NULL, zone_id = NULL"))
        await db.commit()
        print("Reset complete! All hardware is now Unassigned.")

if __name__ == "__main__":
    asyncio.run(reset_hardware())
