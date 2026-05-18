import asyncio
from backend.db.session import AsyncSessionLocal
from backend.models.device import Device
from sqlalchemy import update

async def fix():
    async with AsyncSessionLocal() as db:
        # Update the incorrect Master MAC to the one actually talking to the server
        res = await db.execute(
            update(Device)
            .where(Device.mac_address == 'E8:6B:EA:D9:63:F0')
            .values(
                mac_address='28:05:A5:25:4D:78', 
                device_uid='MASTER-254D78', 
                device_secret='654321',
                status='active'
            )
        )
        await db.commit()
        print(f"Updated {res.rowcount} records. Master is now 28:05:A5:25:4D:78")

if __name__ == "__main__":
    asyncio.run(fix())
