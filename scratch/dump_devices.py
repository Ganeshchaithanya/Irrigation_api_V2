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

async def dump_devices():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        print("--- Devices Data ---")
        result = await conn.execute(text("SELECT id, mac_address, node_label, is_master, farm_id FROM devices"))
        rows = result.fetchall()
        for row in rows:
            print(f"ID: {row[0]} | MAC: {row[1]} | Label: {row[2]} | Master: {row[3]} | Farm: {row[4]}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(dump_devices())
