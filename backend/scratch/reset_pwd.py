import asyncio
from backend.db.session import AsyncSessionLocal
from sqlalchemy import text
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def reset():
    async with AsyncSessionLocal() as db:
        hashed = pwd_ctx.hash("password123")
        await db.execute(
            text("UPDATE users SET hashed_password = :h WHERE email = 'chaithanyaug@gmail.com'"),
            {"h": hashed}
        )
        await db.commit()
        print("Password reset to: password123")

if __name__ == "__main__":
    asyncio.run(reset())
