"""
clear_data.py — Truncate all rows from every table in the public schema
while keeping the schema/structure intact.
Run with: python clear_data.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    base_url = DATABASE_URL.split("?")[0]
    DATABASE_URL = base_url.replace("postgresql://", "postgresql+asyncpg://")


async def clear_data():
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        # Get all user tables in the public schema
        result = await conn.execute(
            text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'")
        )
        tables = [row[0] for row in result.all()]

        if not tables:
            print("No tables found.")
            return

        print(f"Found {len(tables)} table(s): {', '.join(tables)}")
        print("Truncating all tables (keeping schema)...")

        # TRUNCATE with CASCADE handles FK constraints, RESTART IDENTITY resets sequences
        tables_str = ", ".join(f'"{t}"' for t in tables)
        await conn.execute(
            text(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE")
        )

        print("✅ All rows deleted. Schema is intact.")
        print("Tables cleared:")
        for t in tables:
            print(f"  • {t}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(clear_data())
