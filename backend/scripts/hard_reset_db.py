import asyncio
from sqlalchemy import text
from backend.db.base import Base
from backend.db.session import engine
# Import all models to register them with Base.metadata
import backend.models.user
import backend.models.farm
import backend.models.device
import backend.models.sensor_data
import backend.models.state
import backend.models.decision
import backend.models.i18n
import backend.models.crop

async def hard_reset():
    print("WARNING: This will drop ALL tables in the database.")
    async with engine.begin() as conn:
        print("Dropping public schema (CASCADE)...")
        # Raw SQL to wipe the public schema and recreate it
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        await conn.execute(text("COMMENT ON SCHEMA public IS 'standard public schema';"))
        
        print("Recreating all tables from models...")
        await conn.run_sync(Base.metadata.create_all)
        print("Database reset complete.")

if __name__ == "__main__":
    asyncio.run(hard_reset())
