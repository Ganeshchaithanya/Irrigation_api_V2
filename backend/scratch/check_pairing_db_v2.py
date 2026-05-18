import asyncio
from sqlalchemy import select
from backend.models.device import Device
from backend.models.pairing_session import PairingSession
from backend.db.session import AsyncSessionLocal

async def check_db():
    async with AsyncSessionLocal() as db:
        print("\n--- PAIRING SESSIONS ---")
        res = await db.execute(select(PairingSession))
        sessions = res.scalars().all()
        for s in sessions:
            print(f"ID: {s.id}")
            print(f"  Code:     {s.pairing_code}")
            print(f"  Farm:     {s.farm_id}")
            print(f"  MAC:      {s.mac_address}")
            print(f"  Used:     {s.is_used}")
            print(f"  Expires:  {s.expires_at}")
            print(f"  Slot:     {s.node_slot_id}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(check_db())
