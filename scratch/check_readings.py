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

async def check_readings():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        print("Latest 5 Sensor Readings:")
        result = await conn.execute(text("SELECT time, device_id, soil_moisture, temperature, humidity FROM sensor_readings ORDER BY time DESC LIMIT 5"))
        for row in result.fetchall():
            print(f"Time: {row[0]}, Device: {row[1]}, Moisture: {row[2]}, Temp: {row[3]}, Hum: {row[4]}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_readings())
