import asyncio
from backend.db.session import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT id, name, phone FROM users"))
        users = res.all()
        for u in users:
            print(f"User: ID={u.id}, Name={u.name}, Phone={u.phone}")
            
        res = await db.execute(text("SELECT id, user_id, name FROM farms"))
        farms = res.all()
        for f in farms:
            print(f"Farm: ID={f.id}, OwnerID={f.user_id}, Name={f.name}")

if __name__ == "__main__":
    asyncio.run(check())
