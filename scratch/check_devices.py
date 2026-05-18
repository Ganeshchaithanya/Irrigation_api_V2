import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.split("?")[0]
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

async def check_devices():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        print("Devices in DB:")
        result = await conn.execute(text("SELECT id, mac_address, node_label, role FROM devices"))
        for row in result.fetchall():
            print(f"ID: {row[0]}, MAC: {row[1]}, Label: {row[2]}, Role: {row[3]}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_devices())
