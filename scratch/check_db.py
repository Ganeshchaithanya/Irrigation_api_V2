import asyncio
import os
import sys
sys.path.insert(0, os.getcwd())
from backend.db.session import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'devices'"))
        columns = [r[0] for r in res.fetchall()]
        print("Columns in 'devices' table:")
        for col in columns:
            print(f" - {col}")

if __name__ == "__main__":
    asyncio.run(check())
