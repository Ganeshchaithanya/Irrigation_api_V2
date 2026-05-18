"""
One-shot: Correct historically bad soil_moisture readings for node E0:8C:FE:34:1B:18.
The node consistently reported ~2.2% due to a firmware ADC calculation bug.
We cannot know the true value for old readings, so we NULL them out so they
don't corrupt averages / AI models. 

A new corrected formula should be flashed to the node, after which fresh
readings will be correct.

Run: python -m backend.scratch.fix_bad_moisture
"""
import asyncio
from sqlalchemy import text
from backend.db.session import AsyncSessionLocal

BAD_MAC = "E0:8C:FE:34:1B:18"
# Readings with moisture < 5.0 from this node are almost certainly wrong
# (real soil moisture of 2% would mean a bone-dry desert)
THRESHOLD = 5.0

async def main():
    async with AsyncSessionLocal() as db:
        # Count affected rows first
        count_res = await db.execute(text("""
            SELECT COUNT(*) FROM sensor_readings sr
            JOIN devices d ON d.id = sr.device_id
            WHERE d.mac_address = :mac
              AND sr.soil_moisture < :threshold
              AND sr.soil_moisture IS NOT NULL
        """), {"mac": BAD_MAC, "threshold": THRESHOLD})
        count = count_res.scalar()
        print(f"Found {count} bad rows for {BAD_MAC} with moisture < {THRESHOLD}%")

        if count == 0:
            print("Nothing to fix.")
            return

        confirm = input(f"\nNULL out {count} rows? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            return

        await db.execute(text("""
            UPDATE sensor_readings sr
            SET soil_moisture = NULL
            FROM devices d
            WHERE d.id = sr.device_id
              AND d.mac_address = :mac
              AND sr.soil_moisture < :threshold
              AND sr.soil_moisture IS NOT NULL
        """), {"mac": BAD_MAC, "threshold": THRESHOLD})
        await db.commit()
        print(f"Done. Nulled {count} bad readings for {BAD_MAC}.")
        print("Flash corrected firmware to this node and fresh readings will be accurate.")

asyncio.run(main())
