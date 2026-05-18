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

async def check_data():
    async with AsyncSessionLocal() as db:
        for mac in ["E0:8C:FE:34:1B:18", "28:05:A5:25:4D:78"]:
            print(f"--- DATA FOR NODE {mac} ---")
            res = await db.execute(
                select(SensorReading)
                .join(Device, Device.id == SensorReading.device_id)
                .where(Device.mac_address == mac)
                .order_by(desc(SensorReading.time))
                .limit(3)
            )
            rows = res.scalars().all()
            if not rows:
                print("No data found for this node.")
            for r in rows:
                print(f"Time: {r.time} | Moist: {r.soil_moisture}% | Temp: {r.temperature}C")

if __name__ == "__main__":
    asyncio.run(check_data())
