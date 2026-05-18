import asyncio
import os
import sys
from sqlalchemy import text

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.db.session import engine

async def fix():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE sensor_readings ADD COLUMN IF NOT EXISTS solar_voltage NUMERIC(5, 2)"))
            print("Added solar_voltage column.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(fix())
