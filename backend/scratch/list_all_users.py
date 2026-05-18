import asyncio
from backend.db.session import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT id, name, email, phone FROM users"))
        users = res.all()
        print(f"Total Users: {len(users)}")
        for u in users:
            print(f"ID: {u.id}, Name: {u.name}, Email: {u.email}, Phone: {u.phone}")

if __name__ == "__main__":
    asyncio.run(check())
