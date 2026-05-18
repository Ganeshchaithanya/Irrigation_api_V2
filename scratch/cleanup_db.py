import asyncio
from backend.db.session import AsyncSessionLocal
from sqlalchemy import text

async def cleanup():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("DELETE FROM devices WHERE mac_address IS NULL"))
        await db.commit()
        print(f"Deleted {res.rowcount} phantom devices.")

if __name__ == "__main__":
    asyncio.run(cleanup())
