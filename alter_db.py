import asyncio
from sqlalchemy import text
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from backend.db.session import AsyncSessionLocal

async def alter_tables():
    async with AsyncSessionLocal() as db:
        try:
            await db.execute(text("ALTER TABLE zones ADD COLUMN operating_mode VARCHAR(50) DEFAULT 'active';"))
        except Exception as e:
            print("zones error:", e)
            
        try:
            await db.execute(text("ALTER TABLE decision_log ADD COLUMN top_factors JSONB;"))
            await db.execute(text("ALTER TABLE decision_log ADD COLUMN ood_flag BOOLEAN DEFAULT FALSE;"))
        except Exception as e:
            print("decision_log error:", e)
            
        await db.commit()
        print("Success.")

if __name__ == "__main__":
    asyncio.run(alter_tables())
