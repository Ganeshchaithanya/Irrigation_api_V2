"""
truncate_all.py - Delete all rows from all tables in correct FK-safe order.
"""
import asyncio, os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv()
url = os.getenv("DATABASE_URL", "").split("?")[0].replace("postgresql://", "postgresql+asyncpg://")

# Order matters: child tables first, then parent tables
ORDERED_TABLES = [
    "sensor_readings",
    "valve_commands",
    "decision_log",
    "zone_state",
    "diary_entries",
    "crop_plans",
    "schedules",
    "pairing_sessions",
    "devices",
    "crop_bio_profiles",
    "zones",
    "acres",
    "farms",
    "message_templates",
    "users",
]

async def truncate_all():
    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        for table in ORDERED_TABLES:
            result = await conn.execute(text(f'DELETE FROM "{table}"'))
            print(f"  Cleared  {table:<30} ({result.rowcount} rows deleted)")
    await engine.dispose()
    print("\nAll tables cleared successfully.")

asyncio.run(truncate_all())
