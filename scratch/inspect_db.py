import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

# Load env from root
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.split("?")[0]
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

async def inspect_db():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # Get list of tables
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [row[0] for row in result.fetchall()]
        print(f"Tables found: {tables}")
        
        for table in tables:
            print(f"\n--- Schema for {table} ---")
            result = await conn.execute(text(f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{table}'"))
            for col in result.fetchall():
                print(f"  {col[0]} ({col[1]}) - Nullable: {col[2]}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect_db())
