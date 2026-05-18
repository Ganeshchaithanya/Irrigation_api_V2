import asyncio
from sqlalchemy import select
from backend.models.device import Device
from backend.models.pairing_session import PairingSession
from backend.db.session import AsyncSessionLocal

async def check_db():
    async with AsyncSessionLocal() as db:
        print("--- DEVICES ---")
        res = await db.execute(select(Device))
        devices = res.scalars().all()
        for d in devices:
            print(f"ID: {d.id}")
            print(f"  MAC:      {d.mac_address}")
            print(f"  Code:     {d.pairing_code}")
            print(f"  Farm:     {d.farm_id}")
            print(f"  Slot:     {d.node_slot_id}")
            print(f"  Status:   {d.status}")
            print(f"  Role:     {d.role}")
            print(f"  Claimed:  {d.is_claimed}")
            print("-" * 20)
        
        print("\n--- PAIRING SESSIONS ---")
        res = await db.execute(select(PairingSession))
        sessions = res.scalars().all()
        for s in sessions:
            print(f"ID: {s.id}")
            print(f"  Code:     {s.pairing_code}")
            print(f"  Farm:     {s.farm_id}")
            print(f"  Used:     {s.is_used}")
            print(f"  Expires:  {s.expires_at}")
            print(f"  Slot:     {s.node_slot_id}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(check_db())
