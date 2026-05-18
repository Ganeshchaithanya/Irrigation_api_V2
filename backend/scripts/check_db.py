import asyncio
from sqlalchemy import text
from backend.db.session import engine

async def check_users():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, name, phone, email FROM users;"))
        users = result.all()
        print(f"Total users in DB: {len(users)}")
        for user in users:
            print(f" - {user.name} | {user.phone} | {user.email}")

if __name__ == "__main__":
    asyncio.run(check_users())
