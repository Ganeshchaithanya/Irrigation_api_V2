import asyncio
from sqlalchemy import text
from backend.db.session import engine
from backend.db.base import Base

# Import all models to ensure they are registered with Base.metadata
import backend.models.user
import backend.models.farm
import backend.models.device
import backend.models.sensor_data
import backend.models.state
import backend.models.decision
import backend.models.crop
import backend.models.i18n

async def truncate_tables():
    print("Starting database truncation...")
    
    # Get all table names from metadata
    table_names = [table.name for table in Base.metadata.sorted_tables]
    # Reverse order to handle dependencies if not using CASCADE (though we will)
    table_names.reverse()
    
    async with engine.begin() as conn:
        for table in table_names:
            print(f"Truncating {table}...")
            try:
                # Use RESTART IDENTITY to reset IDs
                # Use CASCADE to handle any missed dependencies
                await conn.execute(text(f"TRUNCATE TABLE \"{table}\" RESTART IDENTITY CASCADE;"))
            except Exception as e:
                print(f"Warning: Could not truncate {table}: {e}")
                
    print("Database truncation complete.")

if __name__ == "__main__":
    asyncio.run(truncate_tables())
