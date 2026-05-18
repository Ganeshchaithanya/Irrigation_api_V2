import asyncio
from backend.db.session import AsyncSessionLocal
from sqlalchemy import text
from datetime import datetime, timezone

async def check_discovery():
    async with AsyncSessionLocal() as db:
        print("Checking for discovered hardware...")
        result = await db.execute(text("SELECT id, mac_address, status, is_master, last_seen_at FROM devices ORDER BY last_seen_at DESC NULLS LAST LIMIT 10"))
        rows = result.fetchall()
        
        if not rows:
            print("No devices found in database.")
            return

        print(f"{'ID':<38} | {'MAC':<18} | {'Status':<10} | {'Type':<8} | {'Last Seen'}")
        print("-" * 100)
        for row in rows:
            dev_id = str(row[0])
            mac = str(row[1]) if row[1] else "NONE"
            status = str(row[2]) if row[2] else "UNKNOWN"
            is_master = bool(row[3])
            last_seen_dt = row[4]
            
            dev_type = "Master" if is_master else "Node"
            last_seen_str = last_seen_dt.strftime("%Y-%m-%d %H:%M:%S") if last_seen_dt else "Never"
            
            print(f"{dev_id:<38} | {mac:<18} | {status:<10} | {dev_type:<8} | {last_seen_str}")

if __name__ == "__main__":
    asyncio.run(check_discovery())
