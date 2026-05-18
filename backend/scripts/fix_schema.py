
import asyncio
from sqlalchemy import text
from backend.db.session import AsyncSessionLocal

async def fix_schema():
    async with AsyncSessionLocal() as session:
        await session.execute(text("ALTER TABLE sensor_readings ALTER COLUMN zone_id DROP NOT NULL;"))
        await session.commit()
        print("Schema updated: zone_id is now nullable in sensor_readings.")

if __name__ == "__main__":
    asyncio.run(fix_schema())
