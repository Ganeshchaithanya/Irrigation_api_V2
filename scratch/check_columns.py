import asyncio
import os
import sys
from sqlalchemy import text

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.db.session import engine

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'sensor_readings'"))
        cols = [r[0] for r in res.all()]
        print("Columns in sensor_readings:")
        print(", ".join(cols))

if __name__ == "__main__":
    asyncio.run(check())
