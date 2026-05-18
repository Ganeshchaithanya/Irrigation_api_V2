
import asyncio
from sqlalchemy import text
from backend.db.session import engine

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name = 'devices'"))
        for row in res.fetchall():
            print(row)

if __name__ == "__main__":
    asyncio.run(check())
