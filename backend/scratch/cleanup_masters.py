import asyncio
import socket
from backend.db.session import AsyncSessionLocal
from backend.models.device import Device
from sqlalchemy import select, delete

# DNS Monkeypatch
_original_getaddrinfo = socket.getaddrinfo
def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "ep-restless-meadow-a1l64nqq-pooler.ap-southeast-1.aws.neon.tech":
        return _original_getaddrinfo("13.228.46.236", port, family, type, proto, flags)
    return _original_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _patched_getaddrinfo

async def cleanup_masters():
    async with AsyncSessionLocal() as db:
        # Find masters with status='discovery' or mac_address is None
        res = await db.execute(
            select(Device).where(
                Device.is_master == True,
                (Device.status == "discovery") | (Device.mac_address.is_(None))
            )
        )
        to_delete = res.scalars().all()
        print(f"Found {len(to_delete)} stale master records.")
        for d in to_delete:
            print(f"Deleting stale master: {d.id} (Status: {d.status})")
            await db.delete(d)
        
        await db.commit()
        print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup_masters())
