import asyncio
import os
import sys
sys.path.insert(0, os.getcwd())
from backend.db.session import AsyncSessionLocal
from sqlalchemy import text

async def fix_db():
    async with AsyncSessionLocal() as db:
        print("Starting DB fix...")
        try:
            # Add pairing_code to devices
            await db.execute(text("ALTER TABLE devices ADD COLUMN pairing_code VARCHAR(50);"))
            print("Added pairing_code to devices.")
        except Exception as e:
            print("pairing_code error (might already exist):", e)
            
        try:
            # Add is_active to users
            await db.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;"))
            print("Added is_active to users.")
        except Exception as e:
            print("is_active error (might already exist):", e)
            
        await db.commit()
        print("DB fix complete.")

if __name__ == "__main__":
    asyncio.run(fix_db())
