import asyncio
from sqlalchemy import text
from backend.db.session import engine

async def truncate_tables():
    tables = [
        "diary_entries",
        "sensor_readings",
        "valve_commands",
        "decision_log",
        "crop_plans",
        "zone_state",
        "devices",
        "zones",
        "farms",
        "users"
    ]
    
    async with engine.begin() as conn:
        print("Truncating tables...")
        for table in tables:
            try:
                await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
                print(f"  - {table} truncated.")
            except Exception as e:
                print(f"  - Error truncating {table}: {e}")
        print("Done.")

if __name__ == "__main__":
    asyncio.run(truncate_tables())
