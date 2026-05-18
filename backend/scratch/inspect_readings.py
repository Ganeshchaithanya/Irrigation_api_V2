import asyncio
import socket
from backend.db.session import AsyncSessionLocal
from backend.models.sensor_data import SensorReading
from backend.models.device import Device
from sqlalchemy import select, desc

# DNS Monkeypatch
_original_getaddrinfo = socket.getaddrinfo
def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "ep-restless-meadow-a1l64nqq-pooler.ap-southeast-1.aws.neon.tech":
        return _original_getaddrinfo("13.228.46.236", port, family, type, proto, flags)
    return _original_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _patched_getaddrinfo

async def inspect_readings():
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(SensorReading, Device.mac_address)
            .join(Device, Device.id == SensorReading.device_id)
            .order_by(desc(SensorReading.time))
            .limit(5)
        )
        rows = res.all()
        for r, mac in rows:
            print(f"--- READING AT {r.time} (MAC: {mac}) ---")
            print(f"Soil Moisture: {r.soil_moisture}")
            print(f"Temperature: {r.temperature}")
            print(f"Humidity: {r.humidity}")
            print(f"Battery: {r.battery_pct}")
            print(f"Solar: {r.solar_pct}")
            print(f"Flow Rate: {r.flow_rate}")
            print(f"Raw Payload: {r.raw_payload}")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(inspect_readings())
