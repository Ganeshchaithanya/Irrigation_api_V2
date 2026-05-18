import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import MetaData, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
# Convert postgresql:// to postgresql+asyncpg:// if needed
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    # Strip query parameters that asyncpg doesn't like
    base_url = DATABASE_URL.split("?")[0]
    DATABASE_URL = base_url.replace("postgresql://", "postgresql+asyncpg://")

async def reset_db():
    engine = create_async_engine(DATABASE_URL, echo=True)
    metadata = MetaData()
    
    async with engine.begin() as conn:
        print("Dropping all tables...")
        # Get all table names
        result = await conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"))
        tables = [row[0] for row in result.all()]
        
        if tables:
            # Drop all tables in public schema
            tables_str = ", ".join(f'"{t}"' for t in tables)
            await conn.execute(text(f"DROP TABLE IF EXISTS {tables_str} CASCADE"))
            print(f"Dropped: {tables_str}")
        else:
            print("No tables found.")

    await engine.dispose()
    print("Database cleared. Run alembic upgrade head to recreate schema.")

if __name__ == "__main__":
    asyncio.run(reset_db())
