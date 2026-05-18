import asyncio
import socket
from backend.db.session import AsyncSessionLocal
from backend.models.device import Device
from sqlalchemy import select

# DNS Monkeypatch (same as in session.py)
_original_getaddrinfo = socket.getaddrinfo
def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "ep-restless-meadow-a1l64nqq-pooler.ap-southeast-1.aws.neon.tech":
        return _original_getaddrinfo("13.228.46.236", port, family, type, proto, flags)
    return _original_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _patched_getaddrinfo

async def check_masters():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Device).where(Device.is_master == True))
        rows = res.scalars().all()
        print(f"Total Masters: {len(rows)}")
        for r in rows:
            print(f"MAC: {r.mac_address} | Farm: {r.farm_id} | Status: {r.status}")

if __name__ == "__main__":
    asyncio.run(check_masters())
