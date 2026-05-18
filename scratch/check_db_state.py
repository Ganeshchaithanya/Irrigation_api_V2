import asyncio
import uuid
from backend.db.session import AsyncSessionLocal
from sqlalchemy import text
from backend.models.farm import Farm, Zone, Acre
from backend.models.device import Device

async def check_db():
    async with AsyncSessionLocal() as db:
        farms = (await db.execute(text("SELECT id, name FROM farms"))).all()
        zones = (await db.execute(text("SELECT id, name FROM zones"))).all()
        devices = (await db.execute(text("SELECT id, mac_address, farm_id FROM devices"))).all()
        
        print(f"Farms: {len(farms)}")
        for f in farms: print(f" - {f.name} ({f.id})")
        
        print(f"Zones: {len(zones)}")
        for z in zones: print(f" - {z.name} ({z.id})")
        
        print(f"Devices: {len(devices)}")
        for d in devices: print(f" - {d.mac_address} (Farm: {d.farm_id})")

if __name__ == "__main__":
    asyncio.run(check_db())
