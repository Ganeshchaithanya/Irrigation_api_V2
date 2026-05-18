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

async def seed_remaining_crops():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        crops = [
            {
                "name": "Pomegranate",
                "duration": 180,
                "water": 800,
                "kc": {"initial": 0.5, "development": 0.75, "mid": 1.0, "late": 0.75, "harvest": 0.5},
                "stages": [
                    {"name": "Initial", "start": 0, "end": 40, "min_m": 45, "max_m": 65},
                    {"name": "Flowering", "start": 41, "end": 90, "min_m": 55, "max_m": 75},
                    {"name": "Fruit Growth", "start": 91, "end": 150, "min_m": 65, "max_m": 85},
                    {"name": "Harvest", "start": 151, "end": 180, "min_m": 45, "max_m": 60},
                ],
                "rrc_max": 18.0
            },
            {
                "name": "Banana",
                "duration": 365,
                "water": 2000,
                "kc": {"initial": 0.5, "development": 0.8, "mid": 1.1, "late": 1.0, "harvest": 1.0},
                "stages": [
                    {"name": "Vegetative", "start": 0, "end": 180, "min_m": 70, "max_m": 90},
                    {"name": "Flowering", "start": 181, "end": 240, "min_m": 75, "max_m": 95},
                    {"name": "Yield Formation", "start": 241, "end": 330, "min_m": 80, "max_m": 100},
                    {"name": "Ripening", "start": 331, "end": 365, "min_m": 70, "max_m": 85},
                ],
                "rrc_max": 30.0
            },
            {
                "name": "Citrus",
                "duration": 365,
                "water": 1200,
                "kc": {"initial": 0.7, "development": 0.7, "mid": 0.7, "late": 0.7, "harvest": 0.7},
                "stages": [
                    {"name": "Dormancy", "start": 0, "end": 60, "min_m": 40, "max_m": 60},
                    {"name": "Bloom", "start": 61, "end": 120, "min_m": 60, "max_m": 80},
                    {"name": "Fruit Set", "start": 121, "end": 280, "min_m": 65, "max_m": 85},
                    {"name": "Harvest", "start": 281, "end": 365, "min_m": 50, "max_m": 70},
                ],
                "rrc_max": 22.0
            },
            {
                "name": "Coffee",
                "duration": 365,
                "water": 1400,
                "kc": {"initial": 0.9, "development": 0.9, "mid": 0.9, "late": 0.9, "harvest": 0.9},
                "stages": [
                    {"name": "Flowering", "start": 0, "end": 60, "min_m": 65, "max_m": 85},
                    {"name": "Pinhead", "start": 61, "end": 150, "min_m": 70, "max_m": 90},
                    {"name": "Bean Expansion", "start": 151, "end": 300, "min_m": 75, "max_m": 95},
                    {"name": "Ripening", "start": 301, "end": 365, "min_m": 60, "max_m": 80},
                ],
                "rrc_max": 15.0
            }
        ]

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
        print(f"Seeded {len(crops)} additional crop profiles.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_remaining_crops())
