import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

# Load env from root
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.split("?")[0]
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

async def dump_farms():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        print("--- Farms Data ---")
        result = await conn.execute(text("SELECT id, name FROM farms"))
        rows = result.fetchall()
        for row in rows:
            print(f"ID: {row[0]} | Name: {row[1]}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(dump_farms())
