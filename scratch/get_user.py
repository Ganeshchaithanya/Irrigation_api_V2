
import asyncio
from sqlalchemy import select
from backend.db.session import AsyncSessionLocal
from backend.models.user import User

async def get_user():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).limit(1))
        user = res.scalar()
        if user:
            print(user.id)
        else:
            print("NONE")

if __name__ == "__main__":
    asyncio.run(get_user())
