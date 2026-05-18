
import asyncio
from sqlalchemy import select, desc
from backend.db.session import AsyncSessionLocal as SessionLocal
from backend.models.sensor_data import SensorReading
from backend.models.device import Device

async def check():
    async with SessionLocal() as db:
        res = await db.execute(
            select(SensorReading, Device.mac_address)
            .join(Device, Device.id == SensorReading.device_id)
            .order_by(desc(SensorReading.time))
            .limit(20)
        )
        rows = res.all()
        print(f"{'TIME':<25} | {'MAC':<20} | {'MOISTURE':<10}")
        print("-" * 60)
        for r, mac in rows:
            t_str = str(r.time) if r.time else "N/A"
            m_val = str(r.soil_moisture) if r.soil_moisture is not None else "NULL"
            print(f"{t_str:<25} | {mac:<20} | {m_val:<10}")

if __name__ == "__main__":
    asyncio.run(check())
