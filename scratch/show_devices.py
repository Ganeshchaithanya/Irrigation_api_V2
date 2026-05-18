import asyncio
from backend.db.session import AsyncSessionLocal
from sqlalchemy import text

async def show_devices():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT mac_address, node_label, is_master, status, zone_id FROM devices"))
        print("\n--- Current Devices in Database ---")
        for r in res.all():
            node_type = "Master Gateway" if r.is_master else "Irrigation Node"
            zone_info = f" (Zone: {r.zone_id})" if r.zone_id else " (Unassigned)"
            print(f"[{node_type}] MAC: {r.mac_address} | Label: {r.node_label} | Status: {r.status}{zone_info}")

if __name__ == "__main__":
    asyncio.run(show_devices())
