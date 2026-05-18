import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

# Import Base and all models to ensure metadata is populated
from backend.db.base import Base
# Import models in order
import backend.models.user
import backend.models.farm
import backend.models.device
import backend.models.sensor_data
import backend.models.state
import backend.models.decision
import backend.models.crop
import backend.models.i18n

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    base_url = DATABASE_URL.split("?")[0]
    DATABASE_URL = base_url.replace("postgresql://", "postgresql+asyncpg://")

async def recreate_schema():
    engine = create_async_engine(DATABASE_URL, echo=True, connect_args={"ssl": "require"})
    
    async with engine.begin() as conn:
        print("Recreating all tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Schema recreation complete.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(recreate_schema())
