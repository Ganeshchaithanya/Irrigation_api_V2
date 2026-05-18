import asyncio
from backend.db.session import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        users = await db.execute(text("SELECT id, name, phone FROM users"))
        print("\n--- Users ---")
        for u in users:
            print(f"ID: {u.id} | Name: {u.name} | Phone: {u.phone}")
            
        farms = await db.execute(text("SELECT id, name, user_id FROM farms"))
        print("\n--- Farms ---")
        for f in farms:
            print(f"ID: {f.id} | Name: {f.name} | Owner ID: {f.user_id}")
            
        devices = await db.execute(text("SELECT mac_address, farm_id, zone_id, node_label FROM devices"))
        print("\n--- Devices ---")
        for d in devices:
            print(f"MAC: {d.mac_address} | Farm ID: {d.farm_id} | Zone ID: {d.zone_id} | Label: {d.node_label}")

if __name__ == "__main__":
    asyncio.run(check())
