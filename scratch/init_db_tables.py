import asyncio
import os
import sys
sys.path.insert(0, os.getcwd())

# Import all models to ensure they are registered with Base
from backend.db.base import Base
from backend.models.user import User
from backend.models.farm import Farm, Zone, Acre
from backend.models.device import Device
from backend.models.pairing_session import PairingSession
from backend.models.state import ZoneState
from backend.models.sensor_data import SensorReading
from backend.models.decision import DecisionLog, ValveCommand, CropPlan, Schedule
from backend.models.crop import CropBioProfile
# ... add others if needed

from backend.db.session import engine

async def init_db():
    async with engine.begin() as conn:
        print("Creating tables if they don't exist...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created.")

if __name__ == "__main__":
    asyncio.run(init_db())
