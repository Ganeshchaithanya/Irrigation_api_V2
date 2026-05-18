"""
Scratch: Inspect raw soil_moisture values in sensor_readings to confirm fraction vs pct issue.
Run:  python -m backend.scratch.inspect_moisture
"""
import asyncio
from sqlalchemy import text
from backend.db.session import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT
                d.mac_address,
                d.is_master,
                sr.soil_moisture,
                sr.time
            FROM sensor_readings sr
            JOIN devices d ON d.id = sr.device_id
            WHERE sr.soil_moisture IS NOT NULL
            ORDER BY sr.time DESC
            LIMIT 30
        """))
        rows = result.fetchall()
        print(f"\n{'MAC':<22} {'Master':<8} {'Moisture':>10}  {'Time'}")
        print("-" * 60)
        for mac, is_master, moisture, ts in rows:
            flag = " ⚠ FRACTION" if moisture is not None and moisture <= 1.0 else ""
            print(f"{mac:<22} {str(is_master):<8} {moisture:>10.2f}  {ts}{flag}")

        # Summary
        await db.execute(text("SELECT 1"))  # keep session alive
        counts = await db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE soil_moisture <= 1.0)  AS fraction_count,
                COUNT(*) FILTER (WHERE soil_moisture > 1.0)   AS pct_count,
                MIN(soil_moisture)  AS min_val,
                MAX(soil_moisture)  AS max_val,
                AVG(soil_moisture)  AS avg_val
            FROM sensor_readings
            WHERE soil_moisture IS NOT NULL
        """))
        row = counts.fetchone()
        print(f"\n--- Summary ---")
        print(f"Fraction (<=1.0) rows : {row.fraction_count}")
        print(f"Percentage (>1.0) rows: {row.pct_count}")
        print(f"Min / Max / Avg       : {row.min_val:.3f} / {row.max_val:.3f} / {row.avg_val:.3f}")

asyncio.run(main())
