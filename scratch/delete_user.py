
import asyncio
import sys
import os
from sqlalchemy import select, delete
from backend.db.session import AsyncSessionLocal, get_db
from backend.models.user import User

async def remove_user(identifier: str):
    async for db in get_db():
        # Check if user exists
        stmt = select(User).where((User.phone == identifier) | (User.email == identifier))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User not found: {identifier}")
            return
            
        print(f"Deleting user: {user.name} ({user.phone} / {user.email})")
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()
        print("User deleted successfully.")
        break

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_user.py <phone_or_email>")
    else:
        asyncio.run(remove_user(sys.argv[1]))
