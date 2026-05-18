import asyncio
import os
import sys
sys.path.insert(0, os.getcwd())
from backend.db.session import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [r[0] for r in res.fetchall()]
        print(f"Existing tables: {tables}")

if __name__ == "__main__":
    asyncio.run(check())
