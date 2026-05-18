import asyncio
import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.db.session import engine
from backend.models.crop import CropBioProfile

async def seed_crops():
    print("Seeding expert biological profiles...")
    async with engine.begin() as conn:
        # We use a list of common crops
        crops = [
            {
                "name": "Rice",
                "season": "kharif",
                "duration_days": 120,
                "water_req_mm": 1200.0,
                "osmotic_shock_sensitive": True,
                "rrc_max_mm_per_cycle": 30.0,
                "rrc_stage_split": [0.6, 0.4],
                "temp_stress_threshold_c": 35.0,
                "temp_optimal_min_c": 22.0,
                "temp_optimal_max_c": 32.0,
                "tsi_threshold": 42.0,
                "kc_json": {"initial": 1.05, "development": 1.15, "mid": 1.20, "late": 1.10, "harvest": 0.90},
                "stages_json": [
                    {"name": "Initial", "start": 0, "end": 20, "min_m": 75, "max_m": 95},
                    {"name": "Tillering", "start": 21, "end": 50, "min_m": 80, "max_m": 95},
                    {"name": "Panicle Initiation", "start": 51, "end": 80, "min_m": 85, "max_m": 98},
                    {"name": "Maturity", "start": 81, "end": 120, "min_m": 60, "max_m": 80}
                ],
                "soil_type": "clay"
            },
            {
                "name": "Tomato",
                "season": "rabi",
                "duration_days": 90,
                "water_req_mm": 600.0,
                "osmotic_shock_sensitive": True,
                "rrc_max_mm_per_cycle": 15.0,
                "rrc_stage_split": [0.5, 0.5],
                "temp_stress_threshold_c": 30.0,
                "temp_optimal_min_c": 18.0,
                "temp_optimal_max_c": 26.0,
                "tsi_threshold": 38.0,
                "kc_json": {"initial": 0.6, "development": 0.8, "mid": 1.15, "late": 0.9, "harvest": 0.7},
                "stages_json": [
                    {"name": "Establishment", "start": 0, "end": 15, "min_m": 60, "max_m": 80},
                    {"name": "Vegetative", "start": 16, "end": 45, "min_m": 65, "max_m": 85},
                    {"name": "Flowering/Fruit", "start": 46, "end": 75, "min_m": 70, "max_m": 90},
                    {"name": "Ripening", "start": 76, "end": 90, "min_m": 50, "max_m": 70}
                ],
                "soil_type": "loam"
            },
             {
                "name": "Cotton",
                "season": "kharif",
                "duration_days": 180,
                "water_req_mm": 800.0,
                "osmotic_shock_sensitive": False,
                "rrc_max_mm_per_cycle": 25.0,
                "rrc_stage_split": [0.4, 0.6],
                "temp_stress_threshold_c": 38.0,
                "temp_optimal_min_c": 25.0,
                "temp_optimal_max_c": 35.0,
                "tsi_threshold": 45.0,
                "kc_json": {"initial": 0.35, "development": 0.7, "mid": 1.2, "late": 0.9, "harvest": 0.6},
                "stages_json": [
                    {"name": "Germination", "start": 0, "end": 30, "min_m": 40, "max_m": 60},
                    {"name": "Squaring", "start": 31, "end": 70, "min_m": 50, "max_m": 70},
                    {"name": "Boll Formation", "start": 71, "end": 140, "min_m": 60, "max_m": 80},
                    {"name": "Boll Opening", "start": 141, "end": 180, "min_m": 40, "max_m": 50}
                ],
                "soil_type": "sandy loam"
            }
        ]
        
        for crop_data in crops:
            # We use text() or just insert objects
            # Since we are using engine.begin() we can use models
            # But wait, conn is a Connection, not a Session.
            # We can use run_sync with a session or just raw inserts.
            # For simplicity, we'll use a session.
            pass

    # Better to use a session
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        for crop_data in crops:
            profile = CropBioProfile(**crop_data)
            session.add(profile)
        await session.commit()
    
    print("Seeded Rice, Tomato, and Cotton profiles.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_crops())
