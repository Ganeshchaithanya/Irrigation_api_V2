import asyncio
from sqlalchemy import text
import sys
import os

# Add root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.db.session import AsyncSessionLocal

async def add_column():
    async with AsyncSessionLocal() as db:
        try:
            print("Adding zones_per_acre to farms table...")
            await db.execute(text("ALTER TABLE farms ADD COLUMN zones_per_acre INTEGER DEFAULT 4;"))
            await db.commit()
            print("Success.")
        except Exception as e:
            print("Error:", e)
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(add_column())
