import asyncio
import os
import sys
sys.path.insert(0, os.getcwd())
from backend.db.session import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        for table in ['devices', 'zones', 'farms', 'users']:
            res = await conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'"))
            columns = [r[0] for r in res.fetchall()]
            print(f"Columns in '{table}' table: {columns}")

if __name__ == "__main__":
    asyncio.run(check())
