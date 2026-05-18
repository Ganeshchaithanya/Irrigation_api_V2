import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from backend.config.settings import get_settings

engine = create_async_engine(get_settings().DATABASE_URL)

async def fix():
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM crop_plans WHERE farm_id IS NULL"))

asyncio.run(fix())
