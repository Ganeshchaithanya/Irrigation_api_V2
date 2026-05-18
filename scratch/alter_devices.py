
import asyncio
from sqlalchemy import text
from backend.db.session import engine

async def alter():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE devices ALTER COLUMN farm_id DROP NOT NULL"))
        print("SUCCESS")

if __name__ == "__main__":
    asyncio.run(alter())
