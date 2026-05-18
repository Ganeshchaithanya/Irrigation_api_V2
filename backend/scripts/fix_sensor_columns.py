import asyncio
import sys
import os
from sqlalchemy import text

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.db.session import engine

async def fix_columns():
    print("Fixing sensor_readings columns...")
    
    renames = [
        ("total_water_used", "total_water"),
        ("battery_percentage", "battery_pct"),
        ("solar_percentage", "solar_pct"),
        ("is_valve_open", "valve_status"),
    ]
    
    for old, new in renames:
        async with engine.begin() as conn:
            try:
                await conn.execute(text(f"ALTER TABLE sensor_readings RENAME COLUMN {old} TO {new};"))
                print(f"Renamed {old} -> {new}")
            except Exception as e:
                print(f"Skipped {old} -> {new}: {e}")

    print("Fix complete.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_columns())
