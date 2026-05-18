import asyncio
from sqlalchemy import text
from backend.db.session import engine

async def force_truncate():
    async with engine.begin() as conn:
        print("Force truncating all tables...")
        # Order doesn't strictly matter with CASCADE, but let's be thorough
        sql = """
        TRUNCATE TABLE 
            diary_entries, 
            sensor_readings, 
            valve_commands, 
            decision_log, 
            crop_plans, 
            zone_state, 
            devices, 
            zones, 
            farms, 
            users 
        RESTART IDENTITY CASCADE;
        """
        try:
            await conn.execute(text(sql))
            print("Successfully truncated all tables.")
        except Exception as e:
            print(f"Error during truncation: {e}")

if __name__ == "__main__":
    asyncio.run(force_truncate())
