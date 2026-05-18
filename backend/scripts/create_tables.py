import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.db.session import engine
from backend.db.base import Base

# Import all models to register them with Base.metadata
# Importing from backend.models ensures everything in __init__.py is loaded
import backend.models 

async def create_tables():
    print("Connecting to database and creating tables...")
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    print("All tables (including Acre, Farm, Zone, ValveCommand, etc.) created/verified successfully.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())
