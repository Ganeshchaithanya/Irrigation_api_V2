import asyncio
from backend.db.session import engine
from backend.db.base import Base

async def clean():
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("Database Reset Complete.")

if __name__ == "__main__":
    asyncio.run(clean())
