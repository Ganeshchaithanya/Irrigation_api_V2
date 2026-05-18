import asyncio
from backend.db.session import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT count(*) FROM farms"))
        count = res.scalar()
        print(f"Farms count: {count}")
        
        res = await db.execute(text("SELECT count(*) FROM users"))
        ucount = res.scalar()
        print(f"Users count: {ucount}")

if __name__ == "__main__":
    asyncio.run(check())
