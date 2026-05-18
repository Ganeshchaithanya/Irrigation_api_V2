import asyncio
import os
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv
import json

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.split("?")[0]
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

async def seed_crops():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        # Clear existing
        await conn.execute(text("DELETE FROM crop_bio_profiles"))
        
        crops = [
            {
                "name": "Rice",
                "duration": 120,
                "water": 1200,
                "kc": {"initial": 1.05, "development": 1.15, "mid": 1.20, "late": 0.9, "harvest": 0.6},
                "stages": [
                    {"name": "Initial", "start": 0, "end": 20, "min_m": 80, "max_m": 100},
                    {"name": "Development", "start": 21, "end": 50, "min_m": 85, "max_m": 100},
                    {"name": "Mid-Season", "start": 51, "end": 90, "min_m": 90, "max_m": 100},
                    {"name": "Late-Season", "start": 91, "end": 120, "min_m": 70, "max_m": 90},
                ],
                "rrc_max": 25.0
            },
            {
                "name": "Tomato",
                "duration": 140,
                "water": 600,
                "kc": {"initial": 0.6, "development": 0.8, "mid": 1.15, "late": 0.8, "harvest": 0.7},
                "stages": [
                    {"name": "Establishment", "start": 0, "end": 25, "min_m": 65, "max_m": 80},
                    {"name": "Vegetative", "start": 26, "end": 60, "min_m": 60, "max_m": 85},
                    {"name": "Flowering", "start": 61, "end": 100, "min_m": 70, "max_m": 90},
                    {"name": "Ripening", "start": 101, "end": 140, "min_m": 50, "max_m": 75},
                ],
                "rrc_max": 15.0
            },
            {
                "name": "Mango",
                "duration": 365,
                "water": 1500,
                "kc": {"initial": 0.6, "development": 0.7, "mid": 0.85, "late": 0.7, "harvest": 0.6},
                "stages": [
                    {"name": "Dormancy", "start": 0, "end": 90, "min_m": 30, "max_m": 50},
                    {"name": "Flowering", "start": 91, "end": 150, "min_m": 50, "max_m": 70},
                    {"name": "Fruit Development", "start": 151, "end": 300, "min_m": 60, "max_m": 80},
                    {"name": "Harvest", "start": 301, "end": 365, "min_m": 40, "max_m": 60},
                ],
                "rrc_max": 40.0
            },
            {
                "name": "Grape",
                "duration": 180,
                "water": 700,
                "kc": {"initial": 0.3, "development": 0.6, "mid": 0.85, "late": 0.6, "harvest": 0.4},
                "stages": [
                    {"name": "Bud burst", "start": 0, "end": 30, "min_m": 40, "max_m": 60},
                    {"name": "Flowering", "start": 31, "end": 70, "min_m": 50, "max_m": 70},
                    {"name": "Berry Growth", "start": 71, "end": 140, "min_m": 60, "max_m": 80},
                    {"name": "Ripening", "start": 141, "end": 180, "min_m": 40, "max_m": 60},
                ],
                "rrc_max": 20.0
            }
        ]

        # Simplified for brevity but including essentials
        for c in crops:
            await conn.execute(text("""
                INSERT INTO crop_bio_profiles (
                    id, name, season, duration_days, water_req_mm, 
                    kc_json, stages_json, osmotic_shock_sensitive, 
                    rrc_max_mm_per_cycle, rrc_stage_split, 
                    temp_stress_threshold_c, temp_optimal_min_c, 
                    temp_optimal_max_c, tsi_threshold, soil_type
                ) VALUES (
                    :id, :name, 'all', :duration, :water,
                    :kc, :stages, true, :rrc_max, '[0.4, 0.6]',
                    35.0, 22.0, 30.0, 42.0, 'loam'
                )
            """), {
                "id": str(uuid.uuid4()),
                "name": c["name"],
                "duration": c["duration"],
                "water": c["water"],
                "kc": json.dumps(c["kc"]),
                "stages": json.dumps(c["stages"]),
                "rrc_max": c["rrc_max"]
            })
        print(f"Seeded {len(crops)} crop profiles.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_crops())
