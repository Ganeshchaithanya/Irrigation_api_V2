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
        # Check Master readings
        print("--- MASTER GATEWAY DATA ---")
        master_res = await db.execute(
            select(SensorReading, Device.mac_address)
            .join(Device, Device.id == SensorReading.device_id)
            .where(Device.is_master == True)
            .order_by(desc(SensorReading.time))
            .limit(5)
        )
        masters = master_res.all()
        if not masters:
            print("No master data found.")
        for r, mac in masters:
            print(f"Time: {r.time} | MAC: {mac} | Flow: {r.flow_rate} | Rain: {r.rain_detected} | Bat: {r.battery_pct}%")

        # Check Node readings
        print("\n--- NODE SENSOR DATA ---")
        node_res = await db.execute(
            select(SensorReading, Device.mac_address, Device.node_label)
            .join(Device, Device.id == SensorReading.device_id)
            .where(Device.is_master == False)
            .order_by(desc(SensorReading.time))
            .limit(5)
        )
        nodes = node_res.all()
        if not nodes:
            print("No node data found.")
        for r, mac, label in nodes:
            print(f"Time: {r.time} | MAC: {mac} | Label: {label} | Moist: {r.soil_moisture}% | Temp: {r.temperature}C")

if __name__ == "__main__":
    asyncio.run(check_data())
