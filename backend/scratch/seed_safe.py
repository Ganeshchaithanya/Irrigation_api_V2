import asyncio
import os
import uuid
import socket
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext

# DNS Monkeypatch
_original_getaddrinfo = socket.getaddrinfo
def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "ep-restless-meadow-a1l64nqq-pooler.ap-southeast-1.aws.neon.tech":
        return _original_getaddrinfo("13.228.46.236", port, family, type, proto, flags)
    return _original_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _patched_getaddrinfo

load_dotenv()

from backend.db.base import Base
from backend.models.user import User

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    base_url = DATABASE_URL.split("?")[0]
    DATABASE_URL = base_url.replace("postgresql://", "postgresql+asyncpg://")

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_db():
    engine = create_async_engine(DATABASE_URL, connect_args={"ssl": "require"})
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession)

    async with AsyncSessionLocal() as db:
        # Create Admin User
        admin_phone = "9900990099"
        result = await db.execute(select(User).where(User.phone == admin_phone))
        if not result.scalar_one_or_none():
            admin = User(
                id=uuid.uuid4(),
                name="Admin User",
                phone=admin_phone,
                email="admin@aquasol.com",
                hashed_password=pwd_ctx.hash("password123"),
                preferred_lang="en"
            )
            db.add(admin)
            await db.commit()
            print(f"Admin user created: {admin_phone} / password123")
        else:
            print("Admin user already exists.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_db())
