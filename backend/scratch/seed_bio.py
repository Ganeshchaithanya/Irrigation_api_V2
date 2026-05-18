import asyncio
import os
import uuid
from backend.db.session import AsyncSessionLocal
from sqlalchemy import text

async def seed_bio():
    async with AsyncSessionLocal() as db:
        # Check if Tomato exists
        res = await db.execute(text("SELECT count(*) FROM crop_bio_profiles WHERE name = 'Tomato'"))
        if res.scalar() == 0:
            await db.execute(text("""
                INSERT INTO crop_bio_profiles (id, name, kc_json, stages_json, tsi_threshold)
                VALUES (:id, 'Tomato', '{"initial": 0.6, "mid": 1.15, "end": 0.8}', 
                '[{"name": "Seedling", "start": 0, "end": 20, "min_m": 55, "max_m": 65}]', 45.0)
            """), {"id": uuid.uuid4()})
            print("Seeded Tomato profile.")
        
        # Add Sugarcane too
        res = await db.execute(text("SELECT count(*) FROM crop_bio_profiles WHERE name = 'Sugarcane'"))
        if res.scalar() == 0:
            await db.execute(text("""
                INSERT INTO crop_bio_profiles (id, name, kc_json, stages_json, tsi_threshold)
                VALUES (:id, 'Sugarcane', '{"initial": 0.4, "mid": 1.25, "end": 0.7}', 
                '[{"name": "Sprouting", "start": 0, "end": 45, "min_m": 60, "max_m": 80}]', 50.0)
            """), {"id": uuid.uuid4()})
            print("Seeded Sugarcane profile.")
            
        await db.commit()

if __name__ == "__main__":
    asyncio.run(seed_bio())
