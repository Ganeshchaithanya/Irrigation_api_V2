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

async def check_all_readings():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        print("Detailed Readings:")
        result = await conn.execute(text("""
            SELECT r.time, d.mac_address, r.soil_moisture, r.solar_voltage, r.battery_pct, r.flow_rate 
            FROM sensor_readings r
            JOIN devices d ON r.device_id = d.id
            ORDER BY r.time DESC LIMIT 20
        """))
        for row in result.fetchall():
            print(f"Time: {row[0]}, MAC: {row[1]}, Soil: {row[2]}, SolV: {row[3]}, Bat: {row[4]}, Flow: {row[5]}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_all_readings())
