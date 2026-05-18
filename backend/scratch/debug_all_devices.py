import asyncio
import socket
from backend.db.session import AsyncSessionLocal
from backend.models.device import Device
from sqlalchemy import select

# DNS Monkeypatch
_original_getaddrinfo = socket.getaddrinfo
def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "ep-restless-meadow-a1l64nqq-pooler.ap-southeast-1.aws.neon.tech":
        return _original_getaddrinfo("13.228.46.236", port, family, type, proto, flags)
    return _original_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _patched_getaddrinfo

async def check_devices():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Device))
        rows = res.scalars().all()
        print(f"Total Devices: {len(rows)}")
        for r in rows:
            role = "MASTER" if r.is_master else "NODE"
            print(f"ROLE: {role} | MAC: {r.mac_address} | Code: {r.pairing_code} | Status: {r.status}")

if __name__ == "__main__":
    asyncio.run(check_devices())
